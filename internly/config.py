from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency exists in normal app installs
    load_dotenv = None


if load_dotenv:
    load_dotenv()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")
    gemini_chat_model: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash")
    gemini_embedding_model: str = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-2")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/internly.db")
    chroma_dir: str = os.getenv("CHROMA_DIR", "./data/chroma")
    num_interview_questions: int = int(os.getenv("NUM_INTERVIEW_QUESTIONS", "3"))
    top_dsa_questions: int = int(os.getenv("TOP_DSA_QUESTIONS", "10"))
    sql_echo: bool = os.getenv("SQL_ECHO", "false").lower() == "true"


settings = Settings()
