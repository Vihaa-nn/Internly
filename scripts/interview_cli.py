from __future__ import annotations

from internly.config import settings
from internly.db.database import get_session, init_db
from internly.db.models import Candidate
from internly.pipeline import resume_profile_from_candidate
from internly.schemas import CompanyIntel
from internly.services.interview_service import (
    ask_next_question,
    handle_candidate_turn,
    start_interview_session,
)
from internly.services.research_service import prepare_research_context


def main() -> None:
    init_db()
    candidate_id = int(input("Candidate id: ").strip())

    with get_session() as session:
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {candidate_id} was not found.")

        research = prepare_research_context(
            session,
            company=candidate.target_company,
            role=candidate.target_role,
            allow_search=False,
        )
        if not research.dsa_available:
            print(research.dsa_message)
            return

        interview = start_interview_session(session, candidate.id)
        used_question_ids: set[int] = set()
        resume_profile = resume_profile_from_candidate(candidate)
        company_intel = research.company_intel or CompanyIntel()

        print(f"Starting DSA-only interview session {interview.id}.")
        for _ in range(settings.num_interview_questions):
            asked = ask_next_question(
                session,
                interview_session_id=interview.id,
                company=candidate.target_company,
                role=candidate.target_role,
                used_question_ids=used_question_ids,
            )
            if not asked:
                print("No more DSA questions are available.")
                break

            print(f"\nQuestion: {asked.display_text}")
            while True:
                response = input("\nYour approach/pseudocode: ").strip()
                action, _session_context = handle_candidate_turn(
                    session,
                    interview_session_id=interview.id,
                    question_index=asked.question_index,
                    candidate_response=response,
                    resume_profile=resume_profile,
                    company_intel=company_intel,
                    company=candidate.target_company,
                    role=candidate.target_role,
                )
                print(f"\nInterviewer: {action.text}")
                if action.type == "accept":
                    break

        print("\nInterview complete. Run the evaluation agent to generate feedback.")


if __name__ == "__main__":
    main()

