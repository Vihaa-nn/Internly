from internly.db import crud
from internly.db.database import get_session, init_db
from internly.schemas import CompanyIntel, Evaluation, ResumeProfile


def main() -> None:
    init_db()
    with get_session() as session:
        profile = ResumeProfile(
            skills=["Python", "DSA"],
            years_experience=1.5,
            projects=["Resume reviewer"],
            education="B.Tech Computer Science",
            notable_gaps=[],
        )
        candidate = crud.create_candidate(
            session,
            resume_text="Python developer with DSA projects.",
            profile=profile,
            target_role="Software Engineer",
            target_company="ExampleCorp",
        )
        crud.save_company_intel(
            session,
            company="ExampleCorp",
            role="Software Engineer",
            intel=CompanyIntel(
                interview_rounds=["Online assessment", "DSA interview"],
                common_questions=["Arrays", "Graphs"],
                difficulty_notes="Medium DSA focus.",
                culture_notes="Collaborative engineering culture.",
            ),
            raw_research_text="Dummy research text.",
        )
        question = crud.upsert_dsa_question(
            session,
            company="ExampleCorp",
            title="Two Sum",
            difficulty="Easy",
            frequency=95.0,
            acceptance="50%",
            link="https://leetcode.com/problems/two-sum/",
        )
        interview = crud.create_interview_session(session, candidate.id)
        question_index = crud.append_question_to_session(
            session,
            interview.id,
            question=question.title,
            question_id=question.id,
        )
        crud.append_interview_turn(
            session,
            interview.id,
            question_index,
            role="candidate",
            text="I would use a hash map.",
        )
        crud.mark_question_resolved(session, interview.id, question_index)
        crud.save_evaluation(
            session,
            interview.id,
            Evaluation(
                technical_score=8,
                communication_score=7,
                role_fit_score=8,
                strengths=["Identified hash map approach"],
                weaknesses=["Could mention edge cases earlier"],
                recommendation="Good DSA foundation.",
                detailed_feedback="The candidate explained a near-optimal approach clearly.",
            ),
        )
        print(f"Created candidate {candidate.id}, question {question.id}, session {interview.id}.")


if __name__ == "__main__":
    main()

