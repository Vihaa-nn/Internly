from __future__ import annotations

import streamlit as st

from internly.agents.evaluation_agent import evaluate_interview
from internly.db import crud
from internly.db.database import get_session, init_db
from internly.db.models import Candidate, InterviewSession
from internly.pipeline import resume_profile_from_candidate
from internly.schemas import CompanyIntel
from internly.services.interview_service import (
    ask_next_question,
    handle_candidate_turn,
    start_interview_session,
)
from internly.services.leetcode_service import fetch_question

st.set_page_config(
    page_title="Internly – Mock Interview",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()

# ── guard: must arrive from the analysis page ──────────────────────────────────
pipeline_result = st.session_state.get("pipeline_result")
if pipeline_result is None:
    st.error("No session found. Please go back and analyze your resume first.")
    if st.button("← Back to Resume Analysis"):
        st.switch_page("app.py")
    st.stop()

company = st.session_state.get("target_company", "")
role    = st.session_state.get("target_role", "")

# ── styles ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: #0f0f13; }
    #MainMenu, footer, header { visibility: hidden; }

    /* ── topbar ── */
    .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.2rem 0 1.5rem;
        border-bottom: 1px solid #1e1e2e;
        margin-bottom: 1.8rem;
    }
    .topbar-brand {
        font-size: 1.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #e0e7ff 0%, #a5b4fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .topbar-meta { color: #64748b; font-size: 0.82rem; }
    .topbar-meta span {
        background: rgba(99,102,241,0.12);
        color: #a5b4fc;
        border-radius: 6px;
        padding: 0.2rem 0.6rem;
        font-weight: 500;
        margin-left: 0.4rem;
    }

    /* ── question card ── */
    .q-card {
        background: linear-gradient(145deg, #1e1e2e, #16162a);
        border: 1px solid #2d2d4a;
        border-radius: 16px;
        padding: 1.8rem 2rem 1.4rem;
        margin-bottom: 1.5rem;
    }
    .q-header {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin-bottom: 1.1rem;
        flex-wrap: wrap;
    }
    .q-label {
        font-size: 0.67rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #6366f1;
    }
    .q-title {
        color: #e2e8f0;
        font-size: 1.35rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    .diff-badge {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.2rem 0.65rem;
        border-radius: 6px;
        letter-spacing: 0.05em;
    }
    .diff-easy   { background: rgba(16,185,129,0.15); color: #6ee7b7; }
    .diff-medium { background: rgba(251,191,36,0.15);  color: #fbbf24; }
    .diff-hard   { background: rgba(239,68,68,0.15);   color: #fca5a5; }

    .tag-chip {
        display: inline-block;
        background: rgba(99,102,241,0.1);
        color: #818cf8;
        border: 1px solid rgba(99,102,241,0.2);
        border-radius: 5px;
        font-size: 0.68rem;
        font-weight: 500;
        padding: 0.15rem 0.5rem;
        margin: 0 0.2rem 0.2rem 0;
    }
    .lc-link {
        display: inline-block;
        color: #f97316;
        font-size: 0.75rem;
        font-weight: 600;
        text-decoration: none;
        background: rgba(249,115,22,0.1);
        border: 1px solid rgba(249,115,22,0.25);
        border-radius: 6px;
        padding: 0.15rem 0.55rem;
    }
    .lc-link:hover { background: rgba(249,115,22,0.2); }

    /* LeetCode content HTML styles */
    .lc-content {
        color: #cbd5e1;
        font-size: 0.9rem;
        line-height: 1.75;
        margin-top: 1rem;
    }
    .lc-content p   { margin: 0.5rem 0; }
    .lc-content strong { color: #e2e8f0; }
    .lc-content em  { color: #a5b4fc; }
    .lc-content pre {
        background: #0f0f1a;
        border: 1px solid #2d2d4a;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: #a5b4fc;
        overflow-x: auto;
        margin: 0.7rem 0;
    }
    .lc-content code {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: #a5b4fc;
        background: rgba(99,102,241,0.1);
        padding: 0.1rem 0.35rem;
        border-radius: 4px;
    }
    .lc-content ul, .lc-content ol {
        padding-left: 1.4rem;
        margin: 0.5rem 0;
    }
    .lc-content li { margin: 0.25rem 0; }
    .lc-content sup { font-size: 0.7rem; }

    .q-hint {
        color: #475569;
        font-size: 0.8rem;
        margin-top: 1rem;
        padding-top: 0.8rem;
        border-top: 1px solid #1e1e2e;
        font-style: italic;
    }

    /* ── chat messages ── */
    .msg-user {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 0.9rem;
    }
    .msg-user-bubble {
        background: linear-gradient(135deg, #6366f1, #7c3aed);
        color: #fff;
        border-radius: 18px 18px 4px 18px;
        padding: 0.75rem 1.1rem;
        max-width: 75%;
        font-size: 0.9rem;
        line-height: 1.55;
        box-shadow: 0 4px 16px rgba(99,102,241,0.25);
    }
    .msg-agent {
        display: flex;
        justify-content: flex-start;
        margin-bottom: 0.9rem;
        align-items: flex-start;
        gap: 0.65rem;
    }
    .msg-agent-avatar {
        width: 30px; height: 30px;
        border-radius: 50%;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        display: flex; align-items: center; justify-content: center;
        font-size: 0.85rem;
        flex-shrink: 0;
        margin-top: 2px;
    }
    .msg-agent-bubble {
        background: #1e1e2e;
        border: 1px solid #2d2d4a;
        color: #cbd5e1;
        border-radius: 4px 18px 18px 18px;
        padding: 0.75rem 1.1rem;
        max-width: 75%;
        font-size: 0.9rem;
        line-height: 1.6;
    }
    .msg-type-badge {
        font-size: 0.62rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        padding: 0.1rem 0.45rem;
        border-radius: 4px;
        margin-bottom: 0.3rem;
        display: inline-block;
    }
    .badge-hint     { background:rgba(251,191,36,0.15); color:#fbbf24; }
    .badge-followup { background:rgba(99,102,241,0.15); color:#a5b4fc; }
    .badge-guide    { background:rgba(239,68,68,0.12);  color:#fca5a5; }
    .badge-accept   { background:rgba(16,185,129,0.12); color:#6ee7b7; }

    /* ── buttons ── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.7rem 1.5rem !important;
        font-size: 0.9rem !important;
        box-shadow: 0 4px 20px rgba(99,102,241,0.35) !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 8px 28px rgba(99,102,241,0.5) !important;
    }
    .stButton > button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid #2d2d4a !important;
        color: #94a3b8 !important;
        border-radius: 12px !important;
        font-size: 0.85rem !important;
    }

    /* ── score / evaluation ── */
    .score-card {
        background: linear-gradient(145deg,#1e1e2e,#16162a);
        border: 1px solid #2d2d4a;
        border-radius: 16px;
        padding: 1.6rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .score-num {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg,#6366f1,#8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .score-lbl { color:#64748b; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.1em; }
    .eval-section {
        background: #1a1a2e;
        border: 1px solid #2d2d4a;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
    }
    .eval-section h4 { color:#94a3b8; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.12em; margin:0 0 0.8rem; }
    .eval-list-item { color:#cbd5e1; font-size:0.88rem; padding:0.3rem 0; border-bottom:1px solid #1e1e2e; }
    .eval-list-item:last-child { border-bottom:none; }

    .divider { border:none; border-top:1px solid #1e1e2e; margin:1.5rem 0; }
    .stChatInput textarea {
        background: #1a1a2e !important;
        border: 1px solid #2d2d4a !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        font-family: 'Inter', sans-serif !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── topbar ─────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="topbar">
        <div class="topbar-brand">⚡ Internly</div>
        <div class="topbar-meta">
            Interviewing for<span>{role}</span> at <span>{company}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button("← Back to Resume Analysis", key="back_btn"):
    st.switch_page("app.py")

st.markdown("<hr class='divider'>", unsafe_allow_html=True)


# ── session state defaults ─────────────────────────────────────────────────────
for key, default in {
    "interview_session_id": None,
    "used_question_ids": set(),
    "active_question_index": None,
    "active_question_text": None,
    "active_question_link": None,
    "active_question_difficulty": None,
    "active_question_tags": [],
    "lc_content_html": None,      # cached fetched LeetCode HTML
    "chat_history": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── initialize interview session if needed ─────────────────────────────────────
if not st.session_state.interview_session_id:
    with get_session() as session:
        interview = start_interview_session(session, pipeline_result.candidate_id, include_greeting=True)
        st.session_state.interview_session_id = interview.id
        st.session_state.used_question_ids    = set()
        st.session_state.active_question_index = 0
        st.session_state.active_question_text  = "Introduction"
        st.session_state.active_question_link  = None
        st.session_state.lc_content_html       = ""
        
        # Load the greeting turn from the database transcript
        turns = interview.transcript_json[0]["turns"]
        st.session_state.chat_history = [
            {"role": t["role"], "text": t["text"], "type": t.get("type", "followup")}
            for t in turns
        ]


# ── fetch next question if none is active ─────────────────────────────────────
if st.session_state.active_question_text is None:
    with get_session() as session:
        asked = ask_next_question(
            session,
            interview_session_id=st.session_state.interview_session_id,
            company=company,
            used_question_ids=st.session_state.used_question_ids,
        )
    if asked:
        st.session_state.active_question_index      = asked.question_index
        st.session_state.active_question_text       = asked.display_text
        st.session_state.active_question_link       = asked.question_link
        st.session_state.active_question_difficulty = asked.question.difficulty or ""
        st.session_state.active_question_tags       = []   # will be filled after LeetCode fetch
        st.session_state.lc_content_html            = None # reset so we re-fetch
        
        # Add transition message to chat history
        st.session_state.chat_history.append({
            "role": "agent",
            "text": f"Here is our next technical question: **{asked.display_text}**. Please review the problem description on the left, then outline your approach.",
            "type": "followup"
        })
    else:
        st.session_state.active_question_text = None


# ── fetch LeetCode content if we have a link but no cached content ─────────────
if st.session_state.active_question_link and st.session_state.lc_content_html is None:
    with st.spinner("📡 Fetching full question from LeetCode…"):
        lc = fetch_question(st.session_state.active_question_link)
    if lc:
        st.session_state.lc_content_html      = lc["content_html"]
        st.session_state.active_question_tags  = lc["topic_tags"]
        if lc["difficulty"]:
            st.session_state.active_question_difficulty = lc["difficulty"]
    else:
        st.session_state.lc_content_html = ""   # mark as attempted but failed


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN LAYOUT  — split into question panel (left) + chat panel (right)
# ═══════════════════════════════════════════════════════════════════════════════
q_col, chat_col = st.columns([5, 4], gap="large")

# ── LEFT: question display ─────────────────────────────────────────────────────
with q_col:
    active_q = st.session_state.active_question_text
    link     = st.session_state.active_question_link
    diff     = (st.session_state.active_question_difficulty or "").strip()
    tags     = st.session_state.active_question_tags or []

    if active_q:
        if active_q == "Introduction":
            body_section = (
                f'<div class="lc-content">'
                f'<p>Welcome to your interview at <strong>{company}</strong> for the <strong>{role}</strong> position!</p>'
                f'<p>Before we begin the technical challenge, please take a moment to introduce yourself in the chat on the right.</p>'
                f'<p><strong>Suggested topics to cover:</strong></p>'
                f'<ul>'
                f'<li>Your professional background and technical stack</li>'
                f'<li>Key projects you have built recently</li>'
                f'<li>Your interest in this target role</li>'
                f'</ul>'
                f'</div>'
            )
            st.markdown(
                f"""
                <div class="q-card">
                    <div class="q-label">👋 Welcome to Internly</div>
                    <div class="q-header">
                        <div class="q-title">Candidate Introduction</div>
                    </div>
                    {body_section}
                    <div class="q-hint">
                        💬 Please respond to the interviewer's greeting in the chat panel on the right.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            diff_cls = {
                "easy":   "diff-easy",
                "medium": "diff-medium",
                "hard":   "diff-hard",
            }.get(diff.lower(), "diff-medium")

            diff_badge = f'<span class="diff-badge {diff_cls}">{diff}</span>' if diff else ""
            lc_link_html = (
                f'<a class="lc-link" href="{link}" target="_blank">🔗 LeetCode</a>'
                if link else ""
            )
            tags_html = "".join(f'<span class="tag-chip">{t}</span>' for t in tags)

            # full LeetCode content or fallback
            content_html = st.session_state.lc_content_html or ""
            if content_html:
                body_section = f'<div class="lc-content">{content_html}</div>'
            else:
                # LeetCode fetch failed or no link — just show the title nicely
                body_section = (
                    '<div class="lc-content" style="color:#64748b;font-style:italic;">'
                    'Full problem statement could not be loaded. '
                    'Open the LeetCode link above, read the problem, then describe your approach here.'
                    '</div>'
                )

            st.markdown(
                f"""
                <div class="q-card">
                    <div class="q-label">🧩 DSA Question</div>
                    <div class="q-header">
                        <div class="q-title">{active_q}</div>
                        {diff_badge}
                        {lc_link_html}
                    </div>
                    {('<div style="margin-bottom:0.9rem">' + tags_html + '</div>') if tags_html else ''}
                    {body_section}
                    <div class="q-hint">
                        💬 Explain your approach, data structures, and time/space complexity below.
                        Type <em>"move on"</em> or <em>"skip"</em> to go to the next question.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            """
            <div class="q-card" style="text-align:center;color:#64748b;padding:2.5rem;">
                <div style="font-size:2rem;margin-bottom:0.5rem;">✅</div>
                All DSA questions have been covered.<br>Generate your final evaluation below.
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── RIGHT: chat panel ──────────────────────────────────────────────────────────
with chat_col:
    st.markdown(
        '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.15em;'
        'text-transform:uppercase;color:#6366f1;margin-bottom:1rem;">💬 Your Response</p>',
        unsafe_allow_html=True,
    )

    # render chat history
    chat_html = ""
    for turn in st.session_state.chat_history:
        if turn["role"] == "user":
            chat_html += (
                f'<div class="msg-user">'
                f'<div class="msg-user-bubble">{turn["text"]}</div>'
                f'</div>'
            )
        else:
            badge_cls = {
                "hint":     "badge-hint",
                "followup": "badge-followup",
                "guide":    "badge-guide",
                "accept":   "badge-accept",
            }.get(turn.get("type", ""), "badge-followup")
            type_label = (turn.get("type") or "agent").upper()
            chat_html += (
                f'<div class="msg-agent">'
                f'<div class="msg-agent-avatar">🤖</div>'
                f'<div>'
                f'<span class="msg-type-badge {badge_cls}">{type_label}</span>'
                f'<div class="msg-agent-bubble">{turn["text"]}</div>'
                f'</div></div>'
            )

    if chat_html:
        st.markdown(chat_html, unsafe_allow_html=True)

    # chat input (only when a question is active)
    if st.session_state.active_question_text:
        user_input = st.chat_input("Describe your approach or pseudocode…")
        if user_input:
            with get_session() as session:
                candidate = session.get(Candidate, pipeline_result.candidate_id)
                if not candidate:
                    st.error("Candidate record was not found.")
                    st.stop()

                action = handle_candidate_turn(
                    session,
                    interview_session_id=st.session_state.interview_session_id,
                    question_index=st.session_state.active_question_index,
                    candidate_response=user_input,
                    resume_profile=resume_profile_from_candidate(candidate),
                    company_intel=pipeline_result.company_intel or CompanyIntel(),
                    company=company,
                    role=role,
                )

            st.session_state.chat_history.append({"role": "user", "text": user_input})
            st.session_state.chat_history.append(
                {"role": "agent", "text": action.text, "type": action.type}
            )

            if action.type == "accept":
                # clear current question — next rerun will auto-fetch new one
                st.session_state.active_question_index      = None
                st.session_state.active_question_text       = None
                st.session_state.active_question_link       = None
                st.session_state.lc_content_html            = None
                st.session_state.active_question_tags       = []
                # Keep chat history continuous (do not reset!)

            st.rerun()

    # ── final evaluation ───────────────────────────────────────────────────────
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    if st.session_state.interview_session_id:
        if st.button("📊 Generate Final Evaluation", type="primary", key="gen_eval_btn"):
            with st.spinner("Evaluating your performance…"):
                with get_session() as session:
                    interview = session.get(InterviewSession, st.session_state.interview_session_id)
                    candidate = session.get(Candidate, pipeline_result.candidate_id)
                    if not interview or not candidate:
                        st.error("Interview records were not found.")
                        st.stop()

                    # Filter out introduction round before evaluation
                    clean_transcript = [
                        q for q in (interview.transcript_json or [])
                        if q.get("question") != "Introduction"
                    ]
                    evaluation = evaluate_interview(
                        transcript=clean_transcript,
                        resume_profile=resume_profile_from_candidate(candidate),
                        company_intel=pipeline_result.company_intel,
                    )
                    crud.save_evaluation(session, interview.id, evaluation)
                    crud.finalize_interview_session(session, interview.id)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<p style="font-size:0.68rem;font-weight:700;letter-spacing:0.15em;'
                'text-transform:uppercase;color:#6366f1;margin-bottom:1rem;">📊 Final Report</p>',
                unsafe_allow_html=True,
            )

            sc1, sc2, sc3 = st.columns(3)
            for col, score, label in [
                (sc1, evaluation.technical_score,     "Technical"),
                (sc2, evaluation.communication_score, "Communication"),
                (sc3, evaluation.role_fit_score,      "Role Fit"),
            ]:
                with col:
                    st.markdown(
                        f'<div class="score-card">'
                        f'<div class="score-num">{score}'
                        f'<span style="font-size:1rem;color:#64748b">/10</span></div>'
                        f'<div class="score-lbl">{label}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            ev1, ev2 = st.columns(2)
            with ev1:
                if evaluation.strengths:
                    items = "".join(
                        f'<div class="eval-list-item">✅ {s}</div>' for s in evaluation.strengths
                    )
                    st.markdown(
                        f'<div class="eval-section"><h4>💪 Strengths</h4>{items}</div>',
                        unsafe_allow_html=True,
                    )
            with ev2:
                if evaluation.weaknesses:
                    items = "".join(
                        f'<div class="eval-list-item">⚠ {w}</div>' for w in evaluation.weaknesses
                    )
                    st.markdown(
                        f'<div class="eval-section"><h4>🔧 Areas to Improve</h4>{items}</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown(
                f'<div class="eval-section">'
                f'<h4>📝 Recommendation</h4>'
                f'<div style="color:#e2e8f0;font-size:0.92rem;font-weight:500;margin-bottom:0.8rem;">'
                f'{evaluation.recommendation}</div>'
                f'<div style="color:#94a3b8;font-size:0.87rem;line-height:1.7;">'
                f'{evaluation.detailed_feedback}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
