"""
Simple rule-based risk scoring without LLM.
Fast and reliable fallback when LLM is too slow.
"""
from typing import Dict, List


def simple_risk_score(profile: dict) -> dict:
    """
    Rule-based risk scoring using FATF data and simple heuristics.
    Returns same format as LLM version.
    """
    score = 0
    reasons: List[str] = []
    
    # Countries
    birth_country = profile.get('country_of_birth', '').lower()
    residence_country = profile.get('residency_country', '').lower()
    
    # FATF Black List countries (very high risk)
    black_list = ['iran', 'north korea', 'myanmar', 'democratic people\'s republic of korea']
    
    # FATF Grey List countries (high risk)
    grey_list = [
        'algeria', 'angola', 'bolivia', 'bulgaria', 'cameroon',
        'côte d\'ivoire', 'democratic republic of congo', 'haiti',
        'kenya', 'lao', 'lebanon', 'monaco', 'namibia', 'nepal',
        'south sudan', 'syria', 'venezuela', 'vietnam', 'yemen'
    ]
    
    # Check birth country
    if any(bc in birth_country for bc in black_list):
        score += 50
        reasons.append(f"FATF_BLACK_LIST_COUNTRY_{birth_country.upper()}")
    elif any(gc in birth_country for gc in grey_list):
        score += 25
        reasons.append(f"FATF_GREY_LIST_COUNTRY_{birth_country.upper()}")
    
    # Check residence country
    if any(bc in residence_country for bc in black_list):
        score += 40
        reasons.append(f"FATF_BLACK_LIST_RESIDENCE_{residence_country.upper()}")
    elif any(gc in residence_country for gc in grey_list):
        score += 20
        reasons.append(f"FATF_GREY_LIST_RESIDENCE_{residence_country.upper()}")
    
    # PEP check
    if profile.get('is_pep'):
        score += 30
        reasons.append("PEP_STATUS_TRUE")
    
    # Cash-intensive occupations
    occupation = profile.get('occupation', '').lower()
    cash_jobs = ['currency_exchange', 'casino', 'night_club', 'money_transfer', 'pawn_shop']
    
    if any(job in occupation for job in cash_jobs):
        score += 15
        reasons.append(f"CASH_INTENSIVE_OCCUPATION_{occupation.upper()}")
    
    # Age factor (very young or very old can be higher risk)
    age = profile.get('age', 0)
    if age < 25 or age > 70:
        score += 5
        reasons.append(f"AGE_RISK_FACTOR_{age}")
    
    # Cap score at 100
    score = min(score, 100)
    
    # Determine risk band
    if score < 40:
        risk_band = "GREEN"
    elif score < 70:
        risk_band = "YELLOW"
    else:
        risk_band = "RED"
    
    return {
        "risk_score": score,
        "risk_band": risk_band,
        "reasons": reasons if reasons else ["NO_RISK_FACTORS"]
    }
