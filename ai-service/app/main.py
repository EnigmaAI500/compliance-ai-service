from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from .risk_engine import RiskMLModel
from .rag_engine import embed, cosine, generate_answer
from .storage import doc_store

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

    
class IngestPayload(BaseModel):
    text: str
    chunk_size: int = 1000  # you can tune


class QAPayload(BaseModel):
    question: str
    top_k: int = 3

def map_score_to_band(score: int) -> str:
    if score < 40:
        return "GREEN"
    elif score < 70:
        return "YELLOW"
    return "RED"

@app.post("/risk/onboarding", response_model=RiskResponse)
def score_onboarding(req: OnboardingRequest):
    score = 0
    reasons: List[str] = []

    # Example sets – tune later or load from DB/config
    high_risk_countries = {"IR", "KP", "SY"}
    medium_risk_countries = {"RU", "AF"}

    # ----- Rule-based scoring -----
    # Country risk (birth or residency)
    if (
        req.country_of_birth in high_risk_countries
        or req.residency_country in high_risk_countries
    ):
        score += 50
        reasons.append("HIGH_RISK_COUNTRY")
    elif (
        req.country_of_birth in medium_risk_countries
        or req.residency_country in medium_risk_countries
    ):
        score += 25
        reasons.append("MEDIUM_RISK_COUNTRY")

    # PEP
    if req.is_pep:
        score += 30
        reasons.append("PEP")

    # Cash-intensive occupation
    cash_jobs = {"currency_exchange", "casino", "night_club"}
    cash_job_flag = req.occupation in cash_jobs
    if cash_job_flag:
        score += 15
        reasons.append("CASH_INTENSIVE_OCCUPATION")

    # Clamp to 0–100
    score = max(0, min(score, 100))

    # ----- ML part (optional) -----
    # Derive a numeric country risk score for the model
    if (
        req.country_of_birth in high_risk_countries
        or req.residency_country in high_risk_countries
    ):
        country_risk_score = 90
    elif (
        req.country_of_birth in medium_risk_countries
        or req.residency_country in medium_risk_countries
    ):
        country_risk_score = 50
    else:
        country_risk_score = 10

    # Call ML model: must match the training feature order
    ml_proba = ml_model.predict_proba(
        country_risk_score,       # numeric
        req.age,                  # numeric
        req.is_pep,               # bool
        cash_job_flag,            # bool
    )
    ml_score = int(ml_proba * 100)

    # Combine: e.g. 70% rules + 30% ML
    combined_score = int(0.7 * score + 0.3 * ml_score)
    combined_score = max(0, min(combined_score, 100))
    band = map_score_to_band(combined_score)

    reasons.append(f"ML_PROBA={ml_score}")

    return RiskResponse(
        risk_score=combined_score,
        risk_band=band,
        reasons=reasons,
    )


# ---- Health check ----
@app.get("/health")
def health():
    return {"status": "ok"}




# ---- Document ingestion ----
@app.post("/docs/ingest")
async def ingest_doc(payload: IngestPayload):
    """
    Ingest a long text (e.g., compliance policy).
    For hackathon: backend can send plain text instead of PDF.
    We:
      - split into chunks
      - get embedding for each chunk
      - store in memory via doc_store
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
        emb = embed(chunk)  # from rag_engine
        chunk_id = doc_store.add_chunk(chunk, emb)
        chunk_ids.append(chunk_id)

    return {
        "status": "ok",
        "chunks_ingested": len(chunks),
        "chunk_ids": chunk_ids,
    }


# ---- Question answering ----
@app.post("/docs/qa")
def docs_qa(body: QAPayload):
    """
    Given a question:
      - embed question
      - find top_k similar chunks
      - call local LLM with those chunks as CONTEXT
      - return answer + snippets
    """
    if not doc_store.chunks:
        return {
            "status": "error",
            "message": "No documents ingested yet",
        }

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
