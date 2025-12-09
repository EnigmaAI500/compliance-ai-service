import json
import os
from functools import lru_cache

from openai import AzureOpenAI


class AzureLlmError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_azure_client() -> AzureOpenAI:
    """
    Singleton Azure OpenAI client.
    Uses API key auth + endpoint (simple, works in containers).
    """
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    if not endpoint or not api_key:
        raise AzureLlmError("Azure OpenAI endpoint or API key is missing")

    return AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=endpoint,
    )


def get_risk_deployment_name() -> str:
    name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_RISK")
    if not name:
        raise AzureLlmError("AZURE_OPENAI_DEPLOYMENT_RISK is not set")
    return name


def call_azure_chat_json(*, system_prompt: str, payload: dict, temperature: float = 0.1) -> dict:
    """
    Helper that sends a JSON payload and expects strict JSON back.
    Used by risk explanation & sanctions agents.
    """
    client = get_azure_client()
    deployment = get_risk_deployment_name()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]

    try:
        # Use Chat Completions with structured JSON output
        resp = client.chat.completions.create(
            model=deployment,  # this is your deployment name
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},  # force JSON
        )
    except Exception as exc:
        # Let FastAPI log this; you'll see it in docker logs
        raise AzureLlmError(f"Azure OpenAI request failed: {exc}") from exc

    content = resp.choices[0].message.content
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise AzureLlmError(f"Invalid JSON from Azure OpenAI: {content}") from exc
