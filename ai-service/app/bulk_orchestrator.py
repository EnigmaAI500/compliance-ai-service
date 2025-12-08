from typing import Dict, Any, List
from datetime import datetime
import uuid
from statistics import mean

from .bulk_excel_parser import BulkExcelParser
from .bulk_risk_engine import BulkRiskEngine
from .agent_sanctions_decision import decide_sanctions
from .agent_risk_explainer import explain_risk
from .bulk_models import (
    BulkRiskResponse, FileMetadata, FileValidation,
    BatchSummary, RiskDistribution, EngineInfo, CustomerRiskOutput,
    CustomerDocument, ResidencyInfo, BusinessProfile, SourceFlags
)


def process_bulk_excel(file_bytes: bytes, filename: str, upload_country: str = "UZ") -> BulkRiskResponse:
    parser = BulkExcelParser()
    parsed = parser.parse(file_bytes)

    rows_processed = parsed["rows_processed"]
    missing_optional = parsed["missing_optional"]
    inputs: List[Dict[str, Any]] = parsed["customers"]

    risk_engine = BulkRiskEngine()

    customers_output: List[CustomerRiskOutput] = []
    scores_for_avg: List[int] = []
    dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    flags_count: Dict[str, int] = {}

    for ri in inputs:
        engine_result = risk_engine.assess(ri)

        sanctions_decision = decide_sanctions(ri)
        # if hard sanctions match, enforce CRITICAL
        if sanctions_decision.get("match") and sanctions_decision.get("confidence", 0) >= 0.8:
            engine_result["score"] = max(engine_result["score"], 90)
            engine_result["riskLevel"] = "CRITICAL"
            # count SANCTIONS_MATCH tag later in LLM response

        # LLM explanation + tags
        llm_result = explain_risk(ri, engine_result, sanctions_decision)

        risk_obj = llm_result.get("risk", {})
        tags = llm_result.get("tags", [])
        actions = llm_result.get("recommendedActions", [])

        score = int(risk_obj.get("score", engine_result["score"]))
        level = str(risk_obj.get("riskLevel", engine_result["riskLevel"])).upper()

        scores_for_avg.append(score)
        if level in dist:
            dist[level] += 1
        else:
            dist[level] = 1

        for t in tags:
            code = t.get("code", "UNKNOWN")
            flags_count[code] = flags_count.get(code, 0) + 1

        customers_output.append(
            CustomerRiskOutput(
                customerNo=ri["customerNo"],
                fullName=ri["fullName"],
                citizenship=ri.get("citizenship"),
                nationality=ri.get("nationalityDesc") or ri.get("nationality"),
                birthCountry=ri.get("birthCountry"),
                document=CustomerDocument(
                    type=ri["document"].get("type"),
                    number=ri["document"].get("number"),
                    serial=ri["document"].get("serial"),
                    issuerCode=ri["document"].get("issuerCode"),
                    issuerPlace=ri["document"].get("issuerPlace"),
                    expiryDate=ri["document"].get("expiryDate"),
                ),
                residency=ResidencyInfo(
                    residentStatus=ri["residency"].get("residentStatus"),
                    district=ri["residency"].get("district"),
                    region=ri["residency"].get("region"),
                    locality=ri["residency"].get("locality"),
                    street=ri["residency"].get("street"),
                    addressCode=ri["residency"].get("addressCode"),
                ),
                business_profile=BusinessProfile(
                    mainAccount=ri["business"].get("mainAccount"),
                    # you can let LLM set categoryRisk if it returns it
                ),
                risk=risk_obj,
                tags=tags,
                recommendedActions=actions,
                rawInput={
                    **(ri.get("rawRow") or {}),
                    "prevRiskScore": ri["sourceFlags"].get("prevRiskScore"),
                    "prevRiskReason": ri["sourceFlags"].get("prevRiskReason"),
                },
            )
        )

    # summary
    avg_score = float(mean(scores_for_avg)) if scores_for_avg else 0.0

    # top risk drivers – for now pick from flags_count codes and map to friendly labels
    driver_labels_map = {
        "FATF_HIGH_RISK": "FATF high-risk jurisdictions",
        "COUNTRY_MISMATCH": "High-risk jurisdiction mismatch",
        "DEVICE_REUSE": "VPN or foreign IP mismatch",
        "EMAIL_HIGH_RISK": "High-risk email domain",
    }
    # naive top 3
    sorted_flags = sorted(flags_count.items(), key=lambda kv: kv[1], reverse=True)
    top_risk_drivers = []
    for code, _ in sorted_flags[:3]:
        label = driver_labels_map.get(code, code)
        if label not in top_risk_drivers:
            top_risk_drivers.append(label)

    summary = BatchSummary(
        total_customers=len(customers_output),
        risk_distribution=RiskDistribution(**dist),
        avg_score=avg_score,
        top_risk_drivers=top_risk_drivers,
        flags_count=flags_count,
    )

    validation = FileValidation(
        status="OK" if not missing_optional else "WARN",
        errors=[],
        warnings=[
            f"Missing optional columns: {', '.join(missing_optional)}"
        ] if missing_optional else [],
    )

    file_meta = FileMetadata(
        filename=filename,
        rows_processed=rows_processed,
        missing_optional_fields=missing_optional,
        upload_country=upload_country,
        validation=validation,
    )

    report_id = f"rpt_{datetime.utcnow().strftime('%Y_%m_%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    engine_info = EngineInfo(
        version="compliance-engine-v1.5.0",
        data_sources=["OFAC", "UN", "EU", "PEP-DB-v3", "GeoRisk-2025"],
        scoring_model="weighted-rules+ml",
        definitions_version="2025.12",
    )

    exports = {
        "pdf": f"/exports/{report_id}/report.pdf",
        "excel": f"/exports/{report_id}/details.xlsx",
        "json": f"/exports/{report_id}/raw.json",
    }

    return BulkRiskResponse(
        report_id=report_id,
        generated_at=datetime.utcnow(),
        file=file_meta,
        summary=summary,
        customers=customers_output,
        exports=exports,
        engine_info=engine_info,
    )
