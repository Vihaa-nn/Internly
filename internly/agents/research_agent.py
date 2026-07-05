from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from internly.config import settings
from internly.llm import get_chat_model
from internly.schemas import CompanyIntel


def search_company_interview_intel(company: str, role: str, max_results: int = 5) -> str:
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is not set. Add it to your .env file.")

    try:
        from langchain_tavily import TavilySearch

        tool = TavilySearch(max_results=max_results, topic="general")
        results = tool.invoke({"query": _build_query(company, role)})
    except ImportError:
        from langchain_community.tools.tavily_search import TavilySearchResults

        tool = TavilySearchResults(max_results=max_results)
        results = tool.invoke(_build_query(company, role))

    return _format_search_results(results)


def synthesize_company_intel(company: str, role: str, raw_research_text: str) -> CompanyIntel:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You synthesize India-specific interview process and culture notes. "
                "This information is context only; do not turn it into multiple mock interview rounds. "
                "Return concise, practical, source-grounded points.",
            ),
            (
                "human",
                "Company: {company}\nRole: {role}\n\nRaw research:\n{raw_research_text}",
            ),
        ]
    )
    llm = get_chat_model(temperature=0.1)
    chain = prompt | llm.with_structured_output(CompanyIntel)
    return chain.invoke(
        {"company": company, "role": role, "raw_research_text": raw_research_text}
    )


def _build_query(company: str, role: str) -> str:
    return (
        f'{company} {role} interview process India AmbitionBox Glassdoor Naukri '
        "Reddit developersIndia common questions culture difficulty"
    )


def _format_search_results(results: object) -> str:
    if isinstance(results, dict) and "results" in results:
        results = results["results"]
    if not isinstance(results, list):
        return str(results)

    chunks: list[str] = []
    for item in results:
        if not isinstance(item, dict):
            chunks.append(str(item))
            continue
        title = item.get("title", "")
        url = item.get("url", "")
        content = item.get("content", item.get("snippet", ""))
        chunks.append(f"TITLE: {title}\nURL: {url}\nCONTENT:\n{content}")
    return "\n\n---\n\n".join(chunks)

