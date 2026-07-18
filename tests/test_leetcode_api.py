from unittest.mock import patch

from internly.api import LeetCodeRequest, leetcode_fetch


@patch("internly.api.fetch_question")
def test_leetcode_fetch_returns_problem(mock_fetch):
    mock_fetch.return_value = {
        "title": "Add Binary",
        "difficulty": "Easy",
        "content_html": "<p>Given two binary strings...</p>",
        "topic_tags": ["Math", "String"],
        "hints": ["Use carry"],
        "paid_only": False,
    }

    result = leetcode_fetch(LeetCodeRequest(link="https://leetcode.com/problems/add-binary/"))

    assert result["found"] is True
    assert result["title"] == "Add Binary"
    assert "binary strings" in result["content_html"]
    mock_fetch.assert_called_once_with("https://leetcode.com/problems/add-binary/")


@patch("internly.api.fetch_question", return_value=None)
def test_leetcode_fetch_not_found(mock_fetch):
    result = leetcode_fetch(LeetCodeRequest(link="https://leetcode.com/problems/missing/"))
    assert result == {"found": False}
    mock_fetch.assert_called_once()
