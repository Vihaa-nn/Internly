from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document

from internly.config import settings
from internly.llm import get_embedding_model

SESSION_COLLECTION = "interview_sessions"
_CHUNK_TRIM = 800
_legacy_collection_deleted = False
_store = None


def get_session_vector_store():
    global _store, _legacy_collection_deleted
    if _store is None:
        Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
        from langchain_chroma import Chroma

        _store = Chroma(
            collection_name=SESSION_COLLECTION,
            persist_directory=settings.chroma_dir,
            embedding_function=get_embedding_model(),
        )
        if not _legacy_collection_deleted:
            _delete_legacy_company_intel_collection()
            _legacy_collection_deleted = True
    return _store


def _delete_legacy_company_intel_collection() -> None:
    """Remove deprecated company_intel Chroma collection (raw Tavily chunks)."""
    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.chroma_dir)
        client.delete_collection("company_intel")
    except Exception:
        pass


def _session_filter(session_id: int) -> dict:
    return {"session_id": str(session_id)}


def _compound_filter(session_id: int, doc_type: str) -> dict:
    return {"$and": [{"session_id": str(session_id)}, {"doc_type": doc_type}]}


def _trim_chunk(text: str) -> str:
    text = text.strip()
    if len(text) > _CHUNK_TRIM:
        text = text[:_CHUNK_TRIM].rstrip() + "…"
    return text


def _clear_retrieval_caches() -> None:
    retrieve_session_context.cache_clear()
    retrieve_session_context_structured.cache_clear()


def _enrich_metadata(
    session_id: int,
    company: str,
    role: str,
    doc_type: str,
) -> dict[str, str]:
    return {
        "session_id": str(session_id),
        "company": company,
        "role": role,
        "doc_type": doc_type,
    }


def index_session_baseline(
    session_id: int,
    company: str,
    role: str,
    documents: list[Document],
) -> None:
    """Replace all session docs with resume/JD baseline (idempotent on re-start)."""
    if not documents:
        return
    delete_session_context(session_id)
    add_session_documents(session_id, company, role, documents)
    _clear_retrieval_caches()


def add_session_documents(
    session_id: int,
    company: str,
    role: str,
    documents: list[Document],
) -> None:
    if not documents:
        return
    store = get_session_vector_store()
    enriched = []
    for doc in documents:
        doc_type = doc.metadata.get("doc_type", "resume")
        metadata = _enrich_metadata(session_id, company, role, doc_type)
        enriched.append(Document(page_content=doc.page_content, metadata=metadata))
    store.add_documents(enriched)
    _clear_retrieval_caches()


def delete_session_context(session_id: int) -> None:
    store = get_session_vector_store()
    try:
        store._collection.delete(where=_session_filter(session_id))
    except Exception:
        pass
    _clear_retrieval_caches()


@lru_cache(maxsize=256)
def retrieve_session_context(session_id: int, query: str, k: int = 2) -> str:
    store = get_session_vector_store()
    try:
        docs = store.similarity_search(
            query,
            k=k,
            filter=_session_filter(session_id),
        )
    except Exception:
        return "No additional session context retrieved."

    if not docs:
        return "No additional session context retrieved."

    chunks: list[str] = []
    for doc in docs:
        chunks.append(_trim_chunk(doc.page_content))
    return "\n\n".join(chunks)


@lru_cache(maxsize=256)
def retrieve_session_context_structured(
    session_id: int,
    query: str,
    is_intro: bool = False,
) -> str:
    store = get_session_vector_store()
    chunks: list[str] = []

    def _fetch_one(doc_type: str) -> None:
        try:
            docs = store.similarity_search(
                query,
                k=1,
                filter=_compound_filter(session_id, doc_type),
            )
        except Exception:
            return
        if docs:
            chunks.append(_trim_chunk(docs[0].page_content))

    _fetch_one("resume")
    _fetch_one("jd")
    if not is_intro:
        _fetch_one("question")

    if chunks:
        return "\n\n".join(chunks)
    return retrieve_session_context(session_id, query, k=2)
