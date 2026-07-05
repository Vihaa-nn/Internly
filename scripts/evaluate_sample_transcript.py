from internly.agents.evaluation_agent import evaluate_interview
from internly.schemas import CompanyIntel, ResumeProfile


def main() -> None:
    transcript = [
        {
            "question": "Two Sum",
            "turns": [
                {"role": "candidate", "text": "I would use a hash map from value to index."},
                {"role": "agent", "text": "What is the complexity?", "type": "followup"},
                {"role": "candidate", "text": "O(n) time and O(n) space."},
                {"role": "agent", "text": "Accepted.", "type": "accept"},
            ],
            "resolved": True,
        }
    ]
    resume_profile = ResumeProfile(
        skills=["Python", "Data Structures"],
        years_experience=1,
        projects=["Coding practice tracker"],
        education="B.Tech Computer Science",
        notable_gaps=[],
    )
    company_intel = CompanyIntel(
        interview_rounds=["Online assessment", "Technical interview"],
        common_questions=["Arrays", "Hash maps"],
        difficulty_notes="Medium DSA focus.",
        culture_notes="Values clear communication.",
    )
    evaluation = evaluate_interview(
        transcript=transcript,
        resume_profile=resume_profile,
        company_intel=company_intel,
    )
    print(evaluation.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

