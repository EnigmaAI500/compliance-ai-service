from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class FileValidation(BaseModel):
    status: str                     # "OK" | "WARN" | "ERROR"
    errors: List[str] = []
    warnings: List[str] = []


class FileMetadata(BaseModel):
    filename: str
    rows_processed: int
    missing_optional_fields: List[str] = []
    upload_country: Optional[str] = None
    validation: FileValidation


class RiskBreakdown(BaseModel):
    sanctions: int = 0
    pep: int = 0
    digitalFootprint: int = 0
    device: int = 0
    profile: int = 0


class RiskInfo(BaseModel):
    score: int
    riskLevel: str                  # LOW / MEDIUM / HIGH / CRITICAL
    confidence: float
    riskDrivers: List[str]
    breakdown: RiskBreakdown


class RiskTag(BaseModel):
    code: str
    label: Optional[str] = None
    severity: str                   # LOW/MEDIUM/HIGH/CRITICAL
    source: Optional[str] = None
    evidence: Dict[str, Any] = {}


class RecommendedAction(BaseModel):
    action: str
    urgency: str                    # LOW/MEDIUM/HIGH/CRITICAL
    reason: str


class CustomerDocument(BaseModel):
    type: Optional[str] = None
    number: Optional[str] = None
    serial: Optional[str] = None
    issuerCode: Optional[str] = None
    issuerPlace: Optional[str] = None
    expiryDate: Optional[str] = None


class ResidencyInfo(BaseModel):
    residentStatus: Optional[str] = None
    district: Optional[str] = None
    region: Optional[str] = None
    locality: Optional[str] = None
    street: Optional[str] = None
    addressCode: Optional[str] = None


class BusinessProfile(BaseModel):
    mainAccount: Optional[str] = None
    mainAccountCategory: Optional[str] = None
    categoryRisk: Optional[str] = None


class SourceFlags(BaseModel):
    riskFlag: Optional[str] = None
    prevRiskScore: Optional[int] = None
    prevRiskReason: Optional[str] = None


class CustomerRiskOutput(BaseModel):
    customerNo: str
    fullName: str
    citizenship: Optional[str] = None
    nationality: Optional[str] = None
    birthCountry: Optional[str] = None
    document: CustomerDocument
    residency: ResidencyInfo
    business_profile: BusinessProfile
    risk: RiskInfo
    tags: List[RiskTag]
    recommendedActions: List[RecommendedAction]
    rawInput: Dict[str, Any]       # whole original row + historical RiskScore/RiskReason


class RiskDistribution(BaseModel):
    LOW: int = 0
    MEDIUM: int = 0
    HIGH: int = 0
    CRITICAL: int = 0


class BatchSummary(BaseModel):
    total_customers: int
    risk_distribution: RiskDistribution
    avg_score: float
    top_risk_drivers: List[str]
    flags_count: Dict[str, int]


class EngineInfo(BaseModel):
    version: str
    data_sources: List[str]
    scoring_model: str
    definitions_version: str


class BulkRiskResponse(BaseModel):
    report_id: str
    generated_at: datetime
    file: FileMetadata
    summary: BatchSummary
    customers: List[CustomerRiskOutput]
    exports: Dict[str, str]
    engine_info: EngineInfo
