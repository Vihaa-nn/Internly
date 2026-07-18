from __future__ import annotations

import re


def normalize_name(value: str) -> str:
    """Normalize company/role names for cache lookups without losing display text."""
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


_LOWERCASE_WORDS = frozenset(
    {"and", "or", "of", "the", "a", "an", "in", "for", "at", "to", "on"}
)


def _format_word(word: str, *, is_first: bool) -> str:
    if not word:
        return word
    if re.fullmatch(r"[A-Z]{2,}", word):
        return word
    if re.fullmatch(r"[A-Z0-9]+", word) and len(word) <= 5:
        return word
    lower = word.lower()
    if not is_first and lower in _LOWERCASE_WORDS:
        return lower
    return lower[:1].upper() + lower[1:]


def format_display_label(value: str) -> str:
    """Title-case company names, job titles, and similar user-entered labels."""
    trimmed = value.strip()
    if not trimmed:
        return ""

    parts: list[str] = []
    for word_index, word in enumerate(trimmed.split()):
        if "-" in word:
            hyphen_parts = word.split("-")
            parts.append(
                "-".join(
                    _format_word(part, is_first=word_index == 0 and part_index == 0)
                    for part_index, part in enumerate(hyphen_parts)
                )
            )
        else:
            parts.append(_format_word(word, is_first=word_index == 0))
    return " ".join(parts)


def parse_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace("%", "").strip())
    except ValueError:
        return None


def candidate_wants_to_move_on(text: str) -> bool:
    lowered = text.strip().lower()
    move_phrases = [
        "move on",
        "next question",
        "skip",
        "i give up",
        "show solution",
        "show me the solution",
    ]
    return any(phrase in lowered for phrase in move_phrases)


def is_underexplained_strategy_answer(text: str) -> bool:
    lowered = text.strip().lower()
    words = re.findall(r"[a-z0-9]+", lowered)
    if len(words) >= 18:
        return False

    strategy_terms = [
        "hashmap",
        "hash map",
        "dictionary",
        "dict",
        "set",
        "stack",
        "queue",
        "heap",
        "two pointer",
        "two pointers",
        "sliding window",
        "binary search",
        "bfs",
        "dfs",
        "dynamic programming",
        "dp",
        "recursion",
        "greedy",
    ]
    has_strategy = any(term in lowered for term in strategy_terms)
    explanation_markers = [
        "iterate",
        "loop",
        "for each",
        "while",
        "if",
        "else",
        "return",
        "store",
        "check",
        "complexity",
        "edge",
        "pseudocode",
        "step",
    ]
    has_explanation = any(marker in lowered for marker in explanation_markers)
    return has_strategy and not has_explanation
