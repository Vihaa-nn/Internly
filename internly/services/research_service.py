from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from internly.agents.research_agent import (
    generate_interview_playbook,
    search_company_interview_intel,
    synthesize_company_intel,
)
from internly.config import settings
from internly.db import crud
from internly.db.models import DsaQuestion
from internly.schemas import CompanyIntel


@dataclass(frozen=True)
class ResearchContext:
    dsa_available: bool
    dsa_message: str
    dsa_questions: list[DsaQuestion]
    company_intel: CompanyIntel | None


def ensure_interview_playbook(session: Session, company: str, role: str) -> str:
    """Return cached playbook text, backfilling via search if the record exists but playbook is empty."""
    record = crud.get_company_intel(session, company, role)
    if not record:
        return ""
    playbook = (record.interview_playbook_text or "").strip()
    if playbook:
        return playbook
    raw_text = search_company_interview_intel(company, role)
    playbook = generate_interview_playbook(company, role, raw_text)
    intel = CompanyIntel(
        interview_rounds=record.interview_rounds,
        common_questions=record.common_questions,
        difficulty_notes=record.difficulty_notes,
        culture_notes=record.culture_notes,
    )
    crud.save_company_intel(
        session,
        company=company,
        role=role,
        intel=intel,
        interview_playbook_text=playbook,
    )
    return playbook


def prepare_research_context(
    session: Session,
    *,
    company: str,
    role: str,
    allow_search: bool = True,
) -> ResearchContext:
    dsa_questions = crud.get_top_dsa_questions(session, company, limit=settings.top_dsa_questions)
    dsa_available = bool(dsa_questions)
    dsa_message = (
        f"Found {len(dsa_questions)} DSA questions for {company}."
        if dsa_available
        else f"No DSA data is available for {company}. The DSA mock interview cannot start."
    )

    company_intel_record = crud.get_company_intel(session, company, role)
    if company_intel_record:
        ensure_interview_playbook(session, company, role)
        company_intel = CompanyIntel(
            interview_rounds=company_intel_record.interview_rounds,
            common_questions=company_intel_record.common_questions,
            difficulty_notes=company_intel_record.difficulty_notes,
            culture_notes=company_intel_record.culture_notes,
        )
    elif allow_search:
        raw_text = search_company_interview_intel(company, role)
        company_intel = synthesize_company_intel(company, role, raw_text)
        playbook = generate_interview_playbook(company, role, raw_text)
        crud.save_company_intel(
            session,
            company=company,
            role=role,
            intel=company_intel,
            interview_playbook_text=playbook,
        )
    else:
        company_intel = None

    return ResearchContext(
        dsa_available=dsa_available,
        dsa_message=dsa_message,
        dsa_questions=dsa_questions,
        company_intel=company_intel,
    )
