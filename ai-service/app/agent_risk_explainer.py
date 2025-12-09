from typing import Dict, Any
from .azure_openai_client import call_azure_chat_json

RISK_EXPLAIN_SYSTEM_PROMPT = """
You are an AI assistant for a bank’s compliance risk engine.
You receive structured risk evidence for one customer and must:
- Summarize top risk drivers,
- Generate tags with codes, labels, severity, source, and evidence,
- Suggest recommended actions.

Risk levels: LOW, MEDIUM, HIGH, CRITICAL.
Focus on these top drivers:
- FATF high-risk jurisdictions,
- VPN or foreign IP mismatch,
- High-risk occupations (front-company, cash-intensive business).

Return strictly valid JSON like:
{
  "risk": { ... },
  "tags": [ ... ],
  "recommendedActions": [ ... ]
}
Do NOT include any text outside the JSON.
""".strip()


def explain_risk(
    risk_input: Dict[str, Any],
    engine_result: Dict[str, Any],
    sanctions_decision: Dict[str, Any],
) -> Dict[str, Any]:
    payload = {
        "customer": {
            "customerNo": risk_input.get("customerNo"),
            "fullName": risk_input.get("fullName"),
            "citizenship": risk_input.get("citizenship"),
            "nationalityDesc": risk_input.get("nationalityDesc"),
            "birthCountry": risk_input.get("birthCountry"),
        },
        "riskEngine": {
            "score": engine_result["score"],
            "riskLevel": engine_result["riskLevel"],
            "breakdown": engine_result["breakdown"],
            "sanctionsMatch": sanctions_decision,
        },
        "business": risk_input.get("business") or {},
        "residency": risk_input.get("residency") or {},
        "sourceFlags": risk_input.get("sourceFlags") or {},
    }

    return call_azure_chat_json(system_prompt=RISK_EXPLAIN_SYSTEM_PROMPT, payload=payload)
