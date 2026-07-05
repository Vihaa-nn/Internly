from __future__ import annotations

from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from internly.llm import get_chat_model
from internly.schemas import ResumeProfile


def load_resume_text(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader

        documents = PyPDFLoader(str(path)).load()
    elif suffix == ".docx":
        from langchain_community.document_loaders import Docx2txtLoader

        documents = Docx2txtLoader(str(path)).load()
    else:
        raise ValueError("Resume must be a PDF or DOCX file.")

    return "\n\n".join(doc.page_content for doc in documents).strip()


def evaluate_resume_text(resume_text: str, job_description: str | None = None) -> ResumeProfile:
    system_instruction = (
        "You extract structured resume facts. Be faithful to the resume text. "
        "If a field is unclear, use an empty list, empty string, or 0. "
        "Always extract target programming languages (e.g., Python, C++, Java, JavaScript, Go, Rust, etc.) "
        "the candidate is proficient in, based on their projects, skills, or experience, into 'target_languages'."
    )
    
    if job_description:
        system_instruction += (
            "\nAdditionally, compare the candidate's resume text against the provided Target Job Description. "
            "Identify alignment signals (strengths, matches, relevant skills/experience) "
            "and identify skill gaps (missing skills, requirements, or areas where the candidate falls short) "
            "relative to the job description. Populate 'alignment_signals' and 'skill_gaps' arrays."
        )

    human_content = f"Resume text:\n\n{resume_text}"
    if job_description:
        human_content += f"\n\nTarget Job Description:\n\n{job_description}"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_instruction),
            ("human", human_content),
        ]
    )
    llm = get_chat_model(temperature=0)
    chain = prompt | llm.with_structured_output(ResumeProfile)
    return chain.invoke({})


def evaluate_resume_file(file_path: str | Path, job_description: str | None = None) -> tuple[str, ResumeProfile]:
    resume_text = load_resume_text(file_path)
    return resume_text, evaluate_resume_text(resume_text, job_description)

