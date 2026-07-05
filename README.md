# Internly

Internly is a learning-focused multi-agent AI project for resume review and DSA-only mock interviews.

The app uses plain Python orchestration with a shared state dictionary, LangChain, Gemini, SQLite, Chroma, Tavily, and Streamlit. It deliberately does not use LangGraph, system design rounds, HR rounds, code execution, or a code editor.

## Setup

1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies:

```powershell
pip install -e ".[dev]"
```

3. Copy `.env.example` to `.env` and fill in:

```text
GEMINI_API_KEY=...
TAVILY_API_KEY=...
```

4. Initialize the database:

```powershell
python scripts/init_db.py
```

5. Run the database demo:

```powershell
python scripts/demo_db.py
```

## Main Workflow

Build and verify one phase at a time:

1. Database layer
2. Resume evaluator
3. Research agent and DSA ingestion
4. Evaluation agent
5. Interview agent CLI
6. Pipeline orchestration
7. Streamlit frontend

## DSA Question Ingestion

The project expects the companywise DSA dataset to be ingested into SQLite before interviews begin.

```powershell
python scripts/ingest_dsa_questions.py --source-dir path\to\leetcode-companywise-interview-questions
```

If a target company has no ingested rows, the interview is blocked with a clear message. The app does not search Tavily or invent generic questions as a fallback.

## Run Streamlit

```powershell
streamlit run streamlit_app/app.py
```

