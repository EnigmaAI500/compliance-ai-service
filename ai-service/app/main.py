from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from .risk_engine import RiskMLModel

app = FastAPI(title="Compliance AI Service")
ml_model = RiskMLModel("app/ml/risk_model.pkl")

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

    country_risk_score = 90 if req.country_of_birth in high_risk_countries else 20 if req.country_of_birth in medium_risk_countries else 0

    ml_proba = ml_model.predict_proba(country_risk_score, req.age, req.is_pep, cash_job_flag)
    ml_score = int(ml_proba * 100)

    # combine: 70% rules, 30% ML (for example)
    combined_score = int(0.7 * score + 0.3 * ml_score)
    combined_score = max(0, min(combined_score, 100))
    band = map_score_to_band(combined_score)

    reasons.append(f"ML_PROBA={ml_score}")

    return RiskResponse(risk_score=combined_score, risk_band=band, reasons=reasons)