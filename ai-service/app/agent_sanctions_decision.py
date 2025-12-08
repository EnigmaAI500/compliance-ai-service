# ai-service/app/agent_sanctions_decision.py
from typing import Dict, Any
from .llm_utils import call_ollama_json
from .bulk_sanctions_matcher import find_sanction_candidates

SANCTIONS_SYSTEM_PROMPT = """
You are a bank sanctions screening assistant.
You receive one customer profile and a small list of candidate sanctions records.
Be conservative: only confirm a match if the evidence is strong (birth date and country match,
plus a high name similarity or alias). Always reply in strict JSON like:
{"match": bool, "matchedRecordId": "ID-or-null", "confidence": float, "reason": "text"}.
Do not add commentary outside JSON.
""".strip()


def decide_sanctions(risk_input: Dict[str, Any]) -> Dict[str, Any]:
    candidates = find_sanction_candidates(risk_input)
    payload = {
        "customer": {
            "customerNo": risk_input["customerNo"],
            "fullName": risk_input["fullName"],
            "birthCountry": risk_input.get("birthCountry"),
            "citizenship": risk_input.get("citizenship"),
        },
        "candidates": candidates,
    }

    if not candidates:
        return {"match": False, "matchedRecordId": None, "confidence": 0.0, "reason": "No candidates"}

    result = call_ollama_json(SANCTIONS_SYSTEM_PROMPT, payload)
    return result
