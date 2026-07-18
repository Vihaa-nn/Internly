import pytest
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from internly.db import crud
from internly.schemas import CompanyIntel, ResumeProfile
from internly.services.research_service import ensure_interview_playbook, prepare_research_context
from internly.services.vector_store import (
    add_session_documents,
    delete_session_context,
    retrieve_session_context,
    retrieve_session_context_structured,
)


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
    crud.save_company_intel(
        db_session,
        company="Acme",
        role="SDE",
        intel=cached_intel,
        interview_playbook_text="Cached playbook text.",
    )

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

    with patch("internly.services.research_service.search_company_interview_intel", return_value="Raw search text") as mock_search, \
         patch("internly.services.research_service.synthesize_company_intel", return_value=synthesized) as mock_synth, \
         patch("internly.services.research_service.generate_interview_playbook", return_value="DSA playbook prose.") as mock_playbook:

        result = prepare_research_context(db_session, company="Acme", role="SDE", allow_search=True)

        assert result.dsa_available is True
        assert result.company_intel == synthesized

        mock_search.assert_called_once_with("Acme", "SDE")
        mock_synth.assert_called_once_with("Acme", "SDE", "Raw search text")
        mock_playbook.assert_called_once_with("Acme", "SDE", "Raw search text")

        db_record = crud.get_company_intel(db_session, "Acme", "SDE")
        assert db_record is not None
        assert db_record.difficulty_notes == "Hard"
        assert db_record.interview_playbook_text == "DSA playbook prose."
        assert db_record.raw_research_text is None


@patch("internly.agents.research_agent.get_chat_model")
def test_generate_interview_playbook_returns_text(mock_get_llm):
    from internly.agents.research_agent import generate_interview_playbook

    mock_response = MagicMock()
    mock_response.content = "Coding round focuses on DSA and complexity analysis."
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_response
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm

    with patch("internly.agents.research_agent.ChatPromptTemplate") as mock_prompt_cls:
        mock_prompt = MagicMock()
        mock_prompt_cls.from_messages.return_value = mock_prompt
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = generate_interview_playbook("Acme", "SDE", "raw tavily text")

    assert "Coding round" in result


@patch("internly.agents.research_agent.get_chat_model")
def test_generate_interview_playbook_handles_list_content(mock_get_llm):
    from internly.agents.research_agent import generate_interview_playbook

    mock_response = MagicMock()
    mock_response.content = [{"type": "text", "text": "Graph and DP focus."}]
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_response
    mock_get_llm.return_value = MagicMock()

    with patch("internly.agents.research_agent.ChatPromptTemplate") as mock_prompt_cls:
        mock_prompt = MagicMock()
        mock_prompt_cls.from_messages.return_value = mock_prompt
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        result = generate_interview_playbook("Google", "SDE-2", "raw")

    assert result == "Graph and DP focus."


@patch("internly.services.vector_store.get_session_vector_store")
def test_add_and_retrieve_session_context(mock_get_store):
    retrieve_session_context.cache_clear()
    mock_store = MagicMock()
    mock_get_store.return_value = mock_store

    mock_doc = MagicMock()
    mock_doc.page_content = "Skills: Python, graphs. JD skill gap: system design."
    mock_store.similarity_search.return_value = [mock_doc]

    add_session_documents(
        42,
        "Acme",
        "SDE",
        [Document(page_content="Skills: Python", metadata={"doc_type": "resume"})],
    )

    mock_store.add_documents.assert_called_once()
    docs = mock_store.add_documents.call_args[0][0]
    assert docs[0].metadata["session_id"] == "42"
    assert docs[0].metadata["doc_type"] == "resume"

    context = retrieve_session_context(42, "graph question follow-up", k=2)
    assert "Python" in context
    mock_store.similarity_search.assert_called_with(
        "graph question follow-up",
        k=2,
        filter={"session_id": "42"},
    )


@patch("internly.services.vector_store.get_session_vector_store")
def test_delete_session_context(mock_get_store):
    retrieve_session_context.cache_clear()
    mock_store = MagicMock()
    mock_store._collection = MagicMock()
    mock_get_store.return_value = mock_store

    delete_session_context(99)

    mock_store._collection.delete.assert_called_once_with(where={"session_id": "99"})


@patch("internly.services.interview_service.assess_candidate_response")
@patch("internly.services.interview_service.retrieve_session_context_structured")
def test_handle_candidate_turn_passes_playbook_and_session_context(
    mock_retrieve,
    mock_assess,
    db_session,
):
    from internly.schemas import InterviewAction
    from internly.services.interview_service import handle_candidate_turn

    mock_retrieve.return_value = "Resume: Kubernetes project."
    mock_assess.return_value = InterviewAction(type="followup", text="Walk me through complexity.")

    profile = ResumeProfile(skills=["Python"], years_experience=2)
    candidate = crud.create_candidate(
        db_session,
        resume_text="resume",
        profile=profile,
        target_role="SDE",
        target_company="Acme",
    )
    question = crud.upsert_dsa_question(
        db_session,
        company="Acme",
        title="Two Sum",
        difficulty="Easy",
        frequency=100,
        acceptance="50%",
        link="https://leetcode.com/problems/two-sum/",
    )
    crud.update_dsa_solution(
        db_session,
        question.id,
        optimal_approach="Hash map",
        optimal_time_complexity="O(n)",
    )
    interview = crud.create_interview_session(db_session, candidate.id)
    question_index = crud.append_question_to_session(
        db_session,
        interview.id,
        question=question.title,
        question_id=question.id,
    )

    action, session_context = handle_candidate_turn(
        db_session,
        interview_session_id=interview.id,
        question_index=question_index,
        candidate_response="hashmap approach",
        resume_profile=profile,
        company_intel=None,
        company="Acme",
        role="SDE",
        interview_playbook="Interviewers push on complexity.",
    )

    assert action.type == "followup"
    assert session_context == "Resume: Kubernetes project."
    mock_assess.assert_called_once()
    kwargs = mock_assess.call_args.kwargs
    assert kwargs["interview_playbook"] == "Interviewers push on complexity."
    assert kwargs["session_context"] == "Resume: Kubernetes project."
    assert kwargs["company"] == "Acme"
    assert kwargs["role"] == "SDE"


def test_ensure_interview_playbook_backfills_empty_playbook_on_cache_hit(db_session):
    cached_intel = CompanyIntel(
        interview_rounds=["OA", "DSA"],
        common_questions=["Arrays"],
        difficulty_notes="Medium",
        culture_notes="Fast-paced",
    )
    crud.save_company_intel(
        db_session,
        company="Acme",
        role="SDE",
        intel=cached_intel,
        interview_playbook_text="",
    )

    with patch(
        "internly.services.research_service.search_company_interview_intel",
        return_value="Raw search text",
    ) as mock_search, patch(
        "internly.services.research_service.generate_interview_playbook",
        return_value="Backfilled playbook prose.",
    ) as mock_playbook:

        result = ensure_interview_playbook(db_session, company="Acme", role="SDE")

    assert result == "Backfilled playbook prose."
    mock_search.assert_called_once_with("Acme", "SDE")
    mock_playbook.assert_called_once_with("Acme", "SDE", "Raw search text")

    db_record = crud.get_company_intel(db_session, "Acme", "SDE")
    assert db_record is not None
    assert db_record.interview_playbook_text == "Backfilled playbook prose."
    assert db_record.interview_rounds == ["OA", "DSA"]
    assert db_record.difficulty_notes == "Medium"


@patch("internly.agents.interview_agent.get_chat_model")
def test_generate_intro_greeting_mentions_resume_project(mock_get_llm):
    from internly.agents.interview_agent import generate_intro_greeting

    mock_response = MagicMock()
    mock_response.content = (
        "Hello! I am Alex, your interviewer for the SDE role at Acme. "
        "I noticed your Kubernetes migration project — impressive work. "
        "Could you briefly introduce yourself?"
    )
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = mock_response
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm

    with patch("internly.agents.interview_agent.ChatPromptTemplate") as mock_prompt_cls:
        mock_prompt = MagicMock()
        mock_prompt_cls.from_messages.return_value = mock_prompt
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        profile = ResumeProfile(
            skills=["Python", "Kubernetes"],
            years_experience=3,
            projects=["Kubernetes migration platform"],
            education="B.Tech CS",
        )
        result = generate_intro_greeting(profile, "Acme", "SDE")

    assert "Kubernetes migration" in result


@patch("internly.services.vector_store.get_session_vector_store")
def test_retrieve_session_context_structured_uses_compound_filters(mock_get_store):
    retrieve_session_context_structured.cache_clear()
    retrieve_session_context.cache_clear()
    mock_store = MagicMock()
    mock_get_store.return_value = mock_store

    resume_doc = MagicMock()
    resume_doc.page_content = "Skills: Python, graphs."
    jd_doc = MagicMock()
    jd_doc.page_content = "JD skill gap: system design."
    question_doc = MagicMock()
    question_doc.page_content = "Question: Two Sum. Difficulty: Easy."

    mock_store.similarity_search.side_effect = [
        [resume_doc],
        [jd_doc],
        [question_doc],
    ]

    context = retrieve_session_context_structured(42, "graph question follow-up", is_intro=False)

    assert "Python" in context
    assert "system design" in context
    assert "Two Sum" in context
    assert mock_store.similarity_search.call_count == 3
    mock_store.similarity_search.assert_any_call(
        "graph question follow-up",
        k=1,
        filter={"$and": [{"session_id": "42"}, {"doc_type": "resume"}]},
    )
    mock_store.similarity_search.assert_any_call(
        "graph question follow-up",
        k=1,
        filter={"$and": [{"session_id": "42"}, {"doc_type": "jd"}]},
    )
    mock_store.similarity_search.assert_any_call(
        "graph question follow-up",
        k=1,
        filter={"$and": [{"session_id": "42"}, {"doc_type": "question"}]},
    )
