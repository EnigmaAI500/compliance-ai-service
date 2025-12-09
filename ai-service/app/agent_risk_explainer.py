from typing import Dict, Any
from .azure_openai_client import call_azure_chat_json

RISK_EXPLAIN_SYSTEM_PROMPT = """
You are an AI assistant for a bank's compliance risk engine.
You receive structured risk evidence for one customer and must analyze the risk factors and provide:
1. Enhanced risk drivers (human-readable explanations)
2. Structured tags with proper evidence
3. Recommended actions with urgency levels

Risk levels: LOW, MEDIUM, HIGH, CRITICAL.

Focus on these key risk drivers:
- FATF high-risk jurisdictions (Iran, North Korea, etc.)
- VPN usage or foreign IP mismatch
- High-risk occupations (front-company, cash-intensive business, money service business)
- PEP (Politically Exposed Person) status
- Device reuse patterns
- Suspicious email domains
- Country mismatches between citizenship, IP, and residence

You must return STRICTLY VALID JSON with this exact structure:
{
  "risk": {
    "score": <number from input>,
    "riskLevel": "<LOW|MEDIUM|HIGH|CRITICAL from input>",
    "confidence": <float 0.0-1.0>,
    "riskDrivers": ["driver 1", "driver 2", ...],
    "breakdown": {
      "sanctions": <number from input>,
      "pep": <number from input>,
      "digitalFootprint": <number from input>,
      "device": <number from input>,
      "profile": <number from input>
    }
  },
  "tags": [
    {
      "code": "TAG_CODE",
      "label": "Human readable label",
      "severity": "LOW|MEDIUM|HIGH|CRITICAL",
      "source": "source_system",
      "evidence": {
        "key1": "value1",
        "key2": "value2"
      }
    }
  ],
  "recommendedActions": [
    {
      "action": "Action description",
      "urgency": "LOW|MEDIUM|HIGH|CRITICAL",
      "reason": "Why this action is needed"
    }
  ]
}

IMPORTANT RULES:
1. Keep the score, riskLevel, and breakdown values exactly as provided in the input
2. tags[].evidence MUST be a JSON object/dict, never a string
3. recommendedActions MUST be an array of objects with action, urgency, and reason fields
4. confidence should be between 0.75-0.95 based on data quality
5. Generate 2-5 risk drivers as clear, actionable statements
6. Generate 1-5 tags with proper evidence objects
7. Generate 2-4 recommended actions based on risk level

Tag codes to use:
- FATF_HIGH_RISK: Customer from FATF blacklist country
- FATF_GREY_LIST: Customer from FATF grey list
- COUNTRY_MISMATCH: IP or citizenship doesn't match residency
- VPN_USAGE: VPN detected
- DEVICE_REUSE: Same device used by multiple customers
- HIGH_RISK_OCCUPATION: Cash-intensive or front company business
- SANCTIONS_MATCH: Matched sanctions list
- PEP_MATCH: Politically exposed person
- EMAIL_HIGH_RISK: Suspicious email domain
- LOCAL_BLACKLIST: In local blacklist

DO NOT include any text outside the JSON. The entire response must be valid JSON.
""".strip()


def explain_risk(
    risk_input: Dict[str, Any],
    engine_result: Dict[str, Any],
    sanctions_decision: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Call Azure OpenAI to generate enhanced risk explanation with proper structure.
    Returns a dict with risk, tags, and recommendedActions that match Pydantic models.
    """
    # Build comprehensive payload for LLM
    payload = {
        "customer": {
            "customerNo": risk_input.get("customerNo"),
            "fullName": risk_input.get("fullName"),
            "citizenship": risk_input.get("citizenship"),
            "citizenshipDesc": risk_input.get("citizenshipDesc"),
            "nationality": risk_input.get("nationality"),
            "nationalityDesc": risk_input.get("nationalityDesc"),
            "birthCountry": risk_input.get("birthCountry"),
        },
        "riskEngine": {
            "score": engine_result["score"],
            "riskLevel": engine_result["riskLevel"],
            "breakdown": engine_result["breakdown"],
            "drivers": engine_result.get("drivers", []),
        },
        "sanctionsMatch": {
            "match": sanctions_decision.get("match", False),
            "confidence": sanctions_decision.get("confidence", 0.0),
            "reason": sanctions_decision.get("reason", ""),
            "matchedRecordId": sanctions_decision.get("matchedRecordId"),
        },
        "business": risk_input.get("business") or {},
        "residency": risk_input.get("residency") or {},
        "digital": risk_input.get("digital") or {},
        "sourceFlags": risk_input.get("sourceFlags") or {},
    }

    # Call Azure OpenAI with structured prompt
    try:
        llm_response = call_azure_chat_json(
            system_prompt=RISK_EXPLAIN_SYSTEM_PROMPT, 
            payload=payload,
            temperature=0.1
        )
        
        # Ensure the response has the correct structure
        if "risk" not in llm_response:
            llm_response["risk"] = {}
        
        # Preserve engine scores and ensure all required fields
        llm_response["risk"]["score"] = engine_result["score"]
        llm_response["risk"]["riskLevel"] = engine_result["riskLevel"]
        llm_response["risk"]["breakdown"] = engine_result["breakdown"]
        
        # Ensure confidence exists
        if "confidence" not in llm_response["risk"]:
            llm_response["risk"]["confidence"] = 0.85
            
        # Ensure riskDrivers exists
        if "riskDrivers" not in llm_response["risk"]:
            llm_response["risk"]["riskDrivers"] = engine_result.get("drivers", ["Risk factors detected"])
            
        # Ensure tags is a list
        if "tags" not in llm_response or not isinstance(llm_response["tags"], list):
            llm_response["tags"] = []
            
        # Validate and fix tags structure
        validated_tags = []
        for tag in llm_response.get("tags", []):
            if isinstance(tag, dict):
                # Ensure evidence is a dict
                if "evidence" not in tag:
                    tag["evidence"] = {}
                elif not isinstance(tag["evidence"], dict):
                    tag["evidence"] = {"description": str(tag["evidence"])}
                validated_tags.append(tag)
        llm_response["tags"] = validated_tags
            
        # Ensure recommendedActions is a list of dicts
        if "recommendedActions" not in llm_response or not isinstance(llm_response["recommendedActions"], list):
            llm_response["recommendedActions"] = []
            
        # Validate and fix recommendedActions structure
        validated_actions = []
        for action in llm_response.get("recommendedActions", []):
            if isinstance(action, dict) and "action" in action:
                validated_actions.append(action)
            elif isinstance(action, str):
                validated_actions.append({
                    "action": action,
                    "urgency": engine_result["riskLevel"],
                    "reason": "Based on overall risk assessment"
                })
        llm_response["recommendedActions"] = validated_actions
        
        return llm_response
        
    except Exception as e:
        # Fallback to deterministic response if LLM fails
        return _create_fallback_response(risk_input, engine_result, sanctions_decision)


def _create_fallback_response(
    risk_input: Dict[str, Any],
    engine_result: Dict[str, Any],
    sanctions_decision: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a deterministic fallback response if LLM fails.
    """
    score = engine_result["score"]
    level = engine_result["riskLevel"]
    drivers = engine_result.get("drivers", [])
    
    # Build tags based on deterministic rules
    tags = []
    
    citizenship = (risk_input.get("citizenship") or "").upper()
    if citizenship in ["IRN", "PRK", "SYR"]:
        tags.append({
            "code": "FATF_HIGH_RISK",
            "label": "FATF High-Risk Jurisdiction",
            "severity": "HIGH",
            "source": "country_risk_list",
            "evidence": {"citizenship": citizenship}
        })
    
    if sanctions_decision.get("match"):
        tags.append({
            "code": "SANCTIONS_MATCH",
            "label": "Sanctions List Match",
            "severity": "CRITICAL",
            "source": "sanctions_screening",
            "evidence": {
                "confidence": sanctions_decision.get("confidence", 0.0),
                "reason": sanctions_decision.get("reason", "")
            }
        })
    
    # Build recommended actions based on risk level
    actions = []
    if level == "CRITICAL":
        actions.append({
            "action": "Enhanced Due Diligence",
            "urgency": "CRITICAL",
            "reason": "Critical risk level requires immediate enhanced due diligence"
        })
        actions.append({
            "action": "Escalate to Compliance",
            "urgency": "CRITICAL",
            "reason": "Critical risk requires compliance officer review"
        })
    elif level == "HIGH":
        actions.append({
            "action": "Enhanced Due Diligence",
            "urgency": "HIGH",
            "reason": "High risk level requires enhanced monitoring"
        })
    elif level == "MEDIUM":
        actions.append({
            "action": "Standard Due Diligence with Alerts",
            "urgency": "MEDIUM",
            "reason": "Medium risk requires standard monitoring with alerts"
        })
    else:
        actions.append({
            "action": "Standard Monitoring",
            "urgency": "LOW",
            "reason": "Low risk requires standard monitoring procedures"
        })
    
    return {
        "risk": {
            "score": score,
            "riskLevel": level,
            "confidence": 0.80,
            "riskDrivers": drivers if drivers else ["Standard risk assessment applied"],
            "breakdown": engine_result["breakdown"]
        },
        "tags": tags,
        "recommendedActions": actions
    }
