from typing import Dict, List
import json

from .rag_engine import embed, cosine, generate_answer
from .storage import doc_store

SYSTEM_PROMPT = """Analyze this customer risk profile and return ONLY valid JSON (no extra text):
{"risk_score": 0-100, "risk_band": "GREEN"/"YELLOW"/"RED", "reasons": ["..."]}

Rules (guidance, not hard rules):
- FATF black list countries => risk_score usually 90+
- FATF grey list => 60+
- If PEP => +30 to risk_score
- If UN/EU sanctions or matches local blacklist => 95+ and risk_band="RED"

You MUST:
- Return only valid JSON.
- Never include explanations outside of JSON.
"""


def _build_query_from_profile(profile: Dict) -> str:
    """
    Turn DB customer profile into a text query for RAG.
    """
    country_of_birth = profile.get("country_of_birth") or "unknown"
    residency_country = profile.get("residency_country") or "unknown"
    occupation = profile.get("occupation") or "unknown"
    is_pep = profile.get("is_pep")

    return (
        f"Customer from {residency_country}, born in {country_of_birth}, "
        f"occupation {occupation}, PEP={is_pep}. "
        "Check FATF risk, UN/EU sanctions, local blacklist and overall AML risk."
    )


def llm_score_onboarding(profile: Dict) -> Dict:
    """
    Use Ollama + RAG (sanctions + FATF docs in doc_store) to score risk.
    Returns dict: { risk_score: int, risk_band: str, reasons: List[str] }
    """
    # 1) Build query & retrieve top sanctions/FATF chunks
    try:
        query = _build_query_from_profile(profile)
        query_embedding = embed(query)
        top_chunks = doc_store.search(query_embedding, k=5, metric=cosine)

        if top_chunks:
            context = "\n\n---\n\n".join(chunk["text"] for chunk in top_chunks)
        else:
            context = "No sanctions documents found in the knowledge base."
    except Exception:
        # If embeddings / doc_store fail, still continue with pure profile-based scoring
        context = "Sanctions knowledge base is temporarily unavailable."

    # 2) Ask LLM to produce JSON only
    question = (
        f"{SYSTEM_PROMPT}\n\n"
        f"CONTEXT_FROM_DOCUMENTS:\n{context}\n\n"
        f"CUSTOMER_PROFILE_JSON:\n{json.dumps(profile, ensure_ascii=False)}\n\n"
        "Return only a single JSON object."
    )

    raw_answer = generate_answer(question=question, context="")

    # 3) Try to extract JSON even if model wraps it with extra text
    try:
        start = raw_answer.find("{")
        end = raw_answer.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = raw_answer[start : end + 1]
        else:
            json_str = raw_answer

        result = json.loads(json_str)
    except Exception:
        return {
            "risk_score": 50,
            "risk_band": "YELLOW",
            "reasons": [
                "LLM_OUTPUT_PARSE_ERROR",
                f"raw={raw_answer[:200]}",
            ],
        }

    # 4) Normalize fields and enforce types
    # risk_score
    rs = result.get("risk_score", 50)
    try:
        rs = int(rs)
    except (ValueError, TypeError):
        rs = 50
    rs = max(0, min(100, rs))

    # risk_band
    band = str(result.get("risk_band", "YELLOW")).upper()
    if band not in ("GREEN", "YELLOW", "RED"):
        if rs >= 80:
            band = "RED"
        elif rs >= 50:
            band = "YELLOW"
        else:
            band = "GREEN"

    # reasons
    reasons = result.get("reasons") or []
    if not isinstance(reasons, list):
        reasons = [str(reasons)]

    return {
        "risk_score": rs,
        "risk_band": band,
        "reasons": reasons,
    }
