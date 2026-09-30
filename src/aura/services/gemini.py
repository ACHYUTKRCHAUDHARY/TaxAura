"""Server-side Gemini integration shared by RAG and the controlled advisor."""

from langchain_google_genai import ChatGoogleGenerativeAI

from aura.core.config import settings


def build_chat_model():
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key.get_secret_value(),
        temperature=0,
        max_retries=0,
        max_output_tokens=2048,
        timeout=settings.ai_timeout_seconds,
    )


def response_text(response) -> str:
    content = response.content
    if isinstance(content, str):
        return content.strip()
    return "\n".join(
        block["text"]
        for block in content
        if isinstance(block, dict)
        and block.get("type") == "text"
        and isinstance(block.get("text"), str)
    ).strip()
