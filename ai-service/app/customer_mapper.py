from typing import Any, Dict


def customer_row_to_profile(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "country_of_birth": row.get("BirthCountry") or "",
        "residency_country": (row.get("Citizenship") or row.get("Nationality") or ""),
        "occupation": (row.get("MainAccount") or "").lower(),
        "is_pep": (row.get("RiskFlag") == "PEP"),  # you can refine this later

        # extra info if you want to use it in LLM/RAG later
        "nationality": row.get("Nationality"),
        "citizenship": row.get("Citizenship"),
        "resident_status": row.get("ResidentStatus"),
        "district": row.get("District"),
        "region": row.get("Region"),
        "locality": row.get("Locality"),
        "street": row.get("Street"),
    }
