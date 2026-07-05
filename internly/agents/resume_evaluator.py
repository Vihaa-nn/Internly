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


def evaluate_resume_text(resume_text: str) -> ResumeProfile:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You extract structured resume facts. Be faithful to the resume text. "
                "If a field is unclear, use an empty list, empty string, or 0.",
            ),
            ("human", "Resume text:\n\n{resume_text}"),
        ]
    )
    llm = get_chat_model(temperature=0)
    chain = prompt | llm.with_structured_output(ResumeProfile)
    return chain.invoke({"resume_text": resume_text})


def evaluate_resume_file(file_path: str | Path) -> tuple[str, ResumeProfile]:
    resume_text = load_resume_text(file_path)
    return resume_text, evaluate_resume_text(resume_text)

