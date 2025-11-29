from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

from .risk_engine import RiskMLModel
from .rag_engine import embed, cosine, generate_answer
from .storage import doc_store
from .sanctions_loader import (
    compute_country_risk_score,
    is_name_sanctioned,
    get_sanction_matches,
    refresh_sanctions,
    get_sanctions,
)

app = FastAPI(title="Compliance AI Service")
ml_model = RiskMLModel("app/ml/risk_model.pkl")


# ---------- Pydantic models ----------

class OnboardingRequest(BaseModel):
    country_of_birth: str
    residency_country: str
    age: int
    occupation: str
    is_pep: bool = False
    # Optional: if you want to check UN/EU sanctions by name too
    full_name: Optional[str] = None


class RiskResponse(BaseModel):
    risk_score: int
    risk_band: str
    reasons: List[str]


class IngestPayload(BaseModel):
    text: str
    chunk_size: int = 1000  # you can tune


class QAPayload(BaseModel):
    question: str
    top_k: int = 3


class SanctionCheckRequest(BaseModel):
    name: str


class SanctionMatch(BaseModel):
    source: str
    name: str
    raw: str


class SanctionCheckResponse(BaseModel):
    is_sanctioned: bool
    matches: List[SanctionMatch]


# ---------- Helper functions ----------

def map_score_to_band(score: int) -> str:
    if score < 40:
        return "GREEN"
    elif score < 70:
        return "YELLOW"
    return "RED"


# ---------- Risk scoring endpoint ----------

@app.post("/risk/onboarding", response_model=RiskResponse)
def score_onboarding(req: OnboardingRequest):
    """
    Combine:
      - Rule-based features from FATF + simple rules
      - ML probability from risk_model.pkl
    """
    score = 0
    reasons: List[str] = []

    # --- Country risk based on FATF JSON ---
    country_risk_score = compute_country_risk_score(
        req.country_of_birth,
        req.residency_country,
    )

    if country_risk_score >= 90:
        score += 50
        reasons.append("FATF_BLACK_LIST_COUNTRY")
    elif country_risk_score >= 60:
        score += 25
        reasons.append("FATF_GREY_LIST_COUNTRY")
    else:
        reasons.append("FATF_OTHER_COUNTRY")

    # --- PEP flag ---
    if req.is_pep:
        score += 30
        reasons.append("PEP")

    # --- Cash-intensive occupation (still rule-based) ---
    cash_jobs = {"currency_exchange", "casino", "night_club"}
    cash_job_flag = req.occupation in cash_jobs
    if cash_job_flag:
        score += 15
        reasons.append("CASH_INTENSIVE_OCCUPATION")

    # Clamp base score to [0, 100]
    score = max(0, min(score, 100))

    # --- ML part using the same inputs as training ---
    ml_proba = ml_model.predict_proba(
        country_risk_score,  # numeric risk from FATF lists
        req.age,             # numeric
        req.is_pep,          # bool
        cash_job_flag,       # bool
    )
    ml_score = int(ml_proba * 100)

    # Combine: 70% rules + 30% ML
    combined_score = int(0.7 * score + 0.3 * ml_score)
    combined_score = max(0, min(combined_score, 100))
    band = map_score_to_band(combined_score)
    reasons.append(f"ML_PROBA={ml_score}")

    # Optional: bump if name is in UN/EU sanctions
    if req.full_name:
        if is_name_sanctioned(req.full_name):
            reasons.append("MATCH_IN_UN_OR_EU_SANCTIONS_LIST")
            combined_score = max(combined_score, 90)
            band = map_score_to_band(combined_score)

    return RiskResponse(
        risk_score=combined_score,
        risk_band=band,
        reasons=reasons,
    )


# ---------- Sanctions helper endpoints ----------

@app.post("/sanctions/check-name", response_model=SanctionCheckResponse)
def check_name(payload: SanctionCheckRequest):
    """
    Utility endpoint for your UI/other services:
    check if a name is in UN/EU sanctions.
    """
    matches = get_sanction_matches(payload.name)
    return SanctionCheckResponse(
        is_sanctioned=len(matches) > 0,
        matches=[
            SanctionMatch(source=m.source, name=m.name, raw=m.raw) for m in matches
        ],
    )


@app.post("/sanctions/refresh")
def refresh_sanctions_endpoint():
    """
    Force reload sanctions data from the files into memory.
    Call this after you update fatf-countries.json / UN / EU lists.
    """
    data = refresh_sanctions()
    return {
        "status": "ok",
        "fatf_categories": list(data.fatf_categories.keys()),
        "fatf_country_count": len(data.fatf_country_index),
        "un_entries": len(data.un_entries),
        "eu_entries": len(data.eu_entries),
    }


@app.get("/sanctions/stats")
def sanctions_stats():
    """
    Quick sanity check endpoint to see that parsing worked + caching is active.
    """
    data = get_sanctions()
    return {
        "status": "ok",
        "as_of": data.as_of,
        "fatf_categories": list(data.fatf_categories.keys()),
        "fatf_country_count": len(data.fatf_country_index),
        "un_entries": len(data.un_entries),
        "eu_entries": len(data.eu_entries),
    }


# ---------- Health check ----------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Document ingestion / RAG ----------

@app.post("/docs/ingest")
async def ingest_doc(payload: IngestPayload):
    """
    Ingest a long text (e.g., compliance policy) into the in-memory doc store.
    """
    text = payload.text
    chunk_size = payload.chunk_size

    if not text or not text.strip():
        return {"status": "error", "message": "Empty text"}

    # Simple chunking by character length
    chunks: List[str] = [
        text[i : i + chunk_size] for i in range(0, len(text), chunk_size)
    ]

    chunk_ids: List[str] = []
    for chunk in chunks:
        emb = embed(chunk)
        chunk_id = doc_store.add_chunk(chunk, emb)
        chunk_ids.append(chunk_id)

    return {
        "status": "ok",
        "chunks": len(chunk_ids),
        "chunk_ids": chunk_ids,
    }


@app.post("/docs/ask")
async def ask_question(body: QAPayload):
    """
    Simple RAG QA endpoint:
      - embed question
      - retrieve top-k chunks from memory
      - let the LLM answer based on those chunks
    """
    q_emb = embed(body.question)
    top = doc_store.get_top_k(q_emb, k=body.top_k, metric=cosine)

    if not top:
        return {
            "status": "error",
            "message": "No relevant chunks found",
        }

    context = "\n\n---\n\n".join([t["text"] for t in top])
    answer = generate_answer(body.question, context)

    return {
        "status": "ok",
        "answer": answer,
        "snippets": [
            {"id": t["id"], "similarity": t["similarity"], "text": t["text"]}
            for t in top
        ],
    }
