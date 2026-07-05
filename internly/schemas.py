from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ResumeProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    years_experience: float = 0.0
    projects: list[str] = Field(default_factory=list)
    education: str = ""
    notable_gaps: list[str] = Field(default_factory=list)


class CompanyIntel(BaseModel):
    interview_rounds: list[str] = Field(default_factory=list)
    common_questions: list[str] = Field(default_factory=list)
    difficulty_notes: str = ""
    culture_notes: str = ""


class InterviewAction(BaseModel):
    type: Literal["hint", "followup", "guide", "accept"]
    text: str
    reasoning: str = Field(
        default="",
        description="Internal interviewer reasoning: why this action was chosen. Not shown to candidate.",
    )


class OptimalSolution(BaseModel):
    optimal_approach: str
    optimal_time_complexity: str


class Evaluation(BaseModel):
    technical_score: int = Field(ge=1, le=10)
    communication_score: int = Field(ge=1, le=10)
    role_fit_score: int = Field(ge=1, le=10)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendation: str
    detailed_feedback: str


class PipelineStartResult(BaseModel):
    candidate_id: int
    dsa_available: bool
    dsa_message: str
    resume_profile: ResumeProfile
    company_intel: CompanyIntel | None = None

