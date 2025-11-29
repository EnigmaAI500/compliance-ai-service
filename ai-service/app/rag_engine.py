import math
import requests
from typing import List, Dict

OLLAMA_URL = "http://ollama:11434"
TIMEOUT = 60  # 60 seconds timeout

def embed(text: str) -> List[float]:
    resp = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text},
        timeout=TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()["embedding"]

def cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x*x for x in a))
    norm_b = math.sqrt(sum(x*x for x in b))
    return dot / (norm_a * norm_b + 1e-9)

def generate_answer(question: str, context: str) -> str:
    prompt = f"""You are a compliance assistant for Agrobank.
Use only the CONTEXT below to answer the QUESTION.
If you don't know, say you don't know.

CONTEXT:
{context}

QUESTION:
{question}
"""
    print(f"🤖 Calling LLM with prompt length: {len(prompt)} chars")
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": "llama3:8b", "prompt": prompt, "stream": False},
        timeout=120  # 2 minutes for LLM generation
    )
    resp.raise_for_status()
    result = resp.json()["response"]
    print(f"✅ LLM response received: {len(result)} chars")
    return result
