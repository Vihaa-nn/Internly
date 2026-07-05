# Internly — AI Resume Evaluator & DSA-Only Mock Interview System

> **Read this entire file before writing or modifying any code in this repo.**
> This document exists so that anyone picking up this project understands not just
> *what* the code does, but *why* it's built this way — including deliberate scope
> restrictions that must NOT be casually expanded.

## 1. What this project is

Internly is a learning-focused, solo-developer, multi-agent AI application built with
LangChain + Google Gemini. It does exactly two things for a candidate:

1. **Evaluates a resume** and researches the target company's interview process
   (India-specific context).
2. **Conducts a DSA-only mock interview** (approach/pseudocode based, not a code editor)
   and produces a scored evaluation report at the end.

It is NOT a general interview simulator. It does not cover system design, HR, or
behavioral rounds. This is a deliberate, explicit scope decision — see Section 3.

## 2. High-level architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│ Resume Evaluator │     │   Research Agent      │     │  Interview Agent    │     │ Evaluation Agent  │
│  (agents/        │     │  (agents/             │     │  (agents/           │     │  (agents/         │
│  resume_         │     │  research_agent.py)   │     │  interview_agent.py)│     │  evaluation_      │
│  evaluator.py)   │     │                       │     │                     │     │  agent.py)        │
└────────┬─────────┘     └──────────┬────────────┘     └──────────┬──────────┘     └─────────┬─────────┘
         │                          │                             │                          │
         ▼                          ▼                             ▼                          ▼
   ResumeProfile              CompanyIntel                 InterviewAction              Evaluation
   (Pydantic)                 (Pydantic)                   (Pydantic)                   (Pydantic)
```

All four "agents" are **LangChain structured-output chains**, not LangChain
`AgentExecutor`/ReAct agents. None of them autonomously decide which tool to call.
**All branching logic (cache-check-before-scrape, hint caps, question selection) is
enforced in plain Python, not left to LLM discretion.** This is intentional — see
Section 4 for the reasoning.

Orchestration is plain Python (`internly/pipeline.py`, `internly/services/*.py`) —
there is **no LangGraph** in this project. This was a deliberate choice made early on
because the graph shape needed (branch + inner loop) is simple enough to hand-write and
the developer wanted to stay within plain LangChain rather than learn a second
framework.

## 3. Deliberate scope locks — do not silently expand these

These constraints were chosen on purpose and should be respected unless the user
explicitly asks to change them:

- **DSA/coding round only.** No system design, HR, or behavioral rounds. The
  `CompanyIntel` (interview_rounds, culture_notes, etc.) gathered by the Research Agent
  is shown to the candidate as *informational flavor only* — it must never drive
  multiple interview round types in the Interview Agent.
- **No code execution, no code editor, no sandboxing.** The candidate types their
  approach/pseudocode into a normal chat box. The Interview Agent evaluates *reasoning*,
  not runnable code. Do not add `streamlit-ace`, Judge0, Docker sandboxes, etc. unless
  explicitly requested — this was a conscious complexity cutoff.
- **No LangGraph.** Orchestration stays as plain Python functions/loops with an
  explicit state object, per `internly/pipeline.py` and `internly/services/`.
- **Max 3 hints per DSA question, enforced in code, not just prompted.** See
  `internly/services/interview_service.py::handle_candidate_turn` — there is a hard
  Python-level override (`if action.type == "hint" and hint_guide_count >= 2: force guide`)
  in addition to prompt instructions. Do not remove this safety net even if it seems
  redundant with the prompt.
- **No DSA data for a company → block the interview, do not fall back to Tavily search
  or generic questions.** This is enforced in `research_service.py::prepare_research_context`
  and `pipeline.py::run_pipeline_start`. The candidate simply sees "No DSA data is
  available for {company}."
- **`optimal_approach`/`optimal_time_complexity` per DSA question are generated
  LAZILY**, only the first time a question is actually selected for an interview
  (`interview_service.py::ensure_question_has_solution`), and cached in the
  `dsa_questions` table from then on. Do not batch-generate these for the entire
  ingested dataset — most rows are never used.

## 4. Key design decisions and why

- **Two independent caches, checked separately, both plain-Python-enforced:**
  - `dsa_questions` table — populated once via `scripts/ingest_dsa_questions.py` from a
    local clone of https://github.com/snehasishroy/leetcode-companywise-interview-questions
    (NOT committed into this repo — `datasets/` is intentionally an empty placeholder
    directory; you must clone the source repo separately and pass `--source-dir`).
  - `company_intel` table — the actual "check DB, else scrape+synthesize+save" cache for
    India-specific interview-process research (AmbitionBox, Glassdoor India, Naukri,
    Reddit r/developersIndia, JD pages via Tavily search).
  - Both company/role lookups are done via **normalized names**
    (`utils.normalize_name` — lowercases, strips non-alphanumerics) with a
    `UniqueConstraint` on the normalized columns, so "Google", "google", and "Google Inc"
    all hit the same cache row.
- **Chroma vector store is used ONLY for the raw scraped `company_intel` text**, not for
  resumes or interview transcripts (those are small enough to pass directly in prompts).
  Retrieval results are `lru_cache`'d in `vector_store.py::retrieve_company_context`
  since the same (company, role, query) triple is queried repeatedly during a single
  interview session.
- **Resume evaluation and company research run concurrently** in
  `pipeline.py::run_pipeline_start` via `ThreadPoolExecutor`, since they're independent
  LLM/network calls. The SQLAlchemy `session` is only touched on the main thread after
  both futures resolve — the worker threads only call pure agent functions. Chroma
  indexing after a cache-miss scrape happens in a background daemon thread so it doesn't
  block the UI.
- **The nested transcript structure**: `interview_sessions.transcript_json` is a list of
  question objects, each with its own `turns` list and a `resolved` boolean. See
  `db/models.py::InterviewSession` and `db/crud.py` (`append_question_to_session`,
  `append_interview_turn`, `mark_question_resolved`). Every sub-turn is persisted
  immediately, not just at question boundaries, so a session can be inspected or resumed
  mid-way.
- **The Evaluation Agent never sees the Interview Agent's internal `reasoning` field.**
  `InterviewAction.reasoning` (why the interviewer chose hint/followup/guide/accept) is
  used internally but is never written into `transcript_json` by
  `crud.append_interview_turn` (only `role`, `text`, `turn_type` are persisted). This
  keeps evaluation grounded in only what the candidate could actually see.
- **Question diversity scoring**: `interview_service.py::ask_next_question` does more
  than "pick top-N by frequency" — it scores candidate questions to avoid repeating
  difficulty levels and overlapping keywords/topics across the same session (e.g. avoid
  asking "3Sum" right after "Two Sum"). This is beyond the original spec but is a
  reasonable, low-risk enhancement.
- **The "Introduction" pseudo-question**: `crud.create_interview_session(..., include_greeting=True)`
  seeds the transcript with a special `"question": "Introduction"` entry so the
  interviewer can greet the candidate and ask about their background before DSA
  questions start. The Interview Agent's system prompt has a special branch for this
  ("SPECIAL PHASE: INTRODUCTION ROUND"). The Streamlit evaluation step explicitly filters
  this entry out of the transcript before calling the Evaluation Agent
  (`interview.py`, `clean_transcript = [q for q in ... if q.get("question") != "Introduction"]`).
  If you change the Introduction flow, keep this filter in sync.
- **LeetCode full-problem-text fetching**: `services/leetcode_service.py::fetch_question`
  live-queries LeetCode's public GraphQL endpoint with a spoofed browser `User-Agent`
  and a dummy CSRF token to pull full problem statements/hints/tags, since the ingested
  CSV dataset only has titles/difficulty/frequency/link — not full problem text. This
  fills a real gap (a candidate can't be asked "Two Sum" with zero context), but see
  Section 6 — it's a fragile, likely-ToS-noncompliant dependency, not a "core," durable
  part of the architecture.

## 5. Data model (SQLite via SQLAlchemy, `internly/db/models.py`)

```
candidates
  id, resume_text, skills(JSON), years_experience, projects(JSON), education,
  notable_gaps(JSON), target_role, target_company, created_at
  → has many interview_sessions

company_intel
  id, company, role, company_normalized, role_normalized,
  interview_rounds(JSON), common_questions(JSON), difficulty_notes, culture_notes,
  raw_research_text, last_updated
  UNIQUE(company_normalized, role_normalized)   ← the actual cache key

dsa_questions
  id, company, company_normalized, title, difficulty, frequency, acceptance, link,
  optimal_approach (nullable, lazy-generated), optimal_time_complexity (nullable, lazy-generated),
  created_at, updated_at
  UNIQUE(company_normalized, title, link)

interview_sessions
  id, candidate_id (FK), transcript_json(JSON), start_time, end_time
  transcript_json shape: [
    { "question_id": int|null, "question": str, "resolved": bool,
      "turns": [ {"role": "candidate"|"agent", "text": str, "type"?: "hint"|"followup"|"guide"|"accept"} ]
    }, ...
  ]
  → has one evaluation

evaluations
  id, session_id (FK, unique), technical_score(1-10), communication_score(1-10),
  role_fit_score(1-10), strengths(JSON), weaknesses(JSON), recommendation,
  detailed_feedback, created_at
```

Chroma (separate from SQLite): one collection `company_intel`, documents chunked at
~1800 chars / 200 overlap, metadata `{company, role}`, filtered similarity search.
Persisted to `./data/chroma` (path from `CHROMA_DIR` env var).

Pydantic schemas mirroring the above for LLM structured output:
`internly/schemas.py` — `ResumeProfile`, `CompanyIntel`, `InterviewAction`,
`OptimalSolution`, `Evaluation`, `PipelineStartResult`.

## 6. Known limitations / things a future contributor should know

- **`services/leetcode_service.py` scrapes LeetCode's GraphQL API with a spoofed
  User-Agent and a dummy CSRF token, live, on every question view.** This likely isn't
  compliant with LeetCode's Terms of Service, and it's fragile — if LeetCode changes
  its GraphQL schema, tightens bot detection, or rate-limits the IP, this silently
  degrades to the "Full problem statement could not be loaded" fallback in
  `interview.py`. Do not depend on this for anything beyond a personal/learning project.
- **LLM model is `gemini-3.5-flash` (default in `config.py`), not `gemini-2.5-flash`
  as originally planned.** This is a real model (GA as of mid-2026) and does have free-
  tier access as of the last check, but it is newer, still labeled "Preview" by some
  Google surfaces, has tighter free-tier rate limits than 2.5 Flash, and its pricing/
  quota terms are more likely to shift. If free-tier limits become a problem, consider
  reverting to `gemini-2.5-flash` via the `GEMINI_CHAT_MODEL` env var — no code change
  needed, it's fully config-driven.
- **`is_underexplained_strategy_answer` and `candidate_wants_to_move_on` in `utils.py`
  are keyword/heuristic-based**, not LLM-based. They're intentionally cheap fast-paths
  (see `interview_service.py::handle_candidate_turn` steps 2–3) to bypass an LLM call
  for obvious cases, but they will have false negatives/positives on unusual phrasing.
  This is an accepted MVP tradeoff, not a bug to "fix" by making them more clever without
  discussion — over-engineering this risks breaking the fast-path's purpose.
- **`vector_store.py::retrieve_company_context.cache_clear()` clears the ENTIRE lru_cache**
  on every new indexing call, not just entries for the affected company/role. Harmless at
  this project's scale (single user, few companies) but not fine-grained.
- **Streamlit pages build raw HTML strings with f-strings and `unsafe_allow_html=True`**
  throughout (`app.py`, `interview.py`) for the custom dark theme. LLM-generated text
  (resume fields, interview responses, evaluation feedback) is interpolated directly into
  this HTML without escaping. For a local single-user app this is a low real risk, but if
  this is ever exposed to untrusted input or multiple users, this needs proper escaping
  (e.g. `html.escape()`) before interpolation.
- **`NUM_INTERVIEW_QUESTIONS` defaults to 3** (`config.py`, env var
  `NUM_INTERVIEW_QUESTIONS`), not 2 as discussed in early planning. This is a config
  value, trivially changeable, not hardcoded logic.
- **`GEMINI_EMBEDDING_MODEL` defaults to `models/gemini-embedding-2`** — verify this
  model name is still current if embeddings calls start failing; embedding model names
  have changed more than once during 2026.

## 7. Environment variables (`.env`, never committed — see `.gitignore`)

```
GEMINI_API_KEY=            # required — from Google AI Studio, no card needed for free tier
TAVILY_API_KEY=            # required — for company interview-process research
GEMINI_CHAT_MODEL=gemini-3.5-flash        # optional override
GEMINI_EMBEDDING_MODEL=models/gemini-embedding-2   # optional override
DATABASE_URL=sqlite:///./data/internly.db  # optional override
CHROMA_DIR=./data/chroma                   # optional override
NUM_INTERVIEW_QUESTIONS=3                  # optional override
TOP_DSA_QUESTIONS=10                       # optional override
SQL_ECHO=false                             # optional, set true to log all SQL
```

A committed `.env.example` should mirror these keys with empty values — never commit
real keys. If a `.env` with real keys is ever accidentally committed, treat every key in
it as compromised and rotate immediately, then `git rm --cached .env` and add it to
`.gitignore` if it isn't already covered.

## 8. Repo file map

```
internly/
  config.py                    # Settings dataclass, reads .env via python-dotenv
  llm.py                       # Singleton factories for chat model + embedding model
  schemas.py                   # All Pydantic I/O schemas shared across agents
  pipeline.py                  # run_pipeline_start() — Phase-2/3 orchestration, threaded
  utils.py                     # normalize_name, parse_float, move-on / underexplained heuristics

  agents/                      # Pure LLM chains — no DB access, no orchestration logic
    resume_evaluator.py         # load_resume_text, evaluate_resume_text/_file
    research_agent.py           # search_company_interview_intel (Tavily), synthesize_company_intel
    interview_agent.py          # generate_optimal_solution, assess_candidate_response (the interviewer)
    evaluation_agent.py         # evaluate_interview

  services/                    # Orchestration + caching logic — DB-aware, calls agents/
    research_service.py         # prepare_research_context — the cache-check-then-scrape logic
    interview_service.py        # ask_next_question, handle_candidate_turn — the nested interview loop
    vector_store.py             # Chroma singleton, chunking, cached retrieval
    leetcode_service.py         # fetch_question — live LeetCode GraphQL scrape (see Section 6 caveats)

  db/
    database.py                 # engine/session setup (SQLite WAL mode, get_session() ctx manager)
    models.py                   # SQLAlchemy ORM models (see Section 5)
    crud.py                      # All DB read/write functions, upsert-aware

scripts/
  init_db.py                    # Create tables
  ingest_dsa_questions.py       # One-time CSV → dsa_questions table loader (needs --source-dir)
  demo_db.py, resume_text_demo.py, evaluate_sample_transcript.py, interview_cli.py
                                 # Standalone manual-test scripts for individual phases

streamlit_app/
  app.py                        # Page 1: resume/JD/company input → resume analysis + company intel display
  pages/interview.py            # Page 2: DSA question display (incl. live LeetCode fetch) + chat loop + final eval

tests/
  conftest.py                   # in-memory SQLite fixture (db_session)
  test_db_crud.py                # DB round-trip + model registration
  test_research_rules.py         # cache-hit/miss + normalized lookup rules
  test_research_service.py       # mocked verification that cache hits never call search/synth/index
  test_interview_answer_depth.py # underexplained-answer heuristic + followup behavior
  test_resume_evaluator.py       # resume evaluation chain

datasets/leetcode-companywise-interview-questions/   # intentionally empty — clone the real
                                                       # dataset repo separately, point
                                                       # ingest_dsa_questions.py at it
```

## 9. Setup (for a fresh clone)

```bash
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
cp .env.example .env    # then fill in GEMINI_API_KEY and TAVILY_API_KEY
python scripts/init_db.py
git clone https://github.com/snehasishroy/leetcode-companywise-interview-questions.git /some/path
python scripts/ingest_dsa_questions.py --source-dir /some/path
streamlit run streamlit_app/app.py
```

Run tests with `pytest` from the repo root (uses `tests/conftest.py`'s in-memory SQLite
fixture — no real API keys needed for the DB/logic tests; `test_resume_evaluator.py` and
similar may need a real `GEMINI_API_KEY` if they hit the actual LLM rather than mocking
it — check each test file before assuming full offline coverage).

## 10. Before extending this project

- Re-read Section 3 before adding anything that smells like: a code editor, code
  execution, multiple interview round types, LangGraph, or LLM-driven (rather than
  Python-enforced) cache/hint-cap logic. These are constraints, not oversights.
- Follow the existing pattern of "agents/ = pure LLM chains, services/ = DB-aware
  orchestration that calls agents/" — don't put DB calls inside `agents/*.py`, and don't
  put prompt-construction inside `services/*.py`.
- New DB fields/tables → update both `db/models.py` and the corresponding CRUD function
  in `db/crud.py`, and add/extend a test in `tests/test_db_crud.py`.
- If hint-cap behavior, question-selection logic, or the cache-check order changes,
  update the corresponding test in `test_research_rules.py` /
  `test_interview_answer_depth.py` — these tests exist specifically to lock in the
  Python-enforced behavior described in Section 4, and should fail loudly if that
  behavior regresses.
- Don't relax the scope locks in Section 3 without a deliberate decision to do so —
  they were chosen on purpose, not defaults left unexamined.