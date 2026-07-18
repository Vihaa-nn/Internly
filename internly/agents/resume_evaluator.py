from __future__ import annotations

from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from internly.llm import get_chat_model
from internly.schemas import ResumeProfile


def _guess_name_from_resume(resume_text: str) -> str:
    """Heuristic fallback when the LLM leaves name empty."""
    noise = {"resume", "curriculum", "vitae", "cv", "profile", "summary", "experience"}
    for line in resume_text.strip().splitlines()[:6]:
        candidate = line.strip()
        if not candidate or "@" in candidate or any(ch.isdigit() for ch in candidate):
            continue
        if len(candidate) > 60:
            continue
        words = candidate.replace(".", " ").split()
        if not (1 <= len(words) <= 4):
            continue
        if any(word.lower() in noise for word in words):
            continue
        if not all(word.isalpha() for word in words):
            continue
        return candidate
    return ""


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
        "If a field is unclear, use an empty list, empty string, or 0.\n"
        "For 'name': extract the candidate's full name from the resume header or contact section. "
        "Use the name as written on the resume (do not invent one).\n"
        "For 'achievements': list competitions, hackathons, awards, rankings, honors, and "
        "leadership roles (e.g. society head, club lead). Each item is a short phrase. "
        "Do NOT put achievements in alignment_signals.\n"
        "Always extract target programming languages (e.g., Python, C++, Java, JavaScript, Go, Rust, etc.) "
        "the candidate is proficient in, based on their projects, skills, or experience, into 'target_languages'."
    )
    
    if job_description:
        system_instruction += (
            "\nAdditionally, compare the candidate's resume text against the provided Target Job Description.\n"
            "For 'alignment_signals': list only specific technical skills, tools, frameworks, domains, or "
            "directly relevant experiences from the resume that explicitly match a requirement stated in the JD. "
            "Each item must name the matching skill/technology/experience AND the JD requirement it satisfies. "
            "Example: 'Python proficiency matches JD requirement for backend scripting.' "
            "Do NOT list achievements, awards, competitions, or leadership roles here — those belong in achievements.\n"
            "For 'skill_gaps': list specific skills, tools, or requirements mentioned in the JD that are "
            "absent or weak in the resume. Each item must name the missing skill and quote or paraphrase "
            "the JD requirement it addresses. "
            "Example: 'No Kubernetes experience — JD requires container orchestration skills.'"
        )
    else:
        system_instruction += (
            "\nNo job description was provided. Leave alignment_signals and skill_gaps as empty lists."
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
    profile: ResumeProfile = chain.invoke({})
    if not job_description:
        profile = profile.model_copy(update={"alignment_signals": [], "skill_gaps": []})
    if not profile.name.strip():
        guessed = _guess_name_from_resume(resume_text)
        if guessed:
            profile = profile.model_copy(update={"name": guessed})
    return profile


def evaluate_resume_file(file_path: str | Path, job_description: str | None = None) -> tuple[str, ResumeProfile]:
    resume_text = load_resume_text(file_path)
    return resume_text, evaluate_resume_text(resume_text, job_description)

