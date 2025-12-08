import os
import json
from typing import Any, Dict, List
from openai import OpenAI

# SDK auto-reads OPENAI_API_KEY from env, but we allow override
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def call_openai_json(
    system_prompt: str,
    user_payload: Dict[str, Any],
    model: str | None = None,
    max_tokens: int = 800,
) -> Dict[str, Any]:
    """
    Send a structured JSON payload to OpenAI and force JSON output.

    - Uses Chat Completions API with response_format={"type": "json_object"}
      so the model must return valid JSON. :contentReference[oaicite:3]{index=3}
    """
    model_name = model or DEFAULT_MODEL

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(user_payload, ensure_ascii=False),
                }
            ],
        },
    ]

    resp = client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
    )

    content = resp.choices[0].message.content or ""
    try:
        return json.loads(content)
    except json.JSONDecodeError as ex:
        raise ValueError(f"OpenAI returned non-JSON content: {content}") from ex
