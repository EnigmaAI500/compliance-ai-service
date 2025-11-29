from typing import List
from .rag_engine import embed, cosine, generate_answer
from .storage import doc_store

SYSTEM_PROMPT = """Analyze this customer risk profile and return ONLY valid JSON (no extra text):
{"risk_score": 0-100, "risk_band": "GREEN"/"YELLOW"/"RED", "reasons": ["..."]}

Rules: FATF black list = 90+, grey list = 60+, PEP = +30, UN/EU sanctions = 95+"""


def llm_score_onboarding(profile: dict) -> dict:
    """
    Use Ollama to score risk based on profile + RAG context.
    Returns parsed JSON dict with keys: risk_score, risk_band, reasons.
    """
    # 1) Create a query string based on profile to retrieve relevant chunks
    q_text = (
        f"Risk evaluation for customer with country_of_birth={profile.get('country_of_birth')}, "
        f"residency_country={profile.get('residency_country')}, "
        f"is_pep={profile.get('is_pep')}, "
        f"occupation={profile.get('occupation')}, "
        f"full_name={profile.get('full_name')}"
    )

    q_emb = embed(q_text)
    # OPTIMIZATION: Reduce to top 3 chunks only
    top = doc_store.get_top_k(q_emb, k=3, metric=cosine)

    # OPTIMIZATION: Limit context to first 2000 chars per chunk
    context = "\n\n---\n\n".join([t["text"][:2000] for t in top])

    # OPTIMIZATION: Shorter, more direct prompt
    user_content = f"""{SYSTEM_PROMPT}

Profile: {profile}

Context (FATF/sanctions):
{context[:3000]}"""

    # 2) Call LLM with simplified prompt
    raw_answer = generate_answer(
        question=user_content,
        context=""  # Already included in question
    )

    # 3) Parse JSON (be defensive)
    import json
    try:
        result = json.loads(raw_answer)
    except json.JSONDecodeError:
        # Fallback in worst case
        return {
            "risk_score": 50,
            "risk_band": "YELLOW",
            "reasons": ["LLM_OUTPUT_PARSE_ERROR", f"raw={raw_answer[:200]}"]
        }

    # sanity defaults
    result.setdefault("risk_score", 50)
    result.setdefault("risk_band", "YELLOW")
    result.setdefault("reasons", [])
    return result
