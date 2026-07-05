from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from internly.db.models import (
    Candidate,
    CompanyIntelRecord,
    DsaQuestion,
    EvaluationRecord,
    InterviewSession,
)
from internly.schemas import CompanyIntel, Evaluation, ResumeProfile
from internly.utils import normalize_name


def create_candidate(
    session: Session,
    *,
    resume_text: str,
    profile: ResumeProfile,
    target_role: str,
    target_company: str,
    job_description: str | None = None,
) -> Candidate:
    candidate = Candidate(
        resume_text=resume_text,
        skills=profile.skills,
        years_experience=profile.years_experience,
        projects=profile.projects,
        education=profile.education,
        notable_gaps=profile.notable_gaps,
        target_role=target_role,
        target_company=target_company,
        job_description=job_description,
        target_languages=profile.target_languages,
        alignment_signals=profile.alignment_signals,
        skill_gaps=profile.skill_gaps,
    )
    session.add(candidate)
    session.flush()
    return candidate


def get_company_intel(session: Session, company: str, role: str) -> CompanyIntelRecord | None:
    stmt = select(CompanyIntelRecord).where(
        CompanyIntelRecord.company_normalized == normalize_name(company),
        CompanyIntelRecord.role_normalized == normalize_name(role),
    )
    return session.scalar(stmt)


def save_company_intel(
    session: Session,
    *,
    company: str,
    role: str,
    intel: CompanyIntel,
    raw_research_text: str | None = None,
) -> CompanyIntelRecord:
    existing = get_company_intel(session, company, role)
    if existing:
        existing.interview_rounds = intel.interview_rounds
        existing.common_questions = intel.common_questions
        existing.difficulty_notes = intel.difficulty_notes
        existing.culture_notes = intel.culture_notes
        existing.raw_research_text = raw_research_text
        existing.last_updated = datetime.utcnow()
        session.flush()
        return existing

    record = CompanyIntelRecord(
        company=company,
        role=role,
        company_normalized=normalize_name(company),
        role_normalized=normalize_name(role),
        interview_rounds=intel.interview_rounds,
        common_questions=intel.common_questions,
        difficulty_notes=intel.difficulty_notes,
        culture_notes=intel.culture_notes,
        raw_research_text=raw_research_text,
    )
    session.add(record)
    session.flush()
    return record


def upsert_dsa_question(
    session: Session,
    *,
    company: str,
    title: str,
    difficulty: str | None = None,
    frequency: float | None = None,
    acceptance: str | None = None,
    link: str | None = None,
) -> DsaQuestion:
    company_normalized = normalize_name(company)
    stmt = select(DsaQuestion).where(
        DsaQuestion.company_normalized == company_normalized,
        DsaQuestion.title == title,
        DsaQuestion.link == link,
    )
    existing = session.scalar(stmt)
    if existing:
        existing.difficulty = difficulty
        existing.frequency = frequency
        existing.acceptance = acceptance
        session.flush()
        return existing

    question = DsaQuestion(
        company=company,
        company_normalized=company_normalized,
        title=title,
        difficulty=difficulty,
        frequency=frequency,
        acceptance=acceptance,
        link=link,
    )
    session.add(question)
    session.flush()
    return question


def get_top_dsa_questions(session: Session, company: str, limit: int = 10) -> list[DsaQuestion]:
    stmt = (
        select(DsaQuestion)
        .where(DsaQuestion.company_normalized == normalize_name(company))
        .order_by(func.coalesce(DsaQuestion.frequency, 0).desc(), DsaQuestion.title.asc())
        .limit(limit)
    )
    return list(session.scalars(stmt))


def get_dsa_question(session: Session, question_id: int) -> DsaQuestion:
    question = session.get(DsaQuestion, question_id)
    if not question:
        raise ValueError(f"DSA question {question_id} was not found.")
    return question


def update_dsa_solution(
    session: Session,
    question_id: int,
    *,
    optimal_approach: str,
    optimal_time_complexity: str,
) -> DsaQuestion:
    question = get_dsa_question(session, question_id)
    question.optimal_approach = optimal_approach
    question.optimal_time_complexity = optimal_time_complexity
    session.flush()
    return question


def create_interview_session(
    session: Session,
    candidate_id: int,
    include_greeting: bool = False,
) -> InterviewSession:
    if include_greeting:
        candidate = session.get(Candidate, candidate_id)
        role = candidate.target_role if candidate else "Software Engineer"
        company = candidate.target_company if candidate else "the company"
        
        welcome_text = (
            f"Hello! I am Alex, and I will be conducting your mock interview today for the {role} "
            f"position at {company}. I have reviewed your resume. Before we jump into the technical "
            "Data Structures and Algorithms problems, could you briefly introduce yourself "
            "and share some details about your background and recent projects?"
        )
        
        transcript = [
            {
                "question_id": None,
                "question": "Introduction",
                "turns": [
                    {
                        "role": "agent",
                        "text": welcome_text,
                        "type": "followup"
                    }
                ],
                "resolved": False
            }
        ]
    else:
        transcript = []

    record = InterviewSession(candidate_id=candidate_id, transcript_json=transcript)
    session.add(record)
    session.flush()
    return record


def append_question_to_session(
    session: Session,
    session_id: int,
    *,
    question: str,
    question_id: int | None = None,
) -> int:
    record = _get_interview_session(session, session_id)
    transcript = list(record.transcript_json or [])
    transcript.append(
        {
            "question_id": question_id,
            "question": question,
            "turns": [],
            "resolved": False,
        }
    )
    record.transcript_json = transcript
    session.flush()
    return len(transcript) - 1


def append_interview_turn(
    session: Session,
    session_id: int,
    question_index: int,
    *,
    role: str,
    text: str,
    turn_type: str | None = None,
) -> InterviewSession:
    record = _get_interview_session(session, session_id)
    transcript = list(record.transcript_json or [])
    if question_index >= len(transcript):
        raise ValueError(f"Question index {question_index} does not exist.")
    question_log = dict(transcript[question_index])
    turns = list(question_log.get("turns", []))
    turn = {"role": role, "text": text}
    if turn_type:
        turn["type"] = turn_type
    turns.append(turn)
    question_log["turns"] = turns
    transcript[question_index] = question_log
    record.transcript_json = transcript
    session.flush()
    return record


def mark_question_resolved(session: Session, session_id: int, question_index: int) -> InterviewSession:
    record = _get_interview_session(session, session_id)
    transcript = list(record.transcript_json or [])
    if question_index >= len(transcript):
        raise ValueError(f"Question index {question_index} does not exist.")
    question_log = dict(transcript[question_index])
    question_log["resolved"] = True
    transcript[question_index] = question_log
    record.transcript_json = transcript
    session.flush()
    return record


def finalize_interview_session(session: Session, session_id: int) -> InterviewSession:
    record = _get_interview_session(session, session_id)
    record.end_time = datetime.utcnow()
    session.flush()
    return record


def save_evaluation(session: Session, session_id: int, evaluation: Evaluation) -> EvaluationRecord:
    existing = session.scalar(select(EvaluationRecord).where(EvaluationRecord.session_id == session_id))
    data = evaluation.model_dump()
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        session.flush()
        return existing

    record = EvaluationRecord(session_id=session_id, **data)
    session.add(record)
    session.flush()
    return record


def _get_interview_session(session: Session, session_id: int) -> InterviewSession:
    record = session.get(InterviewSession, session_id)
    if not record:
        raise ValueError(f"Interview session {session_id} was not found.")
    return record

