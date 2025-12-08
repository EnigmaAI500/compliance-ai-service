# ai-service/app/llm_utils.py
import json
from typing import Any, Dict
import requests
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
GEN_MODEL = os.getenv("GEN_MODEL", "llama3:8b")


def call_ollama_json(system_prompt: str, user_payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"SYSTEM:\n{system_prompt}\n\nUSER JSON:\n{json.dumps(user_payload, ensure_ascii=False)}"
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": GEN_MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    raw = resp.json()["response"]

    # find first JSON object
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"LLM did not return JSON: {raw}")

    return json.loads(raw[start : end + 1])
