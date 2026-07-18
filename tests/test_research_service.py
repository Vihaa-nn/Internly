import pytest
from unittest.mock import MagicMock, patch

from internly.db import crud
from internly.schemas import CompanyIntel
from internly.services.research_service import prepare_research_context


def test_prepare_research_context_cached(db_session):
    crud.upsert_dsa_question(
        db_session,
        company="Acme",
        title="Two Sum",
        difficulty="Easy",
        frequency=100.0,
        acceptance="50%",
        link="https://leetcode.com/problems/two-sum/",
    )

    cached_intel = CompanyIntel(
        interview_rounds=["OA", "DSA"],
        common_questions=["Arrays"],
        difficulty_notes="Medium",
        culture_notes="Fast-paced",
    )
    crud.save_company_intel(db_session, company="Acme", role="SDE", intel=cached_intel)

    with patch("internly.services.research_service.search_company_interview_intel") as mock_search, \
         patch("internly.services.research_service.synthesize_company_intel") as mock_synth, \
         patch("internly.services.research_service.generate_interview_playbook") as mock_playbook:

        result = prepare_research_context(db_session, company="Acme", role="SDE", allow_search=True)

        assert result.dsa_available is True
        assert result.company_intel == cached_intel
        mock_search.assert_not_called()
        mock_synth.assert_not_called()
        mock_playbook.assert_not_called()


def test_prepare_research_context_not_cached_allow_search(db_session):
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

    with patch("internly.services.research_service.search_company_interview_intel", return_value="Raw search text from web") as mock_search, \
         patch("internly.services.research_service.synthesize_company_intel", return_value=synthesized) as mock_synth, \
         patch("internly.services.research_service.generate_interview_playbook", return_value="Playbook text.") as mock_playbook:

        result = prepare_research_context(db_session, company="Acme", role="SDE", allow_search=True)

        assert result.dsa_available is True
        assert result.company_intel == synthesized

        mock_search.assert_called_once_with("Acme", "SDE")
        mock_synth.assert_called_once_with("Acme", "SDE", "Raw search text from web")
        mock_playbook.assert_called_once_with("Acme", "SDE", "Raw search text from web")

        db_record = crud.get_company_intel(db_session, "Acme", "SDE")
        assert db_record is not None
        assert db_record.difficulty_notes == "Hard"
        assert db_record.interview_playbook_text == "Playbook text."
