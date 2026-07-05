from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from internly.agents.interview_agent import assess_candidate_response, generate_optimal_solution
from internly.config import settings
from internly.db import crud
from internly.db.models import Candidate, DsaQuestion, InterviewSession
from internly.schemas import CompanyIntel, InterviewAction, ResumeProfile
from internly.services.vector_store import retrieve_company_context
from internly.utils import candidate_wants_to_move_on, is_underexplained_strategy_answer


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
    return crud.create_interview_session(session, candidate_id, include_greeting=include_greeting)


def ask_next_question(
    session: Session,
    *,
    interview_session_id: int,
    company: str,
    used_question_ids: set[int],
) -> AskedQuestion | None:
    import random
    import re

    # Enforce maximum number of questions per session (limit to settings.num_interview_questions)
    if len(used_question_ids) >= settings.num_interview_questions:
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

    # Score available questions based on diversity
    candidates = []
    for q in available_questions:
        score = 0
        diff = (q.difficulty or "").lower()

        # 1. Difficulty diversity scoring
        if len(used_difficulties) == 0:
            # First question: prefer Easy or Medium to start smoothly
            if diff in ("easy", "medium"):
                score += 3
        else:
            # Subsequent questions: prefer different difficulties from what was already asked
            if diff not in used_difficulties:
                score += 3
            if "easy" in used_difficulties and diff == "easy":
                score -= 2  # penalize repeating easy questions

        # 2. Topic/Keyword diversity scoring
        q_words = re.findall(r'[a-zA-Z0-9]{3,}', q.title.lower())
        overlap = set(q_words).intersection(used_keywords)
        # penalize keyword/topic similarity (e.g. asking 3Sum after Two Sum)
        score -= len(overlap) * 3

        candidates.append((score, q))

    # Sort candidates by score descending and take the top scoring ones
    candidates.sort(key=lambda x: x[0], reverse=True)
    max_score = candidates[0][0]
    best_candidates = [q for score, q in candidates if score >= max_score - 1]

    # Select randomly from the best candidates
    next_question = random.choice(best_candidates)

    ensure_question_has_solution(session, next_question)
    display_text = next_question.title
    question_index = crud.append_question_to_session(
        session,
        interview_session_id,
        question=display_text,
        question_id=next_question.id,
    )
    used_question_ids.add(next_question.id)
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
) -> InterviewAction:
    # ── 1. Persist candidate's message ───────────────────────────────────────
    interview_session = crud.append_interview_turn(
        session,
        interview_session_id,
        question_index,
        role="candidate",
        text=candidate_response,
    )
    question_log = interview_session.transcript_json[question_index]
    question = _load_question_for_log(session, question_log)
    turns = question_log.get("turns", [])

    # ── 2. Hard bypass: candidate explicitly wants to skip ────────────────────
    # We still let the LLM handle all other cases, but an explicit "move on" /
    # "skip" / "give up" signal should always be respected immediately.
    if candidate_wants_to_move_on(candidate_response):
        action = InterviewAction(
            type="accept",
            text=(
                "Sure — let's move on. For reference, the optimal approach for this question is: "
                f"{question.optimal_approach or 'a standard algorithmic pattern'}. "
                f"Time complexity: {question.optimal_time_complexity or 'problem-dependent'}. "
                "Good luck with the next one!"
            ),
            reasoning="Candidate explicitly requested to skip/move on.",
        )
        _persist_and_resolve(session, interview_session_id, question_index, action)
        return action

    # ── 3. Check for underexplained strategy answer (fast bypass) ────────────
    if is_underexplained_strategy_answer(candidate_response):
        action = InterviewAction(
            type="followup",
            text=(
                "That sounds like a reasonable direction, but I need the actual algorithm. "
                "Walk me through the pseudocode: what do you store, what do you check on each "
                "iteration, when do you return, and what are the time and space complexities?"
            ),
            reasoning="Underexplained strategy answer detected.",
        )
        crud.append_interview_turn(
            session,
            interview_session_id,
            question_index,
            role="agent",
            text=action.text,
            turn_type=action.type,
        )
        return action

    # ── 4. Count prior hints/guides so the LLM knows the trajectory ──────────
    hint_guide_count = _count_hint_guides(turns)

    # ── 4. Retrieve relevant company context ─────────────────────────────────
    retrieved_context = retrieve_company_context(
        company=company,
        role=role,
        query=question.title,
        k=3,
    )

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
        retrieved_context=retrieved_context,
    )

    # ── 6. Safety net: if LLM tries to hint a 3rd+ time, force guide ─────────
    # This prevents an infinite hint loop but keeps the LLM's text direction.
    if action.type == "hint" and hint_guide_count >= 2:
        action = InterviewAction(
            type="guide",
            text=(
                f"You've received a couple of nudges, so let me walk you through it. "
                f"The optimal approach for '{question.title}' is: "
                f"{question.optimal_approach or 'a standard pattern — see the LeetCode editorial'}. "
                f"Time/space complexity: {question.optimal_time_complexity or 'depends on the approach'}. "
                "The key insight to remember for next time is the core pattern above. "
                "Let's move to the next question."
            ),
            reasoning=f"LLM chose hint but hint_guide_count={hint_guide_count} >= 2. Forced to guide.",
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

    return action


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
