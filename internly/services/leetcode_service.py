from __future__ import annotations

import re
from typing import TypedDict


class LeetCodeQuestion(TypedDict):
    title: str
    difficulty: str
    content_html: str
    topic_tags: list[str]
    hints: list[str]
    paid_only: bool


_GRAPHQL_QUERY = """
query getQuestionDetail($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    title
    difficulty
    content
    translatedContent
    topicTags { name }
    hints
    isPaidOnly
  }
}
"""

_HEADERS_TEMPLATE = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "x-csrftoken": "dummy",
}


def _slug_from_url(url: str) -> str | None:
    if not url:
        return None
    match = re.search(r"leetcode\.com/problems/([^/?#]+)", url)
    return match.group(1) if match else None


def _paid_only_fallback_html(title: str, difficulty: str) -> str:
    diff = difficulty or "Unknown"
    return (
        f"<p><strong>{title}</strong> is a LeetCode <em>Premium</em> problem "
        f"(difficulty: {diff}). The public API does not include the full statement.</p>"
        "<p>Open the LeetCode link above to read the problem if you have Premium access, "
        "or work from the title and your knowledge of the pattern.</p>"
    )


def is_paid_only_link(link: str | None) -> bool:
    """Return True when LeetCode marks this problem as Premium-only."""
    slug = _slug_from_url(link)
    if not slug:
        return False
    try:
        import requests

        resp = requests.post(
            "https://leetcode.com/graphql/",
            json={"query": _GRAPHQL_QUERY, "variables": {"titleSlug": slug}},
            headers={
                **_HEADERS_TEMPLATE,
                "Referer": f"https://leetcode.com/problems/{slug}/",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return False
        q = (resp.json().get("data") or {}).get("question")
        return bool(q and q.get("isPaidOnly"))
    except Exception:
        return False


def fetch_question(link: str | None) -> LeetCodeQuestion | None:
    """Fetch question detail from LeetCode GraphQL. Returns None on hard failure."""
    if not link:
        return None

    slug = _slug_from_url(link)
    if not slug:
        return None

    try:
        import requests

        resp = requests.post(
            "https://leetcode.com/graphql/",
            json={"query": _GRAPHQL_QUERY, "variables": {"titleSlug": slug}},
            headers={
                **_HEADERS_TEMPLATE,
                "Referer": f"https://leetcode.com/problems/{slug}/",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        q = (data.get("data") or {}).get("question")
        if not q:
            return None

        paid_only = bool(q.get("isPaidOnly"))
        content = (q.get("content") or q.get("translatedContent") or "").strip()
        title = q.get("title") or slug
        difficulty = q.get("difficulty") or ""

        if not content and paid_only:
            content = _paid_only_fallback_html(title, difficulty)

        return LeetCodeQuestion(
            title=title,
            difficulty=difficulty,
            content_html=content,
            topic_tags=[t["name"] for t in (q.get("topicTags") or [])],
            hints=[h for h in (q.get("hints") or []) if h],
            paid_only=paid_only,
        )

    except Exception:
        return None
