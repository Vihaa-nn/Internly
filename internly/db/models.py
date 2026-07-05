from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from internly.db.database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resume_text: Mapped[str] = mapped_column(Text)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    years_experience: Mapped[float] = mapped_column(Float, default=0.0)
    projects: Mapped[list[str]] = mapped_column(JSON, default=list)
    education: Mapped[str] = mapped_column(Text, default="")
    notable_gaps: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_role: Mapped[str] = mapped_column(String(255), index=True)
    target_company: Mapped[str] = mapped_column(String(255), index=True)
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    alignment_signals: Mapped[list[str]] = mapped_column(JSON, default=list)
    skill_gaps: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions: Mapped[list["InterviewSession"]] = relationship(back_populates="candidate")


class CompanyIntelRecord(Base):
    __tablename__ = "company_intel"
    __table_args__ = (
        UniqueConstraint("company_normalized", "role_normalized", name="uq_company_intel_company_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(255), index=True)
    company_normalized: Mapped[str] = mapped_column(String(255), index=True)
    role_normalized: Mapped[str] = mapped_column(String(255), index=True)
    interview_rounds: Mapped[list[str]] = mapped_column(JSON, default=list)
    common_questions: Mapped[list[str]] = mapped_column(JSON, default=list)
    difficulty_notes: Mapped[str] = mapped_column(Text, default="")
    culture_notes: Mapped[str] = mapped_column(Text, default="")
    raw_research_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=func.now())


class DsaQuestion(Base):
    __tablename__ = "dsa_questions"
    __table_args__ = (
        UniqueConstraint("company_normalized", "title", "link", name="uq_dsa_company_title_link"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(255), index=True)
    company_normalized: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    difficulty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    frequency: Mapped[float | None] = mapped_column(Float, nullable=True)
    acceptance: Mapped[str | None] = mapped_column(String(50), nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    optimal_approach: Mapped[str | None] = mapped_column(Text, nullable=True)
    optimal_time_complexity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=func.now())


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    transcript_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    candidate: Mapped[Candidate] = relationship(back_populates="sessions")
    evaluation: Mapped["EvaluationRecord"] = relationship(back_populates="session", uselist=False)


class EvaluationRecord(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id"), index=True, unique=True)
    technical_score: Mapped[int] = mapped_column(Integer)
    communication_score: Mapped[int] = mapped_column(Integer)
    role_fit_score: Mapped[int] = mapped_column(Integer)
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSON, default=list)
    recommendation: Mapped[str] = mapped_column(Text)
    detailed_feedback: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped[InterviewSession] = relationship(back_populates="evaluation")

