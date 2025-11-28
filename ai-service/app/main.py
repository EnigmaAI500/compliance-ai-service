from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Compliance AI Service")

class OnboardingRequest(BaseModel):
    country_of_birth: str
    residency_country: str
    age: int
    occupation: str
    is_pep: bool = False

class RiskResponse(BaseModel):
    risk_score: int
    risk_band: str
    reasons: List[str]

def map_score_to_band(score: int) -> str:
    if score < 40:
        return "GREEN"
    elif score < 70:
        return "YELLOW"
    return "RED"

@app.post("/risk/onboarding", response_model=RiskResponse)
def score_onboarding(req: OnboardingRequest):
    score = 0
    reasons = []

    # VERY simple rule-based v1
    high_risk_countries = {"IR", "KP", "SY"}  # example; later from DB
    medium_risk_countries = {"RU", "AF"}

    if req.country_of_birth in high_risk_countries or req.residency_country in high_risk_countries:
        score += 50
        reasons.append("HIGH_RISK_COUNTRY")

    if req.country_of_birth in medium_risk_countries or req.residency_country in medium_risk_countries:
        score += 25
        reasons.append("MEDIUM_RISK_COUNTRY")

    if req.is_pep:
        score += 30
        reasons.append("PEP")

    cash_jobs = {"currency_exchange", "casino", "night_club"}
    if req.occupation in cash_jobs:
        score += 15
        reasons.append("CASH_INTENSIVE_OCCUPATION")

    # clamp 0–100
    score = max(0, min(score, 100))
    band = map_score_to_band(score)

    return RiskResponse(risk_score=score, risk_band=band, reasons=reasons)