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
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

# ── guard: must arrive from the analysis page ─────────────────────────────────
pipeline_result = st.session_state.get("pipeline_result")
if pipeline_result is None:
    st.error("No session found. Please go back and analyse your resume first.")
    if st.button("← Back to Resume Analysis"):
        st.switch_page("app.py")
    st.stop()

company = st.session_state.get("target_company", "")
role    = st.session_state.get("target_role", "")

# ═══════════════════════════════════════════════════════════════════════════════
# STYLES
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

    *, *::before, *::after { box-sizing: border-box; }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background: #07070f;
        background-image: radial-gradient(ellipse 80% 40% at 50% 0%, rgba(99,102,241,0.09) 0%, transparent 60%);
    }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 0 !important; max-width: 1400px; }

    /* ═══════════════════════════════════════
       SIDEBAR — GLASSMORPHISM PANEL
    ═══════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background: rgba(12,12,22,0.92) !important;
        border-right: 1px solid rgba(45,45,74,0.5) !important;
        backdrop-filter: blur(16px) !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        padding: 1.4rem 1.2rem !important;
    }
    .sb-section {
        margin-bottom: 1.6rem;
    }
    .sb-eyebrow {
        font-size: 0.62rem;
        font-weight: 800;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #4b5563;
        margin-bottom: 0.7rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .sb-eyebrow::after {
        content: '';
        flex: 1;
        height: 1px;
        background: rgba(45,45,74,0.6);
    }
    .sb-brand {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1.4rem;
        padding-bottom: 1.2rem;
        border-bottom: 1px solid rgba(45,45,74,0.5);
    }
    .sb-brand-mark {
        width: 30px; height: 30px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.95rem;
        box-shadow: 0 0 14px rgba(99,102,241,0.4);
        flex-shrink: 0;
    }
    .sb-brand-name {
        font-size: 1rem;
        font-weight: 900;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #e0e7ff, #a5b4fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sb-session-info {
        background: rgba(99,102,241,0.07);
        border: 1px solid rgba(99,102,241,0.12);
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
        margin-bottom: 0.5rem;
    }
    .sb-session-role {
        font-size: 0.72rem;
        color: #a5b4fc;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: 0.2rem;
    }
    .sb-session-company {
        font-size: 0.9rem;
        color: #e2e8f0;
        font-weight: 800;
        letter-spacing: -0.01em;
    }
    .sb-stat-row {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1.2rem;
    }
    .sb-stat {
        flex: 1;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(45,45,74,0.4);
        border-radius: 10px;
        padding: 0.65rem 0.7rem;
        text-align: center;
    }
    .sb-stat-val {
        font-size: 1.1rem;
        font-weight: 800;
        color: #e2e8f0;
        letter-spacing: -0.02em;
    }
    .sb-stat-lbl {
        font-size: 0.62rem;
        color: #4b5563;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-top: 0.15rem;
    }
    .sb-skill-chip {
        display: inline-block;
        background: rgba(99,102,241,0.09);
        color: #a5b4fc;
        border: 1px solid rgba(99,102,241,0.16);
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 0.18rem 0.55rem;
        margin: 0.14rem;
    }
    .sb-lang-chip {
        display: inline-block;
        background: rgba(139,92,246,0.12);
        color: #c4b5fd;
        border: 1px solid rgba(139,92,246,0.22);
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 0.18rem 0.55rem;
        margin: 0.14rem;
    }
    .sb-intel-item {
        display: inline-block;
        background: rgba(16,185,129,0.08);
        color: #6ee7b7;
        border: 1px solid rgba(16,185,129,0.16);
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 0.18rem 0.55rem;
        margin: 0.14rem;
    }
    .sb-tip {
        font-size: 0.78rem;
        color: #64748b;
        line-height: 1.65;
        border-left: 2px solid rgba(99,102,241,0.35);
        padding-left: 0.8rem;
        margin-top: 0.4rem;
    }

    /* ═══════════════════════════════════════
       TOPBAR
    ═══════════════════════════════════════ */
    .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.2rem 0 1.4rem;
        border-bottom: 1px solid rgba(30,30,50,0.9);
        margin-bottom: 1.6rem;
    }
    .topbar-left {
        display: flex;
        align-items: center;
        gap: 0.7rem;
    }
    .topbar-mark {
        width: 32px; height: 32px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 9px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem;
        box-shadow: 0 0 16px rgba(99,102,241,0.4);
        flex-shrink: 0;
    }
    .topbar-brand {
        font-size: 1.05rem;
        font-weight: 900;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #e0e7ff, #a5b4fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .topbar-meta {
        color: #4b5563;
        font-size: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .meta-chip {
        background: rgba(99,102,241,0.1);
        color: #a5b4fc;
        border: 1px solid rgba(99,102,241,0.18);
        border-radius: 6px;
        padding: 0.2rem 0.6rem;
        font-weight: 600;
        font-size: 0.78rem;
    }

    /* ═══════════════════════════════════════
       PROGRESS TRACKER
    ═══════════════════════════════════════ */
    .progress-tracker {
        display: flex;
        align-items: center;
        gap: 0;
        margin-bottom: 1.6rem;
        padding: 0.9rem 1.2rem;
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(45,45,74,0.4);
        border-radius: 14px;
        overflow-x: auto;
    }
    .pt-step {
        display: flex;
        align-items: center;
        gap: 0;
        flex-shrink: 0;
    }
    .pt-node {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        flex-shrink: 0;
    }
    .pt-circle {
        width: 28px; height: 28px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.7rem;
        font-weight: 800;
        flex-shrink: 0;
        transition: all 0.3s ease;
    }
    .pt-circle.done {
        background: rgba(16,185,129,0.2);
        border: 2px solid rgba(16,185,129,0.4);
        color: #6ee7b7;
    }
    .pt-circle.active {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border: 2px solid rgba(99,102,241,0.6);
        color: #fff;
        box-shadow: 0 0 12px rgba(99,102,241,0.5);
    }
    .pt-circle.pending {
        background: rgba(255,255,255,0.04);
        border: 2px solid rgba(45,45,74,0.6);
        color: #4b5563;
    }
    .pt-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.01em;
    }
    .pt-label.done   { color: #34d399; }
    .pt-label.active { color: #e2e8f0; }
    .pt-label.pending{ color: #4b5563; }
    .pt-connector {
        height: 2px;
        width: 2rem;
        margin: 0 0.4rem;
        flex-shrink: 0;
        border-radius: 2px;
    }
    .pt-connector.done    { background: rgba(16,185,129,0.35); }
    .pt-connector.pending { background: rgba(45,45,74,0.5); }

    /* ═══════════════════════════════════════
       QUESTION CARD
    ═══════════════════════════════════════ */
    .q-card {
        background: linear-gradient(160deg, rgba(28,28,44,0.95) 0%, rgba(20,20,38,0.95) 100%);
        border: 1px solid rgba(45,45,74,0.55);
        border-radius: 18px;
        padding: 1.8rem 2rem 1.5rem;
        margin-bottom: 1.2rem;
    }
    .q-eyebrow {
        font-size: 0.64rem;
        font-weight: 800;
        letter-spacing: 0.17em;
        text-transform: uppercase;
        color: #6366f1;
        margin-bottom: 0.7rem;
    }
    .q-header {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }
    .q-title {
        color: #e2e8f0;
        font-size: 1.3rem;
        font-weight: 800;
        letter-spacing: -0.02em;
    }
    .diff-badge {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 700;
        padding: 0.2rem 0.65rem;
        border-radius: 7px;
        letter-spacing: 0.04em;
    }
    .diff-easy   { background: rgba(16,185,129,0.14); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.25); }
    .diff-medium { background: rgba(251,191,36,0.12);  color: #fbbf24; border: 1px solid rgba(251,191,36,0.25); }
    .diff-hard   { background: rgba(239,68,68,0.12);   color: #fca5a5; border: 1px solid rgba(239,68,68,0.22); }
    .tag-chip {
        display: inline-block;
        background: rgba(99,102,241,0.09);
        color: #818cf8;
        border: 1px solid rgba(99,102,241,0.18);
        border-radius: 5px;
        font-size: 0.67rem;
        font-weight: 600;
        padding: 0.14rem 0.5rem;
        margin: 0 0.18rem 0.18rem 0;
    }
    .lc-link {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        color: #f97316;
        font-size: 0.75rem;
        font-weight: 700;
        text-decoration: none;
        background: rgba(249,115,22,0.09);
        border: 1px solid rgba(249,115,22,0.22);
        border-radius: 7px;
        padding: 0.2rem 0.6rem;
        transition: background 0.15s;
    }
    .lc-link:hover { background: rgba(249,115,22,0.18); }
    .lc-content {
        color: #cbd5e1;
        font-size: 0.89rem;
        line-height: 1.8;
        margin-top: 1rem;
    }
    .lc-content p { margin: 0.5rem 0; }
    .lc-content strong { color: #e2e8f0; font-weight: 600; }
    .lc-content em  { color: #a5b4fc; }
    .lc-content pre {
        background: rgba(0,0,0,0.4);
        border: 1px solid rgba(45,45,74,0.6);
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: #a5b4fc;
        overflow-x: auto;
        margin: 0.8rem 0;
    }
    .lc-content code {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: #a5b4fc;
        background: rgba(99,102,241,0.09);
        padding: 0.1rem 0.35rem;
        border-radius: 4px;
    }
    .lc-content ul, .lc-content ol { padding-left: 1.4rem; margin: 0.5rem 0; }
    .lc-content li { margin: 0.3rem 0; }
    .q-hint {
        color: #4b5563;
        font-size: 0.79rem;
        margin-top: 1.1rem;
        padding-top: 0.9rem;
        border-top: 1px solid rgba(30,30,50,0.9);
        font-style: italic;
        line-height: 1.6;
    }

    /* ═══════════════════════════════════════
       CHAT PANEL
    ═══════════════════════════════════════ */
    .chat-panel-label {
        font-size: 0.64rem;
        font-weight: 800;
        letter-spacing: 0.17em;
        text-transform: uppercase;
        color: #6366f1;
        margin-bottom: 1rem;
    }
    .msg-user {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 1rem;
    }
    .msg-user-bubble {
        background: linear-gradient(135deg, #6366f1, #7c3aed);
        color: #fff;
        border-radius: 18px 18px 4px 18px;
        padding: 0.8rem 1.15rem;
        max-width: 78%;
        font-size: 0.88rem;
        line-height: 1.6;
        box-shadow: 0 4px 20px rgba(99,102,241,0.28);
        font-weight: 500;
    }
    .msg-agent {
        display: flex;
        justify-content: flex-start;
        margin-bottom: 1rem;
        align-items: flex-start;
        gap: 0.6rem;
    }
    .msg-agent.anim-in {
        animation: slideInMsg 0.35s cubic-bezier(0.16,1,0.3,1) both;
    }
    @keyframes slideInMsg {
        from { opacity: 0; transform: translateY(10px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .msg-agent-avatar {
        width: 28px; height: 28px;
        border-radius: 50%;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        display: flex; align-items: center; justify-content: center;
        font-size: 0.78rem;
        flex-shrink: 0;
        margin-top: 4px;
        box-shadow: 0 0 10px rgba(99,102,241,0.35);
    }
    .msg-agent-content { max-width: 80%; }
    .msg-type-badge {
        font-size: 0.6rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        padding: 0.12rem 0.48rem;
        border-radius: 5px;
        margin-bottom: 0.3rem;
        display: inline-block;
    }
    .badge-hint     { background: rgba(251,191,36,0.14); color: #fbbf24; border: 1px solid rgba(251,191,36,0.22); }
    .badge-followup { background: rgba(99,102,241,0.13); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.22); }
    .badge-guide    { background: rgba(239,68,68,0.11);  color: #fca5a5; border: 1px solid rgba(239,68,68,0.2); }
    .badge-accept   { background: rgba(16,185,129,0.11); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.2); }
    .msg-agent-bubble {
        background: rgba(28,28,44,0.95);
        border: 1px solid rgba(45,45,74,0.5);
        color: #cbd5e1;
        border-radius: 4px 18px 18px 18px;
        padding: 0.8rem 1.15rem;
        font-size: 0.88rem;
        line-height: 1.7;
    }
    /* Typewriter cursor on newest agent message */
    .msg-agent.anim-in .msg-agent-bubble::after {
        content: '▋';
        color: #6366f1;
        font-size: 0.78rem;
        margin-left: 2px;
        animation: cursorFade 1.2s ease-out forwards;
    }
    @keyframes cursorFade {
        0%, 60% { opacity: 1; }
        100%     { opacity: 0; }
    }

    /* ═══════════════════════════════════════
       BUTTONS
    ═══════════════════════════════════════ */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%) !important;
        color: #fff !important;
        font-weight: 700 !important;
        font-family: 'Inter', sans-serif !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.72rem 1.6rem !important;
        font-size: 0.9rem !important;
        box-shadow: 0 4px 22px rgba(99,102,241,0.4) !important;
        transition: all 0.2s cubic-bezier(0.16,1,0.3,1) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 30px rgba(99,102,241,0.6) !important;
    }
    .stButton > button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid rgba(45,45,74,0.7) !important;
        color: #64748b !important;
        border-radius: 12px !important;
        font-size: 0.84rem !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: rgba(99,102,241,0.4) !important;
        color: #a5b4fc !important;
    }

    /* ── chat input ── */
    .stChatInput textarea {
        background: rgba(20,20,38,0.9) !important;
        border: 1px solid rgba(45,45,74,0.7) !important;
        border-radius: 14px !important;
        color: #e2e8f0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
    }
    .stChatInput textarea:focus {
        border-color: rgba(99,102,241,0.5) !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important;
    }

    /* ═══════════════════════════════════════
       EVALUATION
    ═══════════════════════════════════════ */
    .score-card {
        background: linear-gradient(160deg, rgba(28,28,44,0.95) 0%, rgba(20,20,38,0.95) 100%);
        border: 1px solid rgba(45,45,74,0.5);
        border-radius: 16px;
        padding: 1.6rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .score-num {
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1;
        letter-spacing: -0.04em;
    }
    .score-lbl {
        color: #4b5563;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-top: 0.4rem;
    }
    .eval-section {
        background: rgba(20,20,38,0.8);
        border: 1px solid rgba(45,45,74,0.45);
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
    }
    .eval-section h4 {
        color: #4b5563;
        font-size: 0.66rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        margin: 0 0 0.8rem;
    }
    .eval-list-item {
        color: #cbd5e1;
        font-size: 0.87rem;
        padding: 0.35rem 0;
        border-bottom: 1px solid rgba(30,30,50,0.9);
        line-height: 1.55;
    }
    .eval-list-item:last-child { border-bottom: none; }
    .divider { border: none; border-top: 1px solid rgba(30,30,50,0.9); margin: 1.4rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GLASSMORPHISM SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    profile = pipeline_result.resume_profile
    intel   = pipeline_result.company_intel

    st.markdown(
        f"""
        <div class="sb-brand">
            <div class="sb-brand-mark">⚡</div>
            <span class="sb-brand-name">Internly</span>
        </div>
        <div class="sb-session-info">
            <div class="sb-session-role">{role}</div>
            <div class="sb-session-company">{company}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Experience + skills summary
    years  = int(profile.years_experience)
    months = int(round((profile.years_experience - years) * 12))
    if months == 12:
        years += 1; months = 0
    exp_parts = []
    if years  > 0: exp_parts.append(f"{years}yr")
    if months > 0 or not exp_parts: exp_parts.append(f"{months}mo")
    exp_text = " ".join(exp_parts)

    n_skills   = len(profile.skills or [])
    n_projects = len(profile.projects or [])

    st.markdown(
        f"""
        <div class="sb-stat-row">
            <div class="sb-stat">
                <div class="sb-stat-val">{exp_text}</div>
                <div class="sb-stat-lbl">Experience</div>
            </div>
            <div class="sb-stat">
                <div class="sb-stat-val">{n_skills}</div>
                <div class="sb-stat-lbl">Skills</div>
            </div>
            <div class="sb-stat">
                <div class="sb-stat-val">{n_projects}</div>
                <div class="sb-stat-lbl">Projects</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Skills chips
    if profile.skills:
        st.markdown('<div class="sb-section"><div class="sb-eyebrow">🛠 Skills</div>', unsafe_allow_html=True)
        chips = "".join(f'<span class="sb-skill-chip">{s}</span>' for s in profile.skills[:12])
        st.markdown(f"<div>{chips}</div></div>", unsafe_allow_html=True)

    # Target languages
    if getattr(profile, "target_languages", None):
        st.markdown('<div class="sb-section"><div class="sb-eyebrow">💻 Languages</div>', unsafe_allow_html=True)
        langs = "".join(f'<span class="sb-lang-chip">{l}</span>' for l in profile.target_languages)
        st.markdown(f"<div>{langs}</div></div>", unsafe_allow_html=True)

    # Company intel quick tips
    if intel:
        if intel.interview_rounds:
            st.markdown('<div class="sb-section"><div class="sb-eyebrow">📋 Interview Format</div>', unsafe_allow_html=True)
            rounds = "".join(f'<span class="sb-intel-item">{r}</span>' for r in intel.interview_rounds)
            st.markdown(f"<div>{rounds}</div></div>", unsafe_allow_html=True)

        if intel.difficulty_notes:
            st.markdown(
                f'<div class="sb-section"><div class="sb-eyebrow">📊 Difficulty</div>'
                f'<div class="sb-tip">{intel.difficulty_notes[:220]}{"…" if len(intel.difficulty_notes) > 220 else ""}</div></div>',
                unsafe_allow_html=True,
            )

    # Back button
    if st.button("← Back to Analysis", key="back_btn"):
        st.switch_page("app.py")


# ═══════════════════════════════════════════════════════════════════════════════
# TOPBAR
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"""
    <div class="topbar">
        <div class="topbar-left">
            <div class="topbar-mark">⚡</div>
            <span class="topbar-brand">Internly</span>
        </div>
        <div class="topbar-meta">
            Interviewing for
            <span class="meta-chip">{role}</span>
            at
            <span class="meta-chip">{company}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════════
for key, default in {
    "interview_session_id": None,
    "used_question_ids": set(),
    "active_question_index": None,
    "active_question_text": None,
    "active_question_link": None,
    "active_question_difficulty": None,
    "active_question_tags": [],
    "lc_content_html": None,
    "chat_history": [],
    "questions_completed": 0,
    "animate_last_msg": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ═══════════════════════════════════════════════════════════════════════════════
# INIT INTERVIEW SESSION
# ═══════════════════════════════════════════════════════════════════════════════
if not st.session_state.interview_session_id:
    with get_session() as session:
        interview = start_interview_session(session, pipeline_result.candidate_id, include_greeting=True)
        st.session_state.interview_session_id = interview.id
        st.session_state.used_question_ids    = set()
        st.session_state.active_question_index = 0
        st.session_state.active_question_text  = "Introduction"
        st.session_state.active_question_link  = None
        st.session_state.lc_content_html       = ""
        st.session_state.questions_completed   = 0
        turns = interview.transcript_json[0]["turns"]
        st.session_state.chat_history = [
            {"role": t["role"], "text": t["text"], "type": t.get("type", "followup")}
            for t in turns
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# FETCH NEXT QUESTION
# ═══════════════════════════════════════════════════════════════════════════════
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
        st.session_state.active_question_tags       = []
        st.session_state.lc_content_html            = None
        st.session_state.chat_history.append({
            "role": "agent",
            "text": f"Here is our next technical question: **{asked.display_text}**. Please review the problem description on the left, then outline your approach.",
            "type": "followup",
        })
        st.session_state.animate_last_msg = True
    else:
        st.session_state.active_question_text = None


# ═══════════════════════════════════════════════════════════════════════════════
# FETCH LEETCODE CONTENT
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.active_question_link and st.session_state.lc_content_html is None:
    with st.spinner("📡 Fetching full question from LeetCode…"):
        lc = fetch_question(st.session_state.active_question_link)
    if lc:
        st.session_state.lc_content_html     = lc["content_html"]
        st.session_state.active_question_tags = lc["topic_tags"]
        if lc["difficulty"]:
            st.session_state.active_question_difficulty = lc["difficulty"]
    else:
        st.session_state.lc_content_html = ""


# ═══════════════════════════════════════════════════════════════════════════════
# PROGRESS TRACKER
# ═══════════════════════════════════════════════════════════════════════════════
def _render_progress_tracker():
    completed = st.session_state.questions_completed
    is_intro  = st.session_state.active_question_text == "Introduction"
    is_done   = st.session_state.active_question_text is None

    steps = []
    # Introduction step
    if is_intro:
        steps.append(("Intro", "active"))
    else:
        steps.append(("Intro", "done"))

    # DSA questions — completed ones
    for i in range(1, completed + 1):
        steps.append((f"Q{i}", "done"))

    # Current DSA question (if not intro and not done)
    if not is_intro and not is_done:
        steps.append((f"Q{completed + 1}", "active"))

    # Placeholder "next" step
    if not is_done:
        steps.append(("…", "pending"))
    else:
        steps.append(("Done", "active"))

    html = '<div class="progress-tracker">'
    for idx, (label, state) in enumerate(steps):
        icon = "✓" if state == "done" else ("●" if state == "active" else "○")
        html += (
            f'<div class="pt-step">'
            f'<div class="pt-node">'
            f'<div class="pt-circle {state}">{icon}</div>'
            f'<span class="pt-label {state}">{label}</span>'
            f'</div>'
        )
        if idx < len(steps) - 1:
            conn_cls = "done" if state == "done" else "pending"
            html += f'<div class="pt-connector {conn_cls}"></div>'
        html += "</div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


_render_progress_tracker()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN LAYOUT — question panel (left) + chat panel (right)
# ═══════════════════════════════════════════════════════════════════════════════
q_col, chat_col = st.columns([5, 4], gap="large")


# ── LEFT: question display ────────────────────────────────────────────────────
with q_col:
    active_q = st.session_state.active_question_text
    link     = st.session_state.active_question_link
    diff     = (st.session_state.active_question_difficulty or "").strip()
    tags     = st.session_state.active_question_tags or []

    if active_q:
        if active_q == "Introduction":
            body_section = (
                '<div class="lc-content">'
                f'<p>Welcome to your interview at <strong>{company}</strong> for the <strong>{role}</strong> position!</p>'
                '<p>Before the technical challenge, please take a moment to introduce yourself in the chat on the right.</p>'
                '<p><strong>Suggested topics to cover:</strong></p>'
                '<ul>'
                '<li>Your professional background and technical stack</li>'
                '<li>Key projects you have built recently</li>'
                '<li>Your interest in this target role</li>'
                '</ul>'
                '</div>'
            )
            st.markdown(
                f"""
                <div class="q-card">
                    <div class="q-eyebrow">👋 Welcome to Internly</div>
                    <div class="q-header">
                        <div class="q-title">Candidate Introduction</div>
                    </div>
                    {body_section}
                    <div class="q-hint">
                        💬 Respond to the interviewer's greeting in the chat panel on the right.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            diff_cls  = {"easy": "diff-easy", "medium": "diff-medium", "hard": "diff-hard"}.get(diff.lower(), "diff-medium")
            diff_badge  = f'<span class="diff-badge {diff_cls}">{diff}</span>' if diff else ""
            lc_link_html = (
                f'<a class="lc-link" href="{link}" target="_blank">🔗 LeetCode</a>'
                if link else ""
            )
            tags_html = "".join(f'<span class="tag-chip">{t}</span>' for t in tags)
            content_html = st.session_state.lc_content_html or ""
            if content_html:
                body_section = f'<div class="lc-content">{content_html}</div>'
            else:
                body_section = (
                    '<div class="lc-content" style="color:#4b5563;font-style:italic;">'
                    'Full problem statement could not be loaded. '
                    'Open the LeetCode link above, read the problem, then describe your approach here.'
                    '</div>'
                )

            st.markdown(
                f"""
                <div class="q-card">
                    <div class="q-eyebrow">🧩 DSA Challenge</div>
                    <div class="q-header">
                        <div class="q-title">{active_q}</div>
                        {diff_badge}
                        {lc_link_html}
                    </div>
                    {('<div style="margin-bottom:0.8rem">' + tags_html + '</div>') if tags_html else ''}
                    {body_section}
                    <div class="q-hint">
                        💬 Explain your approach, data structures, and time/space complexity.
                        Type <em>"move on"</em> or <em>"skip"</em> to advance to the next question.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            """
            <div class="q-card" style="text-align:center;color:#4b5563;padding:3rem 2rem;">
                <div style="font-size:2.2rem;margin-bottom:0.7rem;">🏁</div>
                <div style="font-size:1rem;font-weight:700;color:#6366f1;margin-bottom:0.4rem;">All questions completed!</div>
                <div style="font-size:0.85rem;">Generate your final evaluation in the panel on the right.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── RIGHT: chat panel ─────────────────────────────────────────────────────────
with chat_col:
    st.markdown(
        '<p class="chat-panel-label">💬 Interview Chat</p>',
        unsafe_allow_html=True,
    )

    # Build chat HTML — animate only the last agent message
    history     = st.session_state.chat_history
    animate_last = st.session_state.get("animate_last_msg", False)

    # Find index of last agent message
    last_agent_idx = None
    for i in range(len(history) - 1, -1, -1):
        if history[i]["role"] == "agent":
            last_agent_idx = i
            break

    badge_map = {
        "hint":     "badge-hint",
        "followup": "badge-followup",
        "guide":    "badge-guide",
        "accept":   "badge-accept",
    }

    chat_html = ""
    for i, turn in enumerate(history):
        if turn["role"] == "user":
            chat_html += (
                f'<div class="msg-user">'
                f'<div class="msg-user-bubble">{turn["text"]}</div>'
                f'</div>'
            )
        else:
            badge_cls  = badge_map.get(turn.get("type", ""), "badge-followup")
            type_label = (turn.get("type") or "agent").upper()
            anim_class = "anim-in" if (animate_last and i == last_agent_idx) else ""
            chat_html += (
                f'<div class="msg-agent {anim_class}">'
                f'<div class="msg-agent-avatar">🤖</div>'
                f'<div class="msg-agent-content">'
                f'<span class="msg-type-badge {badge_cls}">{type_label}</span>'
                f'<div class="msg-agent-bubble">{turn["text"]}</div>'
                f'</div></div>'
            )

    chat_container = st.container(height=600)
    with chat_container:
        if chat_html:
            st.markdown(chat_html, unsafe_allow_html=True)

    # Clear animation flag after rendering
    st.session_state.animate_last_msg = False

    # ── Chat input ────────────────────────────────────────────────────────────
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
            st.session_state.animate_last_msg = True

            # ── Toast notifications ──────────────────────────────────────────
            if action.type == "accept":
                st.toast("✅ Question accepted! Moving to next…", icon="🎉")
                st.session_state.questions_completed += 1
                st.session_state.active_question_index      = None
                st.session_state.active_question_text       = None
                st.session_state.active_question_link       = None
                st.session_state.lc_content_html            = None
                st.session_state.active_question_tags       = []
            elif action.type == "guide":
                st.toast("📖 Walking you through the optimal solution…", icon="💡")

            st.rerun()

    # ── Final evaluation ──────────────────────────────────────────────────────
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    if st.session_state.interview_session_id:
        if st.button("📊 Generate Final Evaluation", type="primary", key="gen_eval_btn"):
            with st.spinner("🧠 Evaluating your performance…"):
                with get_session() as session:
                    interview  = session.get(InterviewSession, st.session_state.interview_session_id)
                    candidate  = session.get(Candidate, pipeline_result.candidate_id)
                    if not interview or not candidate:
                        st.error("Interview records were not found.")
                        st.stop()

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

            st.toast("📊 Evaluation complete!", icon="✨")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<p class="chat-panel-label">📊 Final Report</p>',
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
                        f'<span style="font-size:1rem;color:#4b5563;">/10</span></div>'
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
                f'<div style="color:#e2e8f0;font-size:0.92rem;font-weight:700;margin-bottom:0.8rem;letter-spacing:-0.01em;">'
                f'{evaluation.recommendation}</div>'
                f'<div style="color:#94a3b8;font-size:0.86rem;line-height:1.8;">'
                f'{evaluation.detailed_feedback}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
