# ai-service/app/bulk_sanctions_matcher.py
from typing import Dict, Any, List
from difflib import SequenceMatcher


def find_sanction_candidates(risk_input: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Enhanced sanctions matching that considers:
    1. Name similarity (existing)
    2. Birth date matching
    3. Birth country/place matching
    
    This helps detect sanctioned persons even if they changed their surname.
    """
    from .sanction_matching import match_sanctions_by_name

    full_name = risk_input.get("fullName") or ""
    birth_date = risk_input.get("birthDate") or ""
    birth_country = (risk_input.get("birthCountry") or "").upper()
    
    # Phase 1: Get candidates by name
    matches = match_sanctions_by_name(full_name)

    candidates: List[Dict[str, Any]] = []
    
    for m in matches[:10]:  # Consider top 10 name matches
        candidate = {
            "id": m.entry.id,
            "names": [m.entry.name],
            "birthDates": [],  # To be filled when sanctions data includes this
            "birthCountries": [],
            "birthPlaces": [],
            "programs": [m.entry.list_type],
            "match_type": m.match_type,
            "similarity": m.similarity,
            "confidence_factors": []
        }
        
        # Calculate confidence based on available data
        confidence = 0.0
        
        # Name similarity contributes to confidence
        if m.similarity >= 0.9:
            confidence += 0.4
            candidate["confidence_factors"].append("High name similarity")
        elif m.similarity >= 0.7:
            confidence += 0.2
            candidate["confidence_factors"].append("Moderate name similarity")
        
        # TODO: When sanctions data includes birth_date and birth_country:
        # if birth_date and birth_date in candidate["birthDates"]:
        #     confidence += 0.4
        #     candidate["confidence_factors"].append("Birth date match")
        #
        # if birth_country and birth_country in candidate["birthCountries"]:
        #     confidence += 0.3
        #     candidate["confidence_factors"].append("Birth country match")
        
        # For now, just name-based confidence
        candidate["overall_confidence"] = confidence
        candidates.append(candidate)
    
    # Sort by confidence and return top 5
    candidates.sort(key=lambda x: x.get("overall_confidence", 0), reverse=True)
    return candidates[:5]


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity between two names.
    Handles different name orderings and formats.
    """
    # Normalize names
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()
    
    # Direct comparison
    direct_similarity = SequenceMatcher(None, n1, n2).ratio()
    
    # Token-based comparison (handles reordering)
    tokens1 = set(n1.split())
    tokens2 = set(n2.split())
    
    if not tokens1 or not tokens2:
        return direct_similarity
    
    # Jaccard similarity
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    token_similarity = len(intersection) / len(union) if union else 0
    
    # Return the maximum of both methods
    return max(direct_similarity, token_similarity)


def enhanced_sanctions_match(
    customer: Dict[str, Any],
    sanction_record: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enhanced matching logic that considers:
    - Name similarity (including aliases)
    - Birth date exact match
    - Birth country/place match
    
    Returns: {"match": bool, "confidence": float, "reason": str}
    """
    confidence = 0.0
    reasons = []
    
    # Extract customer data
    customer_name = (customer.get("fullName") or "").strip()
    customer_birth_date = customer.get("birthDate") or ""
    customer_birth_country = (customer.get("birthCountry") or "").upper()
    
    # Extract sanction record data
    sanction_names = sanction_record.get("names", [])
    sanction_birth_dates = sanction_record.get("birthDates", [])
    sanction_birth_countries = sanction_record.get("birthCountries", [])
    
    # 1. Name matching
    best_name_match = 0.0
    matched_name = None
    
    for sanction_name in sanction_names:
        similarity = calculate_name_similarity(customer_name, sanction_name)
        if similarity > best_name_match:
            best_name_match = similarity
            matched_name = sanction_name
    
    if best_name_match >= 0.8:
        confidence += 0.3
        reasons.append(f"Strong name match with '{matched_name}' (similarity: {best_name_match:.2f})")
    elif best_name_match >= 0.6:
        confidence += 0.15
        reasons.append(f"Moderate name match with '{matched_name}' (similarity: {best_name_match:.2f})")
    else:
        reasons.append(f"Weak name match (similarity: {best_name_match:.2f})")
    
    # 2. Birth date matching (exact match required)
    if customer_birth_date and sanction_birth_dates:
        if customer_birth_date in sanction_birth_dates:
            confidence += 0.4
            reasons.append(f"Birth date exact match: {customer_birth_date}")
        else:
            reasons.append("Birth date does not match")
    
    # 3. Birth country matching
    if customer_birth_country and sanction_birth_countries:
        if customer_birth_country in [c.upper() for c in sanction_birth_countries]:
            confidence += 0.3
            reasons.append(f"Birth country match: {customer_birth_country}")
        else:
            reasons.append("Birth country does not match")
    
    # Decision: match if confidence >= 0.8
    is_match = confidence >= 0.8
    
    return {
        "match": is_match,
        "confidence": confidence,
        "reason": "; ".join(reasons),
        "matched_name": matched_name,
        "name_similarity": best_name_match
    }
