from typing import List
from .rag_engine import embed, cosine, generate_answer
from .storage import doc_store

SYSTEM_PROMPT = """
You are an AML/Compliance risk engine.

You get:
- A customer onboarding profile (JSON).
- Context about FATF, UN sanctions, and EU sanctions.

You must:
- Analyze the profile and context.
- Return a JSON object with:
    {
      "risk_score": <0-100 integer>,
      "risk_band": "GREEN" | "YELLOW" | "RED",
      "reasons": [ "STRING_REASON_1", "STRING_REASON_2", ... ]
    }

Rules:
- Higher score = higher risk.
- Consider FATF black/grey list countries very high risk.
- Consider UN/EU sanction matches extremely high risk.
- Return **only** valid JSON, no extra text.
"""


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
    top = doc_store.get_top_k(q_emb, k=10, metric=cosine)

    context = "\n\n---\n\n".join([t["text"] for t in top])

    user_content = f"""
Customer onboarding profile (JSON):
{profile}

Use the context below about FATF black/grey lists and UN/EU sanctions to compute the risk.

Context:
{context}
"""

    # 2) Call LLM
    raw_answer = generate_answer(
        question=SYSTEM_PROMPT,  # you can treat system prompt as "question"
        context=user_content     # and your profile+context as "context"
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
