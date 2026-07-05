from internly.db import crud
from internly.schemas import ResumeProfile
from internly.services.interview_service import handle_candidate_turn
from internly.utils import is_underexplained_strategy_answer


def test_underexplained_strategy_detection():
    assert is_underexplained_strategy_answer("I would use a hashmap")
    assert is_underexplained_strategy_answer("Use two pointers")
    assert not is_underexplained_strategy_answer(
        "I would use a hashmap, iterate through nums, check complement, return indices, "
        "otherwise store value to index. Time is O(n), space is O(n)."
    )


def test_hashmap_only_answer_gets_followup_not_accept(db_session):
    profile = ResumeProfile(skills=["Python"], years_experience=1)
    candidate = crud.create_candidate(
        db_session,
        resume_text="Python DSA candidate",
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
    interview = crud.create_interview_session(db_session, candidate.id)
    question_index = crud.append_question_to_session(
        db_session,
        interview.id,
        question=question.title,
        question_id=question.id,
    )

    action = handle_candidate_turn(
        db_session,
        interview_session_id=interview.id,
        question_index=question_index,
        candidate_response="I would use a hashmap",
        resume_profile=profile,
        company_intel=None,
        company="Acme",
        role="SDE",
    )

    assert action.type == "followup"
    assert "pseudocode" in action.text.lower()
    assert interview.transcript_json[0]["resolved"] is False
