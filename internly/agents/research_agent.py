from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from internly.config import settings
from internly.llm import get_chat_model
from internly.schemas import CompanyIntel


def search_company_interview_intel(company: str, role: str, max_results: int = 5) -> str:
    if not settings.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY is not set. Add it to your .env file.")

    queries = [
        f"{company} {role} interview process India AmbitionBox Glassdoor Naukri",
        f"{company} {role} technical coding round questions Reddit developersIndia",
        f"{company} {role} DSA interview experience",
    ]

    try:
        from langchain_tavily import TavilySearch
        tool = TavilySearch(max_results=max_results, topic="general")
        invoke_fn = lambda q: tool.invoke({"query": q})
    except ImportError:
        from langchain_community.tools.tavily_search import TavilySearchResults
        tool = TavilySearchResults(max_results=max_results)
        invoke_fn = lambda q: tool.invoke(q)

    import concurrent.futures
    all_results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(queries)) as executor:
        futures = {executor.submit(invoke_fn, q): q for q in queries}
        for future in concurrent.futures.as_completed(futures):
            try:
                res = future.result()
                if isinstance(res, dict) and "results" in res:
                    res = res["results"]
                if isinstance(res, list):
                    all_results.extend(res)
            except Exception as e:
                import sys
                print(f"Warning: Tavily search query failed: {e}", file=sys.stderr)

    # URL Deduplication
    seen_urls = set()
    deduped_results = []
    for item in all_results:
        if isinstance(item, dict):
            url = item.get("url")
            if url:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
            deduped_results.append(item)
        else:
            deduped_results.append(item)

    return _format_search_results(deduped_results)


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


def generate_interview_playbook(company: str, role: str, raw_research_text: str) -> str:
    """Curated DSA/coding-round playbook from in-memory Tavily research (not stored raw)."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You write a concise interview playbook for a DSA/coding technical round only. "
                "Output structured prose (~500–800 words) covering: how interviewers probe, "
                "follow-up patterns, complexity expectations, communication bar, and typical "
                "problem difficulty. Ground points in the research provided. "
                "Exclude HR, salary, offer negotiation, and unrelated culture fluff.",
            ),
            (
                "human",
                "Company: {company}\nRole: {role}\n\nRaw research:\n{raw_research_text}",
            ),
        ]
    )
    llm = get_chat_model(temperature=0.1)
    chain = prompt | llm
    response = chain.invoke(
        {"company": company, "role": role, "raw_research_text": raw_research_text}
    )
    return _llm_content_to_str(response)


def _llm_content_to_str(response: object) -> str:
    """Normalize LangChain/Gemini message content (str or list of blocks) to plain text."""
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if text:
                    parts.append(str(text))
            elif hasattr(block, "text"):
                parts.append(str(block.text))
            else:
                parts.append(str(block))
        return "\n".join(parts).strip()
    return str(content).strip()


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

