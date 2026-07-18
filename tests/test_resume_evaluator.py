import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from internly.agents.resume_evaluator import (
    _guess_name_from_resume,
    load_resume_text,
    evaluate_resume_text,
    evaluate_resume_file,
)
from internly.schemas import ResumeProfile


def test_load_resume_text_invalid_extension():
    with pytest.raises(ValueError, match="Resume must be a PDF or DOCX file."):
        load_resume_text("invalid_file.txt")


@patch("langchain_community.document_loaders.PyPDFLoader")
def test_load_resume_text_pdf(mock_pdf_loader_cls):
    mock_loader = MagicMock()
    mock_pdf_loader_cls.return_value = mock_loader
    
    mock_doc1 = MagicMock()
    mock_doc1.page_content = "First page content"
    mock_doc2 = MagicMock()
    mock_doc2.page_content = "Second page content"
    mock_loader.load.return_value = [mock_doc1, mock_doc2]
    
    text = load_resume_text("test_resume.pdf")
    assert text == "First page content\n\nSecond page content"
    mock_pdf_loader_cls.assert_called_once_with("test_resume.pdf")
    mock_loader.load.assert_called_once()


@patch("langchain_community.document_loaders.Docx2txtLoader")
def test_load_resume_text_docx(mock_docx_loader_cls):
    mock_loader = MagicMock()
    mock_docx_loader_cls.return_value = mock_loader
    
    mock_doc = MagicMock()
    mock_doc.page_content = "Word document content"
    mock_loader.load.return_value = [mock_doc]
    
    text = load_resume_text("test_resume.docx")
    assert text == "Word document content"
    mock_docx_loader_cls.assert_called_once_with("test_resume.docx")
    mock_loader.load.assert_called_once()


@patch("internly.agents.resume_evaluator.ChatPromptTemplate")
@patch("internly.agents.resume_evaluator.get_chat_model")
def test_evaluate_resume_text(mock_get_chat_model, mock_prompt_cls):
    mock_chain = MagicMock()
    mock_prompt = MagicMock()
    mock_prompt_cls.from_messages.return_value = mock_prompt
    mock_prompt.__or__ = MagicMock(return_value=mock_chain)

    expected_profile = ResumeProfile(
        skills=["Python", "FastAPI", "React"],
        years_experience=3.5,
        projects=["E-commerce backend", "Chatbot UI"],
        education="B.E. in Information Technology",
        notable_gaps=["6-month career break in 2024"],
    )
    mock_chain.invoke.return_value = expected_profile

    result = evaluate_resume_text("dummy resume text content")
    assert result == expected_profile
    mock_get_chat_model.assert_called_once_with(temperature=0)



@patch("internly.agents.resume_evaluator.load_resume_text")
@patch("internly.agents.resume_evaluator.evaluate_resume_text")
def test_evaluate_resume_file(mock_eval_text, mock_load_text):
    mock_load_text.return_value = "File text content"
    expected_profile = ResumeProfile(
        skills=["C++"],
        years_experience=1.0,
        projects=[],
        education="",
        notable_gaps=[]
    )
    mock_eval_text.return_value = expected_profile
    
    text, profile = evaluate_resume_file("some_file.pdf")
    assert text == "File text content"
    assert profile == expected_profile
    mock_load_text.assert_called_once_with("some_file.pdf")
    mock_eval_text.assert_called_once_with("File text content", None)


def test_guess_name_from_resume():
    text = "Rahul Sharma\nrahul@example.com\nSkills: Python"
    assert _guess_name_from_resume(text) == "Rahul Sharma"


@patch("internly.agents.resume_evaluator.ChatPromptTemplate")
@patch("internly.agents.resume_evaluator.get_chat_model")
def test_evaluate_resume_text_clears_jd_fields_without_jd(mock_get_chat_model, mock_prompt_cls):
    mock_chain = MagicMock()
    mock_prompt = MagicMock()
    mock_prompt_cls.from_messages.return_value = mock_prompt
    mock_prompt.__or__ = MagicMock(return_value=mock_chain)

    noisy_profile = ResumeProfile(
        name="",
        alignment_signals=["Grand Finalist, Smart India Hackathon"],
        skill_gaps=["No Java"],
        achievements=["Micromouse 3rd place"],
    )
    mock_chain.invoke.return_value = noisy_profile

    result = evaluate_resume_text("Priya Patel\nPython developer", job_description=None)

    assert result.alignment_signals == []
    assert result.skill_gaps == []
    assert result.name == "Priya Patel"
    assert result.achievements == ["Micromouse 3rd place"]
