"""Bounded startup probe: service_started alone does not imply Chroma is ready."""

import time

import httpx

from aura.core.config import settings


def main():
    scheme = "https" if settings.chroma_ssl else "http"
    url = f"{scheme}://{settings.chroma_host}:{settings.chroma_port}/api/v2/heartbeat"
    with httpx.Client(timeout=3, trust_env=False) as client:
        for _ in range(30):
            try:
                client.get(url).raise_for_status()
                return
            except httpx.HTTPError:
                time.sleep(2)
    raise SystemExit(
        "Chroma did not become ready; check CHROMA_HOST/CHROMA_PORT and container logs"
    )


if __name__ == "__main__":
    main()
