import os 
import math
import requests
from typing import List, Dict

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
GEN_MODEL = os.getenv("GEN_MODEL", "llama3:8b")  # used by generate_answer()


def embed(text: str) -> List[float]:
    """
    Generate a single embedding vector using Ollama's /api/embed endpoint.
    Works with models like 'nomic-embed-text', 'all-minilm', 'embeddinggemma', ...
    """
    payload = {
        "model": EMBED_MODEL,
        "input": text,
    }

    resp = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    # /api/embed returns: { "model": ..., "embeddings": [[...]] }
    embeddings = data.get("embeddings")
    if not embeddings or not embeddings[0]:
        raise ValueError(f"Empty embeddings returned from Ollama: {data}")

    return embeddings[0]

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
