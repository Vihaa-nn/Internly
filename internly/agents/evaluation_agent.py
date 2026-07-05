from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from internly.llm import get_chat_model
from internly.schemas import CompanyIntel, Evaluation, ResumeProfile


def evaluate_interview(
    *,
    transcript: list[dict[str, Any]],
    resume_profile: ResumeProfile,
    company_intel: CompanyIntel | None,
) -> Evaluation:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You evaluate a DSA-only mock interview transcript. Score the candidate's "
                "algorithmic reasoning, communication, and role fit. Do not assume hidden "
                "interview-agent reasoning; use only the visible transcript and context.",
            ),
            (
                "human",
                "Resume profile:\n{resume_profile}\n\nCompany intel:\n{company_intel}\n\n"
                "Transcript JSON:\n{transcript_json}",
            ),
        ]
    )
    llm = get_chat_model(temperature=0)
    chain = prompt | llm.with_structured_output(Evaluation)
    return chain.invoke(
        {
            "resume_profile": resume_profile.model_dump_json(indent=2),
            "company_intel": company_intel.model_dump_json(indent=2) if company_intel else "{}",
            "transcript_json": json.dumps(transcript, indent=2),
        }
    )

