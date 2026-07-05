import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from internly.agents.resume_evaluator import load_resume_text, evaluate_resume_text, evaluate_resume_file
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


@patch("internly.agents.resume_evaluator.get_chat_model")
def test_evaluate_resume_text(mock_get_chat_model):
    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_get_chat_model.return_value = mock_llm
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    expected_profile = ResumeProfile(
        skills=["Python", "FastAPI", "React"],
        years_experience=3.5,
        projects=["E-commerce backend", "Chatbot UI"],
        education="B.E. in Information Technology",
        notable_gaps=["6-month career break in 2024"]
    )
    mock_structured_llm.return_value = expected_profile
    mock_structured_llm.invoke.return_value = expected_profile
    
    result = evaluate_resume_text("dummy resume text content")
    assert result == expected_profile
    mock_get_chat_model.assert_called_once_with(temperature=0)
    mock_llm.with_structured_output.assert_called_once_with(ResumeProfile)



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
