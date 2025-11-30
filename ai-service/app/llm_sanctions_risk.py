from typing import Dict, List, Any
import json

from .rag_engine import embed, cosine, generate_answer
from .storage import doc_store
from .sanctions_loader import get_fatf_category


SYSTEM_PROMPT = """You are an AML/CFT risk analyst for a bank.
You get:
- Customer profile (JSON)
- Sanctions matches (UN/EU/local, fuzzy/phonetic/transliteration)
- Baseline rule-based risk decided by the bank.

You MUST:
- Respect that sanctions and FATF black list imply HIGH risk.
- Return ONLY a JSON object like:
  {
    "risk_score": 0-100,
    "risk_band": "GREEN" | "YELLOW" | "RED",
    "reasons": ["..."]
  }

Never add any explanation outside the JSON.
"""


def _baseline_sanctions_risk(
    profile: Dict,
    matches: List[Dict],
    local_blacklist_flag: bool,
) -> Dict[str, Any]:
    """
    Pure rule-based risk (no LLM).
    This is the MINIMUM risk we will ever return.
    FATF & sanctions & local blacklist drive the decision.
    """
    residency = profile.get("residency_country") or profile.get("country_of_birth") or ""
    pep = bool(profile.get("is_pep"))

    fatf_cat = get_fatf_category(residency)

    score = 10
    band = "GREEN"
    reasons: List[str] = []

    # 1) FATF country risk
    if fatf_cat is not None:
        key = str(getattr(fatf_cat, "key", "")).lower()
        if "black" in key:
            score = max(score, 95)
            band = "RED"
            reasons.append(
                f"Customer residency country '{residency}' is in FATF black list."
            )
        elif "grey" in key:
            score = max(score, 75)
            band = "YELLOW"
            reasons.append(
                f"Customer residency country '{residency}' is in FATF grey list."
            )
        else:
            score = max(score, 40)
            if band == "GREEN":
                band = "YELLOW"
            reasons.append(
                f"Customer residency country '{residency}' is in monitored FATF list."
            )

    # 2) UN / EU sanctions matches (any type) → RED
    if matches:
        score = max(score, 98)
        band = "RED"
        reasons.append(
            "Customer name has match in UN/EU sanctions list "
            f"({', '.join(sorted(set(m.get('match_type', 'exact') for m in matches)))})"
        )

    # 3) Local blacklist
    if local_blacklist_flag:
        score = max(score, 99)
        band = "RED"
        reasons.append("Customer is on local blacklist.")

    # 4) PEP
    if pep:
        score = max(score, 80)
        if band != "RED":
            band = "YELLOW"
        reasons.append("Customer is a Politically Exposed Person (PEP).")

    # If nothing triggered, keep very low risk
    if not reasons:
        score = 10
        band = "GREEN"
        reasons.append("No FATF/sanctions/local blacklist/PEP flags detected.")

    return {
        "risk_score": score,
        "risk_band": band,
        "reasons": reasons,
    }


def _build_query_for_rag(
    profile: Dict,
    matches: List[Dict],
    baseline: Dict[str, Any],
) -> str:
    """
    Build a natural language query so we can retrieve the most relevant sanctions/FATF chunks.
    """
    residency = profile.get("residency_country") or "unknown"
    birth = profile.get("country_of_birth") or "unknown"
    full_name = profile.get("full_name") or "unknown"
    occupation = profile.get("occupation") or "unknown"

    return (
        f"Customer {full_name} from {residency}, born in {birth}, "
        f"occupation {occupation}. Baseline risk band={baseline['risk_band']}, "
        f"baseline score={baseline['risk_score']}. "
        f"Sanctions matches: {json.dumps(matches, ensure_ascii=False)}. "
        "Explain if this risk is appropriate and add AML reasoning using FATF and sanctions documents."
    )


def _llm_overlay_on_top_of_baseline(
    profile: Dict,
    matches: List[Dict],
    baseline: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Use RAG + LLM to refine reasons and possibly increase risk,
    but NEVER downgrade below baseline.
    """
    # 1) RAG context
    try:
        query = _build_query_for_rag(profile, matches, baseline)
        q_emb = embed(query)
        top_chunks = doc_store.get_top_k(q_emb, k=5, metric=cosine)
        if top_chunks:
            context = "\n\n---\n\n".join(ch["text"] for ch in top_chunks)
        else:
            context = "No sanctions/FATF documents in the knowledge base."
    except Exception as ex:
        context = f"Sanctions knowledge base temporarily unavailable ({type(ex).__name__})."

    # 2) Ask LLM for JSON
    payload = {
        "profile": profile,
        "matches": matches,
        "baseline": baseline,
    }

    question = (
        f"{SYSTEM_PROMPT}\n\n"
        f"CONTEXT_FROM_DOCUMENTS:\n{context}\n\n"
        f"INPUT_DATA:\n{json.dumps(payload, ensure_ascii=False)}\n\n"
        "Return ONLY ONE JSON object."
    )

    raw = generate_answer(question=question, context="")

    # 3) Parse JSON safely
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in LLM response.")
        parsed = json.loads(raw[start : end + 1])
    except Exception:
        # LLM failed → use baseline only, but mark reason
        baseline["reasons"].append("LLM_FAILED_USED_BASELINE_ONLY")
        return baseline

    # 4) Normalize LLM result
    llm_score = parsed.get("risk_score", baseline["risk_score"])
    try:
        llm_score = int(llm_score)
    except (ValueError, TypeError):
        llm_score = baseline["risk_score"]
    llm_score = max(0, min(100, llm_score))

    llm_band = str(parsed.get("risk_band", baseline["risk_band"])).upper()
    valid_bands = {"GREEN", "YELLOW", "RED"}
    if llm_band not in valid_bands:
        llm_band = baseline["risk_band"]

    llm_reasons = parsed.get("reasons") or []
    if not isinstance(llm_reasons, list):
        llm_reasons = [str(llm_reasons)]

    # 5) Combine with baseline → never downgrade sanctions/FATF risk
    final_score = max(baseline["risk_score"], llm_score)

    band_rank = {"GREEN": 0, "YELLOW": 1, "RED": 2}
    base_rank = band_rank.get(baseline["risk_band"], 1)
    llm_rank = band_rank.get(llm_band, 1)
    final_band = baseline["risk_band"] if base_rank >= llm_rank else llm_band

    # 6) Merge reasons
    reasons = list(baseline["reasons"])
    for r in llm_reasons:
        r_str = str(r)
        if r_str not in reasons:
            reasons.append(r_str)

    return {
        "risk_score": final_score,
        "risk_band": final_band,
        "reasons": reasons,
    }


def llm_score_sanctions(
    profile: Dict,
    matches: List[Dict],
    local_blacklist_flag: bool,
    use_llm: bool,
) -> Dict[str, Any]:
    """
    Main function used by /risk/from-db.

    - Always computes strict baseline with FATF + sanctions + local blacklist + PEP.
    - If use_llm = False -> returns baseline only (no Ollama calls).
    - If use_llm = True  -> calls LLM with RAG, but never downgrades below baseline.
    """
    baseline = _baseline_sanctions_risk(profile, matches, local_blacklist_flag)

    if not use_llm:
        return baseline

    try:
        return _llm_overlay_on_top_of_baseline(profile, matches, baseline)
    except Exception as ex:
        # If anything unexpected happens, use baseline only.
        baseline["reasons"].append(f"LLM_OVERLAY_ERROR_{type(ex).__name__}")
        return baseline
