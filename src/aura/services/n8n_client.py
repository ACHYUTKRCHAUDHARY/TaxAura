import httpx

from aura.core.config import settings


async def publish_workflow_event(event: str, payload: dict) -> bool:
    if not settings.n8n_webhook_url:
        return False
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            settings.n8n_webhook_url,
            json={"event": event, "payload": payload},
        )
        response.raise_for_status()
    return True
