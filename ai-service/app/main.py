from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

from .simple_risk import simple_risk_score
from .ingest_sanctions import ingest_all_sanctions


app = FastAPI(title="Compliance AI Service")


# Ingest sanctions data on startup
@app.on_event("startup")
async def startup_event():
    """Load sanctions data into RAG system when service starts."""
    ingest_all_sanctions()


# ---------- Pydantic models ----------

class OnboardingRequest(BaseModel):
    country_of_birth: str
    residency_country: str
    age: int
    occupation: str
    is_pep: bool = False
    full_name: Optional[str] = None


class RiskResponse(BaseModel):
    risk_score: int
    risk_band: str
    reasons: List[str]


# ---------- Endpoints ----------

@app.get("/health")
def health():
    """Health check endpoint for service monitoring."""
    return {"status": "ok"}


@app.post("/risk/onboarding/llm", response_model=RiskResponse)
def score_onboarding_llm(req: OnboardingRequest):
    """
    Fast rule-based risk scoring using FATF sanctions data.
    
    Analyzes customer onboarding profile using:
    - FATF black/grey list country checks
    - PEP (Politically Exposed Person) status
    - Cash-intensive occupation detection
    - Age risk factors
    
    Returns structured JSON with risk score (0-100), band (GREEN/YELLOW/RED), and reasons.
    """
    profile_dict = req.dict()
    result = simple_risk_score(profile_dict)

    return RiskResponse(
        risk_score=int(result["risk_score"]),
        risk_band=result["risk_band"],
        reasons=[str(r) for r in result.get("reasons", [])],
    )