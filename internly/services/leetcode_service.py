from __future__ import annotations

import re
import html as html_module
from typing import TypedDict


class LeetCodeQuestion(TypedDict):
    title: str
    difficulty: str
    content_html: str          # raw HTML from LeetCode
    topic_tags: list[str]
    hints: list[str]


def _slug_from_url(url: str) -> str | None:
    """Extract the problem slug from a LeetCode problems URL."""
    if not url:
        return None
    match = re.search(r"leetcode\.com/problems/([^/?#]+)", url)
    return match.group(1) if match else None


def fetch_question(link: str | None) -> LeetCodeQuestion | None:
    """
    Fetch the full question detail from LeetCode's public GraphQL API.
    Returns None on failure (network error, unsupported link, etc.).
    """
    if not link:
        return None

    slug = _slug_from_url(link)
    if not slug:
        return None

    query = """
    query getQuestionDetail($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        title
        difficulty
        content
        topicTags { name }
        hints
      }
    }
    """

    try:
        import requests  # already a dependency via langchain

        resp = requests.post(
            "https://leetcode.com/graphql/",
            json={"query": query, "variables": {"titleSlug": slug}},
            headers={
                "Content-Type": "application/json",
                "Referer": f"https://leetcode.com/problems/{slug}/",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "x-csrftoken": "dummy",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        q = (data.get("data") or {}).get("question")
        if not q:
            return None

        return LeetCodeQuestion(
            title=q.get("title") or slug,
            difficulty=q.get("difficulty") or "",
            content_html=q.get("content") or "",
            topic_tags=[t["name"] for t in (q.get("topicTags") or [])],
            hints=[h for h in (q.get("hints") or []) if h],
        )

    except Exception:
        return None
