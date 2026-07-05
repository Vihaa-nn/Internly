from internly.db import crud
from internly.services.research_service import prepare_research_context


def test_missing_dsa_blocks_interview_without_search(db_session):
    result = prepare_research_context(
        db_session,
        company="UnknownCo",
        role="SDE",
        allow_search=False,
    )
    assert result.dsa_available is False
    assert "cannot start" in result.dsa_message


def test_dsa_company_lookup_is_normalized(db_session):
    crud.upsert_dsa_question(
        db_session,
        company="Acme Tech",
        title="Valid Parentheses",
        difficulty="Easy",
        frequency=80,
        acceptance="45%",
        link="https://leetcode.com/problems/valid-parentheses/",
    )
    result = prepare_research_context(
        db_session,
        company="acme-tech",
        role="SDE",
        allow_search=False,
    )
    assert result.dsa_available is True
    assert result.dsa_questions[0].title == "Valid Parentheses"

