from typing import Dict, Any
from .azure_openai_client import call_azure_chat_json
from .bulk_sanctions_matcher import find_sanction_candidates


SANCTIONS_SYSTEM_PROMPT = """
You are a bank sanctions screening assistant.
You receive one customer profile and a small list of candidate sanctions records.
Be conservative: only confirm a match if the evidence is strong
(birth date and country match, plus a high name similarity or alias).
Always reply in strict JSON:
{"match": bool, "matchedRecordId": "string|null", "confidence": float, "reason": "text"}.
Do not add commentary outside JSON.
""".strip()


def decide_sanctions(risk_input: Dict[str, Any]) -> Dict[str, Any]:
    candidates = find_sanction_candidates(risk_input)

    payload = {
        "customer": {
            "customerNo": risk_input.get("customerNo"),
            "fullName": risk_input.get("fullName"),
            "birthCountry": risk_input.get("birthCountry"),
            "citizenship": risk_input.get("citizenship"),
        },
        "candidates": candidates,
    }

    if not candidates:
        return {
            "match": False,
            "matchedRecordId": None,
            "confidence": 0.0,
            "reason": "No candidates found for screening",
        }

    return call_azure_chat_json(system_prompt=SANCTIONS_SYSTEM_PROMPT, payload=payload)
