from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from .db import get_customer_by_no, update_customer_risk
from .customer_mapper import customer_row_to_profile
from .sanction_matching import match_sanctions_by_name
from .llm_sanctions_risk import llm_score_sanctions
from .ingest_sanctions import ingest_all_sanctions
from .logging_config import get_failure_logger


app = FastAPI(title="Compliance AI Service")
failure_logger = get_failure_logger()


class RiskRequest(BaseModel):
    customer_no: str
    use_llm: bool = True  # let caller decide if LLM is used


class RiskResponse(BaseModel):
    risk_score: int
    risk_band: str
    reasons: List[str]


@app.on_event("startup")
def on_startup():
    try:
        ingest_all_sanctions()
    except Exception as ex:
        failure_logger.exception("Failed to ingest sanctions data on startup: %s", ex)


@app.post("/risk/from-db", response_model=RiskResponse)
def risk_from_db(req: RiskRequest) -> RiskResponse:
    customer_no = req.customer_no

    # 1) Load customer
    row = get_customer_by_no(customer_no)
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Customer {customer_no} not found in DB",
        )

    # 2) Build profile
    profile = customer_row_to_profile(row)
    profile["full_name"] = (
        (row.get("FirstName") or "") + " " + (row.get("LastName") or "")
    ).strip()

    # 3) Sanctions matching
    matches = match_sanctions_by_name(profile["full_name"])
    local_blacklist_flag = (row.get("LocalBlackListFlag") == "Y")

    # 4) Risk scoring (rule-based + optional LLM)
    result = llm_score_sanctions(
        profile=profile,
        matches=matches,
        local_blacklist_flag=local_blacklist_flag,
        use_llm=req.use_llm,
    )

    risk_score = int(result.get("risk_score", 50))
    risk_band = str(result.get("risk_band", "YELLOW")).upper()
    reasons_list = result.get("reasons") or []
    if not isinstance(reasons_list, list):
        reasons_list = [str(reasons_list)]

    # Sanity: make sure band is one of allowed
    if risk_band not in ("GREEN", "YELLOW", "RED"):
        if risk_score >= 80:
            risk_band = "RED"
        elif risk_score >= 50:
            risk_band = "YELLOW"
        else:
            risk_band = "GREEN"

    risk_reason = "; ".join(reasons_list)

    # 5) Persist back to DB (RiskFlag, RiskScore, RiskReason)
    try:
        update_customer_risk(
            customer_no=customer_no,
            risk_flag=risk_band,
            risk_score=risk_score,
            risk_reason=risk_reason,
        )
    except Exception as ex:
        failure_logger.exception(
            "DB update failed for CustomerNo=%s: %s", customer_no, ex
        )
        raise HTTPException(
            status_code=500,
            detail="Risk computed but DB update failed",
        )

    # 6) Return API response
    return RiskResponse(
        risk_score=risk_score,
        risk_band=risk_band,
        reasons=reasons_list or ["NO_RISK_FACTORS"],
    )
