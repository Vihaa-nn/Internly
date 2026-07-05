from __future__ import annotations

import concurrent.futures
import threading
from pathlib import Path

from internly.agents.research_agent import search_company_interview_intel, synthesize_company_intel
from internly.agents.resume_evaluator import evaluate_resume_file, evaluate_resume_text
from internly.config import settings
from internly.db import crud
from internly.schemas import CompanyIntel, PipelineStartResult, ResumeProfile
from internly.services.vector_store import index_company_intel_text


def run_pipeline_start(
    session,
    *,
    resume_file_path: str | Path | None = None,
    resume_text: str | None = None,
    target_role: str,
    target_company: str,
    allow_search: bool = True,
    job_description: str | None = None,
) -> PipelineStartResult:
    # ── 1. Fetch DSA status and check if company intel is cached in DB ─────────
    # These DB lookups are extremely fast (< 5ms)
    dsa_questions = crud.get_top_dsa_questions(session, target_company, limit=settings.top_dsa_questions)
    dsa_available = bool(dsa_questions)
    dsa_message = (
        f"Found {len(dsa_questions)} DSA questions for {target_company}."
        if dsa_available
        else f"No DSA data is available for {target_company}. The DSA mock interview cannot start."
    )

    company_intel_record = crud.get_company_intel(session, target_company, target_role)
    need_search = (company_intel_record is None) and allow_search

    # Define tasks for concurrent execution
    def parse_resume():
        if resume_file_path:
            return evaluate_resume_file(resume_file_path, job_description)
        elif resume_text:
            return resume_text, evaluate_resume_text(resume_text, job_description)
        else:
            raise ValueError("Provide either resume_file_path or resume_text.")

    def fetch_and_synthesize_intel():
        raw_text = search_company_interview_intel(target_company, target_role)
        intel = synthesize_company_intel(target_company, target_role, raw_text)
        return raw_text, intel

    # ── 2. Run independent API & LLM operations in parallel ──────────────────
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        resume_future = executor.submit(parse_resume)
        research_future = executor.submit(fetch_and_synthesize_intel) if need_search else None

        # Gather results (blocks until thread tasks complete)
        raw_resume_text, resume_profile = resume_future.result()
        if research_future:
            raw_research_text, company_intel = research_future.result()
        else:
            raw_research_text = None
            company_intel = None

    # ── 3. DB Writes (must be run on the main thread using 'session') ──────────
    candidate = crud.create_candidate(
        session,
        resume_text=raw_resume_text,
        profile=resume_profile,
        target_role=target_role,
        target_company=target_company,
        job_description=job_description,
    )

    if need_search and company_intel:
        crud.save_company_intel(
            session,
            company=target_company,
            role=target_role,
            intel=company_intel,
            raw_research_text=raw_research_text,
        )
        # Background index to Chroma so it doesn't block UI load
        if raw_research_text:
            threading.Thread(
                target=index_company_intel_text,
                args=(target_company, target_role, raw_research_text),
                daemon=True,
            ).start()
    elif company_intel_record:
        company_intel = CompanyIntel(
            interview_rounds=company_intel_record.interview_rounds,
            common_questions=company_intel_record.common_questions,
            difficulty_notes=company_intel_record.difficulty_notes,
            culture_notes=company_intel_record.culture_notes,
        )

    return PipelineStartResult(
        candidate_id=candidate.id,
        dsa_available=dsa_available,
        dsa_message=dsa_message,
        resume_profile=resume_profile,
        company_intel=company_intel,
    )


def resume_profile_from_candidate(candidate) -> ResumeProfile:
    return ResumeProfile(
        skills=candidate.skills,
        years_experience=candidate.years_experience,
        projects=candidate.projects,
        education=candidate.education,
        notable_gaps=candidate.notable_gaps,
        target_languages=getattr(candidate, "target_languages", []),
        alignment_signals=getattr(candidate, "alignment_signals", []),
        skill_gaps=getattr(candidate, "skill_gaps", []),
    )
