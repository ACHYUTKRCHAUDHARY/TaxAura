import hashlib
import hmac
import json

import httpx

from aura.core.config import settings


async def publish_workflow_event(event: str, payload: dict) -> bool:
    if not settings.n8n_webhook_url:
        return False
    body = {"event": event, "payload": payload}
    encoded_body = json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(
        settings.n8n_webhook_secret.encode(),
        encoded_body,
        hashlib.sha256,
    ).hexdigest()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            settings.n8n_webhook_url,
            content=encoded_body,
            headers={
                "Content-Type": "application/json",
                "X-TaxAura-Signature": signature,
            },
        )
        response.raise_for_status()
    return True
