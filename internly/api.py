from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from internly.db.database import get_session, init_db
from internly.db import crud
from internly.db.models import Candidate, InterviewSession
from internly.utils import format_display_label
from internly.pipeline import run_pipeline_start, resume_profile_from_candidate
from internly.schemas import CompanyIntel, PipelineStartResult
from internly.services.interview_service import (
    ask_next_question,
    handle_candidate_turn,
    prepare_session_rag_context,
    start_interview_session,
)
from internly.agents.evaluation_agent import evaluate_interview
from internly.services.leetcode_service import fetch_question
from internly.services.research_service import ensure_interview_playbook

app = FastAPI(title="Internly API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────────────────────────────────────

class StartInterviewRequest(BaseModel):
    candidate_id: int


class NextQuestionRequest(BaseModel):
    session_id: int
    company: str
    used_question_ids: list[int]


class InterviewTurnRequest(BaseModel):
    session_id: int
    question_index: int
    candidate_response: str
    candidate_id: int
    company: str
    role: str


class EvaluateRequest(BaseModel):
    session_id: int
    candidate_id: int


class LeetCodeRequest(BaseModel):
    link: str


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — Resume analysis + company research
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/analyse")
async def analyse(
    resume: UploadFile,
    company: str = Form(...),
    role: str = Form(...),
    job_description: str = Form(""),
) -> dict[str, Any]:
    suffix = Path(resume.filename or "resume.pdf").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await resume.read())
        tmp_path = tmp.name

    try:
        company = format_display_label(company)
        role = format_display_label(role)
        with get_session() as session:
            result: PipelineStartResult = run_pipeline_start(
                session,
                resume_file_path=tmp_path,
                target_role=role,
                target_company=company,
                allow_search=True,
                job_description=job_description or None,
            )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "candidate_id": result.candidate_id,
        "dsa_available": result.dsa_available,
        "dsa_message": result.dsa_message,
        "resume_profile": result.resume_profile.model_dump(),
        "company_intel": result.company_intel.model_dump() if result.company_intel else None,
        "job_description_provided": bool(job_description and job_description.strip()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Interview session
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/interview/start")
def start_interview(body: StartInterviewRequest) -> dict[str, Any]:
    with get_session() as session:
        candidate = session.get(Candidate, body.candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        interview = start_interview_session(session, body.candidate_id, include_greeting=True)
        session_id = interview.id
        transcript = interview.transcript_json

        profile = resume_profile_from_candidate(candidate)
        prepare_session_rag_context(
            session_id=session_id,
            company=candidate.target_company,
            role=candidate.target_role,
            resume_profile=profile,
        )

    intro_turns = transcript[0]["turns"] if transcript else []
    return {
        "session_id": session_id,
        "intro_turns": intro_turns,
    }


@app.post("/api/interview/next-question")
def next_question(body: NextQuestionRequest) -> dict[str, Any] | None:
    used_ids: set[int] = set(body.used_question_ids)
    with get_session() as session:
        interview = session.get(InterviewSession, body.session_id)
        if not interview:
            raise HTTPException(status_code=404, detail="Session not found")
        candidate = session.get(Candidate, interview.candidate_id)
        role = candidate.target_role if candidate else ""

        asked = ask_next_question(
            session,
            interview_session_id=body.session_id,
            company=body.company,
            role=role,
            used_question_ids=used_ids,
        )
        if asked is None:
            return None
        return {
            "question_index": asked.question_index,
            "question_title": asked.display_text,
            "question_link": asked.question_link,
            "difficulty": asked.question.difficulty or "",
            "used_question_ids": list(used_ids),
        }


@app.post("/api/interview/turn")
def interview_turn(body: InterviewTurnRequest) -> dict[str, Any]:
    with get_session() as session:
        candidate = session.get(Candidate, body.candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        company_intel_record = crud.get_company_intel(session, body.company, body.role)
        company_intel = (
            CompanyIntel(
                interview_rounds=company_intel_record.interview_rounds,
                common_questions=company_intel_record.common_questions,
                difficulty_notes=company_intel_record.difficulty_notes,
                culture_notes=company_intel_record.culture_notes,
            )
            if company_intel_record
            else CompanyIntel()
        )

        interview_playbook = ensure_interview_playbook(session, body.company, body.role)

        action, session_context = handle_candidate_turn(
            session,
            interview_session_id=body.session_id,
            question_index=body.question_index,
            candidate_response=body.candidate_response,
            resume_profile=resume_profile_from_candidate(candidate),
            company_intel=company_intel,
            company=body.company,
            role=body.role,
            interview_playbook=interview_playbook,
        )

    return {
        "type": action.type,
        "text": action.text,
        "session_context": session_context,
    }


@app.post("/api/interview/evaluate")
def evaluate(body: EvaluateRequest) -> dict[str, Any]:
    with get_session() as session:
        interview = session.get(InterviewSession, body.session_id)
        candidate = session.get(Candidate, body.candidate_id)
        if not interview or not candidate:
            raise HTTPException(status_code=404, detail="Session or candidate not found")

        company_intel_record = crud.get_company_intel(
            session, candidate.target_company, candidate.target_role
        )
        company_intel = (
            CompanyIntel(
                interview_rounds=company_intel_record.interview_rounds,
                common_questions=company_intel_record.common_questions,
                difficulty_notes=company_intel_record.difficulty_notes,
                culture_notes=company_intel_record.culture_notes,
            )
            if company_intel_record
            else None
        )

        clean_transcript = [
            q for q in (interview.transcript_json or [])
            if q.get("question") != "Introduction"
        ]

        # Enrich each question entry with difficulty + hint stats for the evaluator
        for q in clean_transcript:
            q_id = q.get("question_id")
            if q_id:
                try:
                    dsa_q = crud.get_dsa_question(session, int(q_id))
                    q["difficulty"] = dsa_q.difficulty or "Unknown"
                except Exception:
                    q["difficulty"] = "Unknown"
            turns = q.get("turns", [])
            q["hints_given"] = sum(
                1 for t in turns if t.get("role") == "agent" and t.get("type") in {"hint", "guide"}
            )
            q["was_guided"] = any(
                t.get("role") == "agent" and t.get("type") == "guide" for t in turns
            )
            q["was_skipped"] = any(
                t.get("role") == "agent" and t.get("type") == "accept"
                and "let's move on" in (t.get("text") or "").lower()
                for t in turns
            )

        evaluation = evaluate_interview(
            transcript=clean_transcript,
            resume_profile=resume_profile_from_candidate(candidate),
            company_intel=company_intel,
        )
        crud.save_evaluation(session, interview.id, evaluation)
        crud.finalize_interview_session(session, interview.id)

    return evaluation.model_dump()


@app.post("/api/leetcode/fetch")
def leetcode_fetch(body: LeetCodeRequest) -> dict[str, Any]:
    result = fetch_question(body.link)
    if result is None:
        return {"found": False}
    return {"found": True, **result}
