from __future__ import annotations

from internly.config import settings

# ── Singletons — created once, reused across the process lifetime ──────────────
_chat_models: dict[float, object] = {}
_embedding_model: object | None = None


def get_chat_model(temperature: float = 0.2):
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

    if temperature not in _chat_models:
        from langchain_google_genai import ChatGoogleGenerativeAI

        _chat_models[temperature] = ChatGoogleGenerativeAI(
            model=settings.gemini_chat_model,
            google_api_key=settings.gemini_api_key,
            temperature=temperature,
        )
    return _chat_models[temperature]


def get_embedding_model():
    global _embedding_model
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

    if _embedding_model is None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        _embedding_model = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.gemini_api_key,
        )
    return _embedding_model
