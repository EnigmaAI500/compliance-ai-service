# app/routes/llm_health.py
from fastapi import APIRouter, HTTPException
from ..azure_openai_client import call_azure_chat_json, AzureLlmError

router = APIRouter()


@router.get("/llm/test")
def llm_test():
    try:
        payload = {"ping": "health-check"}
        result = call_azure_chat_json(
            system_prompt="You are a JSON echo bot. Reply with {\"status\":\"ok\"}.",
            payload=payload,
            temperature=0.0,
        )
        return {"ok": True, "result": result}
    except AzureLlmError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
