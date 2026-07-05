from internly.db import crud
from internly.db.database import Base
from internly.db.models import Candidate, CompanyIntelRecord, DsaQuestion, EvaluationRecord, InterviewSession
from internly.schemas import CompanyIntel, Evaluation, ResumeProfile


def test_db_round_trip(db_session):
    profile = ResumeProfile(
        skills=["Python"],
        years_experience=2,
        projects=["Mock interview app"],
        education="B.Tech",
        notable_gaps=[],
    )
    candidate = crud.create_candidate(
        db_session,
        resume_text="Python developer",
        profile=profile,
        target_role="SDE",
        target_company="Acme",
    )
    assert candidate.id is not None

    crud.save_company_intel(
        db_session,
        company="Acme",
        role="SDE",
        intel=CompanyIntel(
            interview_rounds=["OA"],
            common_questions=["Arrays"],
            difficulty_notes="Medium",
            culture_notes="Direct feedback",
        ),
    )
    assert crud.get_company_intel(db_session, "acme", "sde") is not None

    question = crud.upsert_dsa_question(
        db_session,
        company="Acme",
        title="Two Sum",
        difficulty="Easy",
        frequency=99.0,
        acceptance="50%",
        link="https://leetcode.com/problems/two-sum/",
    )
    assert crud.get_top_dsa_questions(db_session, "ACME")[0].id == question.id

    interview = crud.create_interview_session(db_session, candidate.id)
    question_index = crud.append_question_to_session(
        db_session,
        interview.id,
        question=question.title,
        question_id=question.id,
    )
    crud.append_interview_turn(
        db_session,
        interview.id,
        question_index,
        role="candidate",
        text="Use a hash map.",
    )
    crud.mark_question_resolved(db_session, interview.id, question_index)
    assert interview.transcript_json[0]["resolved"] is True

    evaluation = crud.save_evaluation(
        db_session,
        interview.id,
        Evaluation(
            technical_score=8,
            communication_score=8,
            role_fit_score=8,
            strengths=["Clear approach"],
            weaknesses=["More edge cases"],
            recommendation="Proceed",
            detailed_feedback="Good DSA reasoning.",
        ),
    )
    assert evaluation.id is not None


def test_models_are_registered():
    table_names = set(Base.metadata.tables)
    assert Candidate.__tablename__ in table_names
    assert CompanyIntelRecord.__tablename__ in table_names
    assert DsaQuestion.__tablename__ in table_names
    assert InterviewSession.__tablename__ in table_names
    assert EvaluationRecord.__tablename__ in table_names

