from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from .simple_risk import simple_risk_score
from .llm_risk import llm_score_onboarding
from .ingest_sanctions import ingest_all_sanctions
from .db import get_customer_by_no, update_customer_risk
from .customer_mapper import customer_row_to_profile
from .logging_config import get_failure_logger


app = FastAPI(title="Compliance AI Service")
failure_logger = get_failure_logger()


# --- Models -----------------------------------------------------------------

class CustomerRiskRequest(BaseModel):
    # NEW flow: only CustomerNo, data taken from Postgres
    customer_no: str
    use_llm: bool = False  # if you want to toggle simple vs LLM


class RiskResponse(BaseModel):
    risk_score: int
    risk_band: str
    reasons: List[str]


# --- Startup: load sanctions / FATF data into memory ------------------------

@app.on_event("startup")
async def startup_event():
    """
    Load sanctions data into RAG system when service starts.
    This populates the in-memory doc_store from /sunction-lists.
    """
    ingest_all_sanctions()


# --- Helper to map bands to DB flags ----------------------------------------

def _risk_band_to_flag(band: str) -> str:
    band = (band or "").upper()
    if band == "RED":
        return "HIGH"
    if band == "YELLOW":
        return "MEDIUM"
    return "LOW"


# --- New endpoint: risk from Postgres by CustomerNo -------------------------

@app.post("/risk/from-db", response_model=RiskResponse)
def risk_from_db(req: CustomerRiskRequest) -> RiskResponse:
    """
    NEW flow used by your .NET backend.

    1. Receives CustomerNo
    2. Loads customer row from public."Customers"
    3. Maps it to a risk profile
    4. Runs risk scoring
    5. Updates RiskFlag / RiskScore / RiskReason in DB
    """
    customer_no = req.customer_no

    # 1) Load from DB
    row = get_customer_by_no(customer_no)
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")

    # 2) Map row → risk profile
    profile = customer_row_to_profile(row)

    # 3) Run risk scoring
    try:
        if req.use_llm:
            result = llm_score_onboarding(profile)
        else:
            result = simple_risk_score(profile)
    except Exception as ex:
        # Risk engine failure → log and propagate error
        failure_logger.exception(
            "Risk scoring failed for CustomerNo=%s: %s", customer_no, ex
        )
        raise HTTPException(status_code=500, detail="Risk scoring failed")

    risk_score = int(result.get("risk_score", 0))
    risk_band = result.get("risk_band", "YELLOW")
    reasons_list = [str(r) for r in result.get("reasons", [])]
    reasons_text = "; ".join(reasons_list)

    # 4) Update DB (if this fails we still log)
    try:
        update_customer_risk(
            customer_no=customer_no,
            risk_flag=_risk_band_to_flag(risk_band),
            risk_score=risk_score,
            risk_reason=reasons_text[:1000],  # avoid huge text in DB
        )
    except Exception as ex:
        failure_logger.exception(
            "DB update failed for CustomerNo=%s: %s", customer_no, ex
        )
        # Business decision: either still return risk or fail request.
        raise HTTPException(status_code=500, detail="Risk computed but DB update failed")

    # 5) Return response to caller
    return RiskResponse(
        risk_score=risk_score,
        risk_band=risk_band,
        reasons=reasons_list or ["NO_RISK_FACTORS"],
    )
