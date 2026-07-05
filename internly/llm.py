from __future__ import annotations

import os
# ── CRITICAL FIX: Force the environment variables BEFORE importing LangChain ──
from internly.config import settings

if not settings.gemini_api_key:
    raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

# 1. Force the exact environment variable name that the underlying Google client looks for
os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key

# 2. Mask machine-wide gcloud/GCP default credentials that are hijacking the request
os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

# Now it is completely safe to import the LangChain models
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# ── Singletons — created once, reused across the process lifetime ──────────────
_chat_models: dict[float, ChatGoogleGenerativeAI] = {}
_embedding_model: GoogleGenerativeAIEmbeddings | None = None


def get_chat_model(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    if temperature not in _chat_models:
        # Pass both parameter variations to support any version of langchain-google-genai safely
        _chat_models[temperature] = ChatGoogleGenerativeAI(
            model=settings.gemini_chat_model,
            api_key=settings.gemini_api_key,
            google_api_key=settings.gemini_api_key,
            temperature=temperature,
        )
    return _chat_models[temperature]


def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            api_key=settings.gemini_api_key,
            google_api_key=settings.gemini_api_key,
        )
    return _embedding_model