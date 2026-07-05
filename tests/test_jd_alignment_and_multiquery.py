import pytest
from unittest.mock import MagicMock, patch

from internly.db import crud
from internly.schemas import ResumeProfile, CompanyIntel
from internly.agents.research_agent import search_company_interview_intel
from internly.agents.interview_agent import assess_candidate_response
from internly.pipeline import resume_profile_from_candidate


def test_resume_profile_extended_fields():
    profile = ResumeProfile(
        skills=["Python"],
        years_experience=2.0,
        projects=["Proj1"],
        education="MS",
        notable_gaps=[],
        target_languages=["Python", "C++"],
        alignment_signals=["Strong Python background"],
        skill_gaps=["No Java experience"]
    )
    assert profile.target_languages == ["Python", "C++"]
    assert profile.alignment_signals == ["Strong Python background"]
    assert profile.skill_gaps == ["No Java experience"]


def test_candidate_db_persistence(db_session):
    profile = ResumeProfile(
        skills=["Python", "Go"],
        years_experience=3.5,
        projects=["App"],
        education="BS",
        notable_gaps=["Gap"],
        target_languages=["Go", "SQL"],
        alignment_signals=["Match on Go"],
        skill_gaps=["Lacks Rust"]
    )
    candidate = crud.create_candidate(
        db_session,
        resume_text="Resume content",
        profile=profile,
        target_role="SDE-2",
        target_company="Stripe",
        job_description="Go developer with SQL knowledge"
    )
    db_session.commit()

    assert candidate.id is not None
    assert candidate.job_description == "Go developer with SQL knowledge"
    assert candidate.target_languages == ["Go", "SQL"]
    assert candidate.alignment_signals == ["Match on Go"]
    assert candidate.skill_gaps == ["Lacks Rust"]

    # Test loading from candidate
    loaded_profile = resume_profile_from_candidate(candidate)
    assert loaded_profile.target_languages == ["Go", "SQL"]
    assert loaded_profile.alignment_signals == ["Match on Go"]
    assert loaded_profile.skill_gaps == ["Lacks Rust"]


@patch("internly.agents.research_agent.settings")
def test_search_company_interview_intel_multi_query(mock_settings):
    mock_settings.tavily_api_key = "dummy-tavily-key"
    
    # We mock the tool invocation to return dummy results for each query
    mock_results_1 = [{"title": "alpha", "url": "url1", "content": "apple"}]
    mock_results_2 = [{"title": "beta", "url": "url2", "content": "banana"}]
    mock_results_3 = [{"title": "gamma", "url": "url1", "content": "cherry"}] # URL duplicate

    call_count = 0
    def mock_invoke(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_results_1
        elif call_count == 2:
            return mock_results_2
        else:
            return mock_results_3

    # also patch TavilySearch if it can be imported, else pass
    mock_instance = MagicMock()
    mock_instance.invoke.side_effect = mock_invoke
    
    with patch("langchain_community.tools.tavily_search.TavilySearchResults") as MockTavilySearchResults:
        MockTavilySearchResults.return_value = mock_instance
        
        try:
            import langchain_tavily
            patcher = patch("langchain_tavily.TavilySearch")
            MockTavilySearch = patcher.start()
            MockTavilySearch.return_value = mock_instance
        except ImportError:
            patcher = None

        res = search_company_interview_intel("Acme", "SDE", max_results=3)

        if patcher:
            patcher.stop()

        print(f"DEBUG - res: {res}")
        # Because of parallel execution, either alpha or gamma will be processed first and cached.
        # The other will be deduplicated. We verify exactly one is present using XOR.
        assert ("alpha" in res) != ("gamma" in res)
        assert "beta" in res
        # Verify it invoked 3 times (multi-query search)
        assert mock_instance.invoke.call_count == 3


@patch("internly.agents.interview_agent.get_chat_model")
def test_assess_candidate_response_excludes_jd_alignment(mock_get_chat_model):
    mock_llm = MagicMock()
    mock_get_chat_model.return_value = mock_llm
    
    profile = ResumeProfile(
        skills=["Python"],
        years_experience=2.0,
        projects=["Proj1"],
        education="MS",
        notable_gaps=[],
        target_languages=["Python"],
        alignment_signals=["Has Python experience"],
        skill_gaps=["Lacks Java"]
    )
    
    # Mock the LLM chain execution to return a structured output mock
    mock_chain = MagicMock()
    mock_llm.with_structured_output.return_value = mock_chain
    mock_chain.return_value = MagicMock()

    assess_candidate_response(
        question="Two Sum",
        candidate_response="I would use a hashmap",
        turns=[],
        resume_profile=profile,
        company_intel=None,
        optimal_approach=None,
        optimal_time_complexity=None
    )

    # Verify the dictionary sent to the LLM (via prompt compilation)
    args, kwargs = mock_chain.call_args
    prompt_value = args[0]
    messages = prompt_value.to_messages()
    
    # The human message is the second message (index 1)
    human_msg = messages[1].content
    
    # Verify that target_languages is present but alignment_signals and skill_gaps are excluded
    assert "target_languages" in human_msg
    assert "alignment_signals" not in human_msg
    assert "skill_gaps" not in human_msg
