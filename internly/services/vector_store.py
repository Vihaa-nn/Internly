from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document

from internly.config import settings
from internly.llm import get_embedding_model

# ── Singleton Chroma store — created once per process ─────────────────────────
_store = None


def get_company_intel_vector_store():
    global _store
    if _store is None:
        Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
        from langchain_chroma import Chroma

        _store = Chroma(
            collection_name="company_intel",
            persist_directory=settings.chroma_dir,
            embedding_function=get_embedding_model(),
        )
    return _store


def index_company_intel_text(company: str, role: str, raw_text: str) -> None:
    if not raw_text.strip():
        return
    store = get_company_intel_vector_store()
    chunks = _chunk_text(raw_text)
    documents = [
        Document(page_content=chunk, metadata={"company": company, "role": role})
        for chunk in chunks
    ]
    store.add_documents(documents)
    # Bust the retrieval cache for this company/role so fresh docs are visible
    retrieve_company_context.cache_clear()


@lru_cache(maxsize=256)
def retrieve_company_context(company: str, role: str, query: str, k: int = 3) -> str:
    """
    Cached vector-store retrieval.
    The same (company, role, query) triple always returns the same docs,
    so we cache aggressively — this eliminates the embedding API round-trip
    on every interview message after the first one for a given question.
    """
    store = get_company_intel_vector_store()
    docs = store.similarity_search(
        query,
        k=k,
        filter={"$and": [{"company": company}, {"role": role}]},
    )
    return "\n\n".join(doc.page_content for doc in docs)


def _chunk_text(text: str, chunk_size: int = 1800, overlap: int = 200) -> list[str]:
    normalized = text.strip()
    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = max(end - overlap, 0)
    return chunks
