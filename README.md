# Internly

**AI mock interviews tailored to your resume, target company, and role.**

Internly is a multi-agent interview prep platform built for India-focused tech hiring. Upload a resume, choose a company and role, and practice a realistic coding-round interview with an adaptive AI interviewer — complete with live LeetCode problem statements, personalized feedback, and a scored evaluation report.

**Stack:** Python · LangChain · Google Gemini · FastAPI · SQLite · Chroma · Next.js

---

## Highlights

- **Resume intelligence** — PDF/DOCX parsing with structured extraction of skills, projects, achievements, experience, and optional JD alignment signals
- **Company-aware preparation** — Live web research (Tavily) synthesized into interview intel and a cached per-company interview playbook
- **Adaptive AI interviewer** — Personalized intro, contextual follow-ups, LeetCode-style hints, and trajectory-aware questioning driven by a dedicated interview agent
- **Company-specific DSA rounds** — Questions drawn from a company-wise LeetCode dataset with smart selection (difficulty spread, topic diversity, frequency weighting)
- **Session RAG** — Per-interview vector retrieval over resume, JD, and question context so every turn stays grounded in the candidate's profile
- **Rich evaluation report** — Technical, communication, and resume-alignment scores with per-question breakdown and mentor-style feedback
- **Modern UI** — Next.js interview workspace with live problem panel, progress tracking, and evaluation dashboard

---

## How it works

### 1. Analyse

Upload a resume and target company/role. Internly runs resume parsing and company research **in parallel**:

- Extracts a structured `ResumeProfile` (name, skills, projects, achievements, gaps, JD signals)
- Researches the company's interview process and generates a reusable interview playbook
- Surfaces company intel on the landing page before the interview begins

Optional job description unlocks JD alignment strengths and skill-gap analysis.

### 2. Interview

A three-stage mock coding round:

1. **Intro** — LLM-generated greeting that references the candidate's background and projects
2. **Technical questions** — Up to three company-specific problems with live LeetCode statements
3. **Adaptive dialogue** — Chat-based approach discussion (algorithm, data structures, complexity) with hint/follow-up/guide/accept actions

The interviewer enforces interview discipline: complexity must be stated before acceptance, hints are capped at three per question, and explicit skip/move-on requests are honored immediately.

### 3. Evaluate

A dedicated evaluation agent produces a full report:

| Score | What it measures |
|-------|------------------|
| **Technical** | Problem-solving quality across the interview transcript |
| **Communication** | Clarity and structure of explanations |
| **Resume alignment** | Fit between resume profile and target role/company |

Plus per-question outcomes, hint counts, strengths, weaknesses, and actionable recommendations.

---

## Architecture

```
┌──────────────┐     ┌─────────────────────────────────────────┐     ┌──────────────┐
│  Next.js UI  │────▶│  FastAPI (internly/api.py)              │────▶│  SQLite      │
│  frontend/   │     │  pipeline · services · db/crud          │     │  data/       │
└──────────────┘     └──────────────┬──────────────────────────┘     └──────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              agents/*.py    Chroma session RAG   LeetCode GraphQL
              (LLM chains)   (per interview)     (problem text)
```

### Multi-agent design

| Agent | Responsibility |
|-------|----------------|
| `resume_evaluator` | Parse resume files/text into structured profiles |
| `research_agent` | Web search, company intel synthesis, playbook generation |
| `interview_agent` | Intro greeting, turn assessment, optimal solution generation |
| `evaluation_agent` | Post-interview scoring and feedback report |

Agents are pure LangChain structured-output chains with **no direct DB access** — orchestration lives in `services/` and `pipeline.py`.

### Key services

| Module | Role |
|--------|------|
| `pipeline.py` | Parallel analyse-phase orchestration (resume + research) |
| `interview_service.py` | Session lifecycle, question selection, turn handling, hint-cap enforcement |
| `vector_store.py` | Per-session Chroma indexing and structured retrieval |
| `research_service.py` | Company intel caching and playbook backfill |
| `leetcode_service.py` | Live problem statement fetch via LeetCode GraphQL |

### Session RAG

Each interview session gets its own Chroma collection scoped by `session_id`. Documents are tagged by type (`resume`, `jd`, `question`) and retrieved with compound filters so the interviewer always has the right context for the current turn. Company playbooks are cached in SQLite for fast reuse across sessions.

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- [Gemini API key](https://aistudio.google.com/apikey)
- [Tavily API key](https://tavily.com)

---

## Setup

### 1. Backend

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev]"

copy .env.example .env
# Edit .env — set GEMINI_API_KEY and TAVILY_API_KEY

python scripts/init_db.py
```

### 2. DSA question dataset

Internly uses an external company-wise LeetCode dataset. Clone and ingest it once:

```powershell
git clone https://github.com/snehasishroy/leetcode-companywise-interview-questions.git C:\path\to\dataset
python scripts/ingest_dsa_questions.py --source-dir C:\path\to\dataset
```

This populates `dsa_questions` with company-tagged problems used during question selection.

### 3. Run

**Terminal 1 — API**

```powershell
.\.venv\Scripts\uvicorn.exe internly.api:app --reload --port 8000
```

**Terminal 2 — Frontend**

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/analyse` | Upload resume + company/role (+ optional JD) |
| `POST` | `/api/interview/start` | Start session with personalized intro |
| `POST` | `/api/interview/next-question` | Fetch next company-specific question |
| `POST` | `/api/interview/turn` | Candidate message → interviewer response |
| `POST` | `/api/interview/evaluate` | Generate final evaluation report |
| `POST` | `/api/leetcode/fetch` | Load problem statement from LeetCode link |

---

## Configuration

See `.env.example`.

| Variable | Default | Notes |
|----------|---------|-------|
| `GEMINI_API_KEY` | — | Required |
| `TAVILY_API_KEY` | — | Required for company research |
| `GEMINI_CHAT_MODEL` | `gemini-3.5-flash` | Chat model |
| `GEMINI_EMBEDDING_MODEL` | `models/gemini-embedding-2` | Embeddings for session RAG |
| `DATABASE_URL` | `sqlite:///./data/internly.db` | Resolved from repo root |
| `CHROMA_DIR` | `./data/chroma` | Resolved from repo root |
| `NUM_INTERVIEW_QUESTIONS` | `3` | Questions per interview session |
| `TOP_DSA_QUESTIONS` | `10` | Candidate pool size for selection |

Paths starting with `./` resolve relative to the **repository root**.

---

## Project layout

```
internly/
  api.py              FastAPI HTTP layer
  pipeline.py         Analyse orchestration
  config.py           Settings from .env
  schemas.py          Pydantic models
  agents/             LLM agent chains
  services/           Business logic (interview, research, RAG, LeetCode)
  db/                 SQLAlchemy models + CRUD

frontend/             Next.js app (landing, interview, evaluation)
scripts/              DB init, dataset ingest, CLI tools
tests/                pytest suite
data/                 SQLite + Chroma (gitignored, created at runtime)
```

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/init_db.py` | Create / migrate SQLite tables |
| `scripts/ingest_dsa_questions.py` | Load company-wise LeetCode CSVs |
| `scripts/interview_cli.py` | Terminal-based interview demo |
| `scripts/demo_db.py` | Seed sample rows for testing |
| `scripts/resume_text_demo.py` | Resume parsing smoke test |
| `scripts/evaluate_sample_transcript.py` | Evaluation agent smoke test |

---

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Uses in-memory SQLite (`tests/conftest.py`). LLM and network calls are mocked — no API keys required.

---

## Implementation notes

Useful context for contributors and AI assistants working in this repo:

- **Question selection** scores candidates by frequency, difficulty spread, and topic diversity; prefers free LeetCode problems when Premium-only links are detected
- **Optimal solutions** are generated lazily on first use and cached in `dsa_questions` for consistent guide/accept responses
- **Hint trajectory** is tracked per question; the service forces a full guide after three hint/guide turns
- **Introduction round** is stored as `"Introduction"` in the transcript and excluded from technical evaluation
- **Company playbook** is lazily backfilled on cache hits so older intel records gain playbook text without re-searching
- **Accept gate** requires both time and space complexity before the interviewer advances to the next question
