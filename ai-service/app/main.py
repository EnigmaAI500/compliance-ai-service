from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import io

from .db import get_customer_by_no, update_customer_risk
from .customer_mapper import customer_row_to_profile
from .sanction_matching import match_sanctions_by_name
from .llm_sanctions_risk import llm_score_sanctions
from .ingest_sanctions import ingest_all_sanctions
from .logging_config import get_failure_logger
from .excel_processor import process_excel_batch


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
    sanction_matches = match_sanctions_by_name(profile["full_name"])
    local_blacklist_flag = (row.get("LocalBlackListFlag") == "Y")
    
    # Convert SanctionMatch dataclass objects to dictionaries
    matches = []
    for match in sanction_matches:
        matches.append({
            "match_type": match.match_type,
            "similarity": match.similarity,
            "matched_name": match.matched_name,
            "entry": {
                "id": match.entry.id,
                "name": match.entry.name,
                "list_type": match.entry.list_type,
                "raw": match.entry.raw
            }
        })

    # 4) Risk scoring (rule-based + optional LLM)
    result = llm_score_sanctions(
        profile=profile,
        matches=matches,
        local_blacklist_flag=local_blacklist_flag,
        use_llm=req.use_llm,
    )

    risk_score = int(result.get("risk_score"))
    risk_band = str(result.get("risk_band")).upper()
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


@app.post("/risk/batch-excel")
async def risk_batch_excel(
    file: UploadFile = File(...),
    use_llm: bool = True
):
    """
    Batch risk assessment from Excel file.
    
    **Process:**
    1. Upload Excel file with customer data
    2. System analyzes each customer for risk (sanctions, FATF, PEP, etc.)
    3. Returns same Excel with added columns: RiskScore, RiskFlag, RiskReason
    
    **Required Excel Columns:**
    - CustomerNo
    - DocumentName (customer full name)
    - BirthCountry
    - Citizenship
    
    **Optional Excel Columns:**
    - Nationality
    - MainAccount (occupation/account type)
    - RiskFlag (set to "PEP" for Politically Exposed Persons)
    - LocalBlackListFlag (set to "Y" if on local blacklist)
    - ResidentStatus, District, Region, Locality, Street
    - Pinfl, PassportIssuerCode, PassportIssuerPlace
    - NationalityDesc, CitizenshipDesc
    
    **Output Columns Added:**
    - RiskScore (0-100)
    - RiskFlag (GREEN/YELLOW/RED)
    - RiskReason (semicolon-separated list)
    
    **Parameters:**
    - file: Excel file (.xlsx format)
    - use_llm: Use LLM for enhanced analysis (default: True, slower but more accurate)
    
    **Returns:**
    - Excel file with risk assessment results
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Please upload an Excel file (.xlsx or .xls)"
        )
    
    try:
        # Read file bytes
        file_bytes = await file.read()
        
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        # Log processing start
        failure_logger.info(
            f"Starting batch processing for file: {file.filename}, "
            f"size: {len(file_bytes)} bytes, use_llm: {use_llm}"
        )
        
        # Process the Excel file
        try:
            processed_bytes = process_excel_batch(file_bytes, use_llm=use_llm)
        except ValueError as ve:
            # Validation errors (missing columns, bad format, etc.)
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as ex:
            failure_logger.exception(f"Batch processing failed: {ex}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal error during batch processing: {type(ex).__name__}"
            )
        
        # Log completion
        failure_logger.info(
            f"Batch processing completed for file: {file.filename}, "
            f"output size: {len(processed_bytes)} bytes"
        )
        
        # Return processed file
        output_filename = file.filename.replace('.xlsx', '_risk_assessed.xlsx')
        output_filename = output_filename.replace('.xls', '_risk_assessed.xls')
        
        return StreamingResponse(
            io.BytesIO(processed_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={output_filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as ex:
        failure_logger.exception(f"Unexpected error in batch endpoint: {ex}")
        raise HTTPException(
            status_code=500,
            detail="Unexpected error processing request"
        )
