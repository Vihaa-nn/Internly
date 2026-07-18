from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from sqlalchemy.orm import Session

from internly.agents.interview_agent import (
    assess_candidate_response,
    generate_intro_greeting,
    generate_optimal_solution,
)
from internly.db import crud
from internly.db.models import Candidate, DsaQuestion, InterviewSession
from internly.schemas import CompanyIntel, InterviewAction, ResumeProfile
from internly.services.research_service import ensure_interview_playbook
from internly.services.leetcode_service import is_paid_only_link
from internly.services.vector_store import (
    add_session_documents,
    index_session_baseline,
    retrieve_session_context_structured,
)
from internly.utils import candidate_wants_to_move_on


MAX_INTERVIEW_QUESTIONS = 3


@dataclass(frozen=True)
class AskedQuestion:
    question_index: int
    question: DsaQuestion
    display_text: str
    question_link: str | None = None


def start_interview_session(
    session: Session,
    candidate_id: int,
    include_greeting: bool = False,
) -> InterviewSession:
    greeting_text: str | None = None
    if include_greeting:
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} was not found.")
        profile = ResumeProfile(
            name=getattr(candidate, "name", "") or "",
            skills=candidate.skills,
            years_experience=candidate.years_experience,
            projects=candidate.projects,
            education=candidate.education,
            notable_gaps=candidate.notable_gaps,
            target_languages=getattr(candidate, "target_languages", []),
            achievements=getattr(candidate, "achievements", []),
            alignment_signals=getattr(candidate, "alignment_signals", []),
            skill_gaps=getattr(candidate, "skill_gaps", []),
        )
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
        interview_playbook = ensure_interview_playbook(
            session, candidate.target_company, candidate.target_role
        )
        greeting_text = generate_intro_greeting(
            profile,
            candidate.target_company,
            candidate.target_role,
            interview_playbook=interview_playbook,
            company_intel=company_intel,
        )
    return crud.create_interview_session(
        session,
        candidate_id,
        include_greeting=include_greeting,
        greeting_text=greeting_text,
    )


def prepare_session_rag_context(
    *,
    session_id: int,
    company: str,
    role: str,
    resume_profile: ResumeProfile,
) -> None:
    """Index resume/JD docs into Chroma session collection (background thread)."""
    documents: list[Document] = []

    resume_lines = [
        f"Skills: {', '.join(resume_profile.skills) or 'not specified'}",
        f"Years experience: {resume_profile.years_experience}",
        f"Projects: {'; '.join(resume_profile.projects) or 'none listed'}",
        f"Education: {resume_profile.education or 'not specified'}",
        f"Languages: {', '.join(resume_profile.target_languages) or 'not specified'}",
    ]
    documents.append(
        Document(page_content="\n".join(resume_lines), metadata={"doc_type": "resume"})
    )

    if resume_profile.alignment_signals or resume_profile.skill_gaps:
        jd_lines: list[str] = []
        if resume_profile.alignment_signals:
            jd_lines.append(f"JD alignment: {'; '.join(resume_profile.alignment_signals)}")
        if resume_profile.skill_gaps:
            jd_lines.append(f"Skill gaps: {'; '.join(resume_profile.skill_gaps)}")
        documents.append(
            Document(page_content="\n".join(jd_lines), metadata={"doc_type": "jd"})
        )

    if resume_profile.achievements:
        documents.append(
            Document(
                page_content=f"Achievements: {'; '.join(resume_profile.achievements)}",
                metadata={"doc_type": "resume"},
            )
        )

    threading.Thread(
        target=index_session_baseline,
        args=(session_id, company, role, documents),
        daemon=True,
    ).start()


def _index_question_doc(
    session_id: int,
    company: str,
    role: str,
    question: DsaQuestion,
    question_number: int,
) -> None:
    content = (
        f"Question: {question.title}. "
        f"Difficulty: {question.difficulty or 'Unknown'}. "
        f"Question {question_number} of {MAX_INTERVIEW_QUESTIONS}."
    )
    add_session_documents(
        session_id,
        company,
        role,
        [Document(page_content=content, metadata={"doc_type": "question"})],
    )


def ask_next_question(
    session: Session,
    *,
    interview_session_id: int,
    company: str,
    role: str,
    used_question_ids: set[int],
) -> AskedQuestion | None:
    import random
    import re

    # Enforce maximum number of questions per session
    if len(used_question_ids) >= MAX_INTERVIEW_QUESTIONS:
        return None

    # Get a larger pool of top questions (top 20) to select a diverse set from
    questions = crud.get_top_dsa_questions(session, company, limit=20)
    
    # Filter to only questions not yet asked in this session
    available_questions = [q for q in questions if q.id not in used_question_ids]
    if not available_questions:
        return None

    # Retrieve already asked questions to evaluate their difficulty and topics
    used_questions = []
    for q_id in used_question_ids:
        try:
            used_questions.append(crud.get_dsa_question(session, q_id))
        except Exception:
            pass

    # Extract keywords from already asked question titles to avoid same topics
    used_keywords = set()
    for uq in used_questions:
        # Normalize and split into keywords
        words = re.findall(r'[a-zA-Z0-9]{3,}', uq.title.lower())
        used_keywords.update(words)

    # Determine already covered difficulties
    used_difficulties = [uq.difficulty.lower() for uq in used_questions if uq.difficulty]

    # Difficulty rank for progression scoring
    _DIFF_RANK = {"easy": 1, "medium": 2, "hard": 3}

    # Score available questions based on diversity + deliberate difficulty progression
    candidates = []
    for q in available_questions:
        score = 0
        diff = (q.difficulty or "").lower()
        curr_rank = _DIFF_RANK.get(diff, 2)

        # 1. Deliberate difficulty progression
        if len(used_difficulties) == 0:
            # First question: always start Easy, allow Medium
            if diff == "easy":
                score += 5
            elif diff == "medium":
                score += 2
            else:
                score -= 3  # hard first is too punishing
        else:
            last_diff = used_difficulties[-1]
            last_rank = _DIFF_RANK.get(last_diff, 2)
            if curr_rank > last_rank:          # stepping up — ideal
                score += 4
            elif curr_rank == last_rank:       # same level — acceptable
                score += 2
            elif curr_rank == last_rank - 1:   # one step down — small penalty
                score -= 2
            else:                              # big drop — heavy penalty
                score -= 5

        # 2. Topic/Keyword diversity scoring
        q_words = re.findall(r'[a-zA-Z0-9]{3,}', q.title.lower())
        overlap = set(q_words).intersection(used_keywords)
        score -= len(overlap) * 3

        candidates.append((score, q))

    # Sort candidates by score descending and take the top scoring ones
    candidates.sort(key=lambda x: x[0], reverse=True)
    max_score = candidates[0][0]
    best_candidates = [q for score, q in candidates if score >= max_score - 1]

    # Prefer problems with a public LeetCode statement (skip Premium when possible)
    free_candidates = [q for q in best_candidates if not is_paid_only_link(q.link)]
    pool = free_candidates if free_candidates else best_candidates
    next_question = random.choice(pool)

    ensure_question_has_solution(session, next_question)
    display_text = next_question.title
    question_index = crud.append_question_to_session(
        session,
        interview_session_id,
        question=display_text,
        question_id=next_question.id,
    )
    used_question_ids.add(next_question.id)
    question_number = len(used_question_ids)
    threading.Thread(
        target=_index_question_doc,
        args=(interview_session_id, company, role, next_question, question_number),
        daemon=True,
    ).start()
    return AskedQuestion(
        question_index=question_index,
        question=next_question,
        display_text=display_text,
        question_link=next_question.link,
    )


def handle_candidate_turn(
    session: Session,
    *,
    interview_session_id: int,
    question_index: int,
    candidate_response: str,
    resume_profile: ResumeProfile,
    company_intel: CompanyIntel | None,
    company: str,
    role: str,
    interview_playbook: str = "",
) -> tuple[InterviewAction, str]:
    # ── 1. Persist candidate's message ───────────────────────────────────────
    interview_session = crud.append_interview_turn(
        session,
        interview_session_id,
        question_index,
        role="candidate",
        text=candidate_response,
    )
    question_log = interview_session.transcript_json[question_index]
    turns = question_log.get("turns", [])
    session_context = _retrieve_session_context_for_turn(
        interview_session_id, company, role, question_log, session
    )

    # ── 1b. Handle introduction turn without querying DSA database ───────────
    if question_log.get("question") == "Introduction":
        action = assess_candidate_response(
            question="Introduction",
            candidate_response=candidate_response,
            turns=turns,
            resume_profile=resume_profile,
            company_intel=company_intel,
            optimal_approach=None,
            optimal_time_complexity=None,
            trajectory_summary=_build_trajectory_summary(turns),
            company=company,
            role=role,
            interview_playbook=interview_playbook,
            session_context=session_context,
        )
        crud.append_interview_turn(
            session,
            interview_session_id,
            question_index,
            role="agent",
            text=action.text,
            turn_type=action.type,
        )
        if action.type in {"accept", "guide"}:
            crud.mark_question_resolved(session, interview_session_id, question_index)
        return action, session_context

    # Load the DSA question from database for all subsequent technical rounds
    question = _load_question_for_log(session, question_log)

    # ── 2. Hard bypass: candidate explicitly wants to skip ────────────────────
    # We still let the LLM handle all other cases, but an explicit "move on" /
    # "skip" / "give up" signal should always be respected immediately.
    if candidate_wants_to_move_on(candidate_response):
        approach = question.optimal_approach or "a standard algorithmic pattern"
        complexity = question.optimal_time_complexity or "problem-dependent"
        action = InterviewAction(
            type="accept",
            text=(
                f"Sure, let's move on.\n\n"
                f"**Optimal Approach**\n{approach}\n\n"
                f"**Time / Space Complexity**\n{complexity}\n\n"
                "Take a moment to review that pattern — it will come up again. Good luck with the next question!"
            ),
            reasoning="Candidate explicitly requested to skip/move on.",
        )
        _persist_and_resolve(session, interview_session_id, question_index, action)
        return action, session_context

    # ── 3. Count prior hints/guides so the LLM knows the trajectory ──────────
    hint_guide_count = _count_hint_guides(turns)

    # ── 4. Build trajectory summary to help LLM build on prior turns ─────────
    trajectory_summary = _build_trajectory_summary(turns)

    candidate = session.get(Candidate, interview_session.candidate_id)
    if not candidate:
        raise ValueError("Candidate for interview session was not found.")

    # ── 5. Let the LLM decide everything ─────────────────────────────────────
    action = assess_candidate_response(
        question=question.title,
        candidate_response=candidate_response,
        turns=turns,
        resume_profile=resume_profile,
        company_intel=company_intel,
        optimal_approach=question.optimal_approach,
        optimal_time_complexity=question.optimal_time_complexity,
        trajectory_summary=trajectory_summary,
        company=company,
        role=role,
        interview_playbook=interview_playbook,
        session_context=session_context,
    )

    # ── 6. Safety net: if LLM tries to hint a 4th+ time, force guide ─────────
    # Allow up to 3 hints before forcing a guide to prevent infinite hint loops.
    if action.type == "hint" and hint_guide_count >= 3:
        approach = question.optimal_approach or "a standard algorithmic pattern — check the LeetCode editorial for details"
        complexity = question.optimal_time_complexity or "problem-dependent"
        action = InterviewAction(
            type="guide",
            text=(
                f"You've had a few nudges — let me walk you through the full solution now.\n\n"
                f"**Optimal Approach**\n{approach}\n\n"
                f"**Time / Space Complexity**\n{complexity}\n\n"
                "The key insight to internalise is the core pattern above. "
                "Recognising it quickly in future problems is what separates a good attempt from a great one. Let's move on."
            ),
            reasoning=f"LLM chose hint but hint_guide_count={hint_guide_count} >= 3. Forced to guide.",
        )

    # ── 7. Persist agent turn and resolve if needed ───────────────────────────
    crud.append_interview_turn(
        session,
        interview_session_id,
        question_index,
        role="agent",
        text=action.text,
        turn_type=action.type,
    )
    if action.type in {"accept", "guide"}:
        crud.mark_question_resolved(session, interview_session_id, question_index)

    return action, session_context


def _retrieve_session_context_for_turn(
    session_id: int,
    company: str,
    role: str,
    question_log: dict[str, Any],
    db_session: Session,
) -> str:
    is_intro = question_log.get("question") == "Introduction"
    if is_intro:
        query = f"{company} {role} introduction background projects"
    else:
        title = question_log.get("question", "")
        difficulty = ""
        question_id = question_log.get("question_id")
        if question_id:
            try:
                dsa_q = crud.get_dsa_question(db_session, int(question_id))
                difficulty = dsa_q.difficulty or ""
            except Exception:
                pass
        query = f"{title} {difficulty} DSA follow-up"
    return retrieve_session_context_structured(session_id, query, is_intro=is_intro)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def ensure_question_has_solution(session: Session, question: DsaQuestion) -> DsaQuestion:
    if question.optimal_approach and question.optimal_time_complexity:
        return question
    solution = generate_optimal_solution(question.title, question.difficulty)
    return crud.update_dsa_solution(
        session,
        question.id,
        optimal_approach=solution.optimal_approach,
        optimal_time_complexity=solution.optimal_time_complexity,
    )


def _count_hint_guides(turns: list[dict[str, Any]]) -> int:
    """Count how many hint OR guide turns the agent has already given."""
    return sum(
        1
        for t in turns
        if t.get("role") == "agent" and t.get("type") in {"hint", "guide"}
    )


def _persist_and_resolve(
    session: Session,
    interview_session_id: int,
    question_index: int,
    action: InterviewAction,
) -> None:
    crud.append_interview_turn(
        session,
        interview_session_id,
        question_index,
        role="agent",
        text=action.text,
        turn_type=action.type,
    )
    crud.mark_question_resolved(session, interview_session_id, question_index)


def _load_question_for_log(session: Session, question_log: dict[str, Any]) -> DsaQuestion:
    question_id = question_log.get("question_id")
    if not question_id:
        raise ValueError("Question log does not include a question_id.")
    return crud.get_dsa_question(session, int(question_id))


def _build_trajectory_summary(turns: list[dict[str, Any]]) -> str:
    """
    Summarise what the candidate has attempted so far for the current question
    so the interviewer agent can build on prior turns rather than repeat itself.
    """
    candidate_turns = [t for t in turns if t.get("role") == "candidate"]
    agent_turns = [t for t in turns if t.get("role") == "agent"]
    hints_given = sum(1 for t in agent_turns if t.get("type") in {"hint", "guide"})

    if not candidate_turns:
        return "First response — no prior attempts for this question."

    lines = [
        f"Attempts: {len(candidate_turns)}  |  Hints/guides given: {hints_given}",
        "— Candidate attempts in order —",
    ]
    for i, t in enumerate(candidate_turns, 1):
        snippet = t["text"][:150].replace("\n", " ")
        ellipsis = "…" if len(t["text"]) > 150 else ""
        lines.append(f"  {i}. \"{snippet}{ellipsis}\"")

    if hints_given > 0:
        last_hint = next(
            (t["text"][:100] for t in reversed(agent_turns) if t.get("type") in {"hint", "guide"}),
            "",
        )
        lines.append(f"Last hint/guide given: \"{last_hint}…\"")

    return "\n".join(lines)
