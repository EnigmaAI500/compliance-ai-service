# ai-service/app/bulk_sanctions_matcher.py
from typing import Dict, Any, List

def find_sanction_candidates(risk_input: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Phase 1: call existing match_sanctions_by_name() and wrap results.
    Phase 2: extend with birthDate + birthCountry criteria once your
    sanctions data includes those attributes.
    """
    from .sanction_matching import match_sanctions_by_name

    full_name = risk_input.get("fullName") or ""
    matches = match_sanctions_by_name(full_name)

    candidates: List[Dict[str, Any]] = []
    for m in matches[:5]:   # top 5 only
        candidates.append(
            {
                "id": m.entry.id,
                "names": [m.entry.name],
                "birthDates": [],       # to be filled once available
                "birthCountries": [],
                "birthPlaces": [],
                "programs": [m.entry.list_type],
                "match_type": m.match_type,
                "similarity": m.similarity,
            }
        )
    return candidates
