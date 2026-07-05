import pytest
from unittest.mock import MagicMock, patch

from internly.db import crud
from internly.schemas import CompanyIntel
from internly.services.research_service import prepare_research_context
from internly.services.vector_store import index_company_intel_text, retrieve_company_context


def test_prepare_research_context_cached(db_session):
    # Pre-populate some DSA questions for the company so dsa_available will be True
    crud.upsert_dsa_question(
        db_session,
        company="Acme",
        title="Two Sum",
        difficulty="Easy",
        frequency=100.0,
        acceptance="50%",
        link="https://leetcode.com/problems/two-sum/",
    )
    
    # Save company intel to the DB
    cached_intel = CompanyIntel(
        interview_rounds=["OA", "DSA"],
        common_questions=["Arrays"],
        difficulty_notes="Medium",
        culture_notes="Fast-paced",
    )
    crud.save_company_intel(db_session, company="Acme", role="SDE", intel=cached_intel)
    
    # Mock external calls to verify they are NOT called when cache hit occurs
    with patch("internly.services.research_service.search_company_interview_intel") as mock_search, \
         patch("internly.services.research_service.synthesize_company_intel") as mock_synth, \
         patch("internly.services.research_service.index_company_intel_text") as mock_index:
        
        result = prepare_research_context(db_session, company="Acme", role="SDE", allow_search=True)
        
        assert result.dsa_available is True
        assert result.company_intel == cached_intel
        mock_search.assert_not_called()
        mock_synth.assert_not_called()
        mock_index.assert_not_called()


def test_prepare_research_context_not_cached_allow_search(db_session):
    # Pre-populate some DSA questions for the company
    crud.upsert_dsa_question(
        db_session,
        company="Acme",
        title="Two Sum",
        difficulty="Easy",
        frequency=100.0,
        acceptance="50%",
        link="https://leetcode.com/problems/two-sum/",
    )

    synthesized = CompanyIntel(
        interview_rounds=["Technical Interview"],
        common_questions=["Linked List"],
        difficulty_notes="Hard",
        culture_notes="Detail-oriented",
    )
    
    # Mock the search agent and vector indexing
    with patch("internly.services.research_service.search_company_interview_intel", return_value="Raw search text from web") as mock_search, \
         patch("internly.services.research_service.synthesize_company_intel", return_value=synthesized) as mock_synth, \
         patch("internly.services.research_service.index_company_intel_text") as mock_index:
        
        result = prepare_research_context(db_session, company="Acme", role="SDE", allow_search=True)
        
        assert result.dsa_available is True
        assert result.company_intel == synthesized
        
        mock_search.assert_called_once_with("Acme", "SDE")
        mock_synth.assert_called_once_with("Acme", "SDE", "Raw search text from web")
        mock_index.assert_called_once_with("Acme", "SDE", "Raw search text from web")
        
        # Verify it saved it to the database
        db_record = crud.get_company_intel(db_session, "Acme", "SDE")
        assert db_record is not None
        assert db_record.difficulty_notes == "Hard"


@patch("internly.services.vector_store.get_company_intel_vector_store")
def test_index_company_intel_text(mock_get_store):
    mock_store = MagicMock()
    mock_get_store.return_value = mock_store
    
    index_company_intel_text("Acme", "SDE", "Some raw company research text.")
    
    mock_get_store.assert_called_once()
    mock_store.add_documents.assert_called_once()
    args, kwargs = mock_store.add_documents.call_args
    docs = args[0]
    assert len(docs) == 1
    assert docs[0].page_content == "Some raw company research text."
    assert docs[0].metadata == {"company": "Acme", "role": "SDE"}


@patch("internly.services.vector_store.get_company_intel_vector_store")
def test_retrieve_company_context(mock_get_store):
    mock_store = MagicMock()
    mock_get_store.return_value = mock_store
    
    mock_doc1 = MagicMock()
    mock_doc1.page_content = "Chunk 1"
    mock_doc2 = MagicMock()
    mock_doc2.page_content = "Chunk 2"
    mock_store.similarity_search.return_value = [mock_doc1, mock_doc2]
    
    context = retrieve_company_context("Acme", "SDE", "Two Sum", k=2)
    
    assert context == "Chunk 1\n\nChunk 2"
    mock_store.similarity_search.assert_called_once_with(
        "Two Sum",
        k=2,
        filter={"$and": [{"company": "Acme"}, {"role": "SDE"}]}
    )
