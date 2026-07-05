from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from internly.db.database import get_session, init_db
from internly.pipeline import run_pipeline_start

st.set_page_config(
    page_title="Internly – AI Interview Prep",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()

# ── session state defaults ────────────────────────────────────────────────────
for key, default in {
    "pipeline_result": None,
    "target_company": "",
    "target_role": "",
    "interview_session_id": None,
    "used_question_ids": set(),
    "active_question_index": None,
    "active_question_text": None,
    "chat_history": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── global styles ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

    *, *::before, *::after { box-sizing: border-box; }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background: #07070f;
        background-image:
            radial-gradient(ellipse 90% 55% at 50% -10%, rgba(99,102,241,0.12) 0%, transparent 65%);
        min-height: 100vh;
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 1rem !important;
        max-width: 1180px;
    }

    /* ═══════════════════════════════════════
       LOGO / TOPNAV
    ═══════════════════════════════════════ */
    .topnav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.9rem 0 0.45rem;
        border-bottom: 1px solid rgba(45,45,74,0.4);
        margin-bottom: 0;
    }
    .brand {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        text-decoration: none;
    }
    .brand-mark {
        width: 32px; height: 32px;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.1rem;
        box-shadow: 0 0 0 1px rgba(99,102,241,0.3), 0 0 20px rgba(99,102,241,0.35);
        animation: logoGlow 3s ease-in-out infinite;
        flex-shrink: 0;
    }
    @keyframes logoGlow {
        0%, 100% { box-shadow: 0 0 0 1px rgba(99,102,241,0.3), 0 0 20px rgba(99,102,241,0.35); }
        50%       { box-shadow: 0 0 0 1px rgba(99,102,241,0.5), 0 0 36px rgba(139,92,246,0.55); }
    }
    .brand-text {
        font-size: 1.05rem;
        font-weight: 900;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #e0e7ff 0%, #a5b4fc 70%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .nav-tag {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #4b5563;
    }

    /* ═══════════════════════════════════════
       HERO
    ═══════════════════════════════════════ */
    .hero {
        text-align: center;
        padding: 1.35rem 1rem 1.05rem;
    }
    .hero-eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        background: rgba(99,102,241,0.1);
        border: 1px solid rgba(99,102,241,0.25);
        color: #a5b4fc;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.13em;
        text-transform: uppercase;
        padding: 0.38rem 1rem;
        border-radius: 999px;
        margin-bottom: 0.75rem;
    }
    .hero-eyebrow-dot {
        width: 6px; height: 6px;
        background: #6366f1;
        border-radius: 50%;
        animation: pulse-dot 1.8s ease-in-out infinite;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.7); }
    }
    .hero h1 {
        font-size: clamp(2.15rem, 4.6vw, 3.45rem);
        font-weight: 900;
        line-height: 1.02;
        letter-spacing: -0.04em;
        margin: 0 0 0.75rem;
        background: linear-gradient(160deg, #ffffff 0%, #e0e7ff 45%, #a5b4fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-sub {
        font-size: 0.92rem;
        color: #64748b;
        max-width: 660px;
        margin: 0 auto 1.1rem;
        line-height: 1.55;
        font-weight: 400;
    }
    .hero-pills {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-bottom: 0;
    }
    .hero-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: rgba(255,255,255,0.035);
        border: 1px solid rgba(255,255,255,0.07);
        color: #94a3b8;
        font-size: 0.72rem;
        font-weight: 500;
        padding: 0.3rem 0.75rem;
        border-radius: 999px;
    }

    /* ═══════════════════════════════════════
       UPLOAD / SETUP CARD
    ═══════════════════════════════════════ */
    [data-testid="stForm"] {
        background: linear-gradient(160deg, rgba(30,30,46,0.95) 0%, rgba(20,20,38,0.95) 100%);
        border: 1px solid rgba(99,102,241,0.14) !important;
        border-radius: 18px !important;
        padding: 1rem 1.15rem 1.1rem !important;
        max-width: 720px;
        margin: 0 auto;
        box-shadow:
            0 0 0 1px rgba(0,0,0,0.3),
            0 18px 48px rgba(0,0,0,0.38),
            0 0 60px rgba(99,102,241,0.06);
        backdrop-filter: blur(12px);
    }
    .setup-card-header {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        margin-bottom: 0.2rem;
    }
    .setup-card-icon {
        width: 32px; height: 32px;
        background: rgba(99,102,241,0.15);
        border: 1px solid rgba(99,102,241,0.25);
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem;
    }
    .setup-card-title {
        font-size: 1rem;
        font-weight: 800;
        color: #e2e8f0;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .setup-card-sub {
        font-size: 0.82rem;
        color: #475569;
        margin: 0 0 0.8rem;
        padding-left: 2.45rem;
    }
    .field-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
        margin-bottom: 0.1rem;
    }

    /* ── Form inputs ── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(10,10,20,0.8) !important;
        border: 1px solid rgba(45,45,74,0.7) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.84rem !important;
        padding: 0.52rem 0.8rem !important;
        transition: border-color 0.2s, box-shadow 0.2s !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: rgba(99,102,241,0.55) !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important;
    }
    .stTextInput label, .stTextArea label, .stFileUploader label {
        color: #4b5563 !important;
        font-size: 0.74rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.09em !important;
    }
    .stFileUploader > div {
        background: rgba(10,10,20,0.8) !important;
        border: 1.5px dashed rgba(45,45,74,0.8) !important;
        border-radius: 14px !important;
        transition: border-color 0.2s !important;
    }
    .stFileUploader > div:hover {
        border-color: rgba(99,102,241,0.4) !important;
    }

    /* ── Primary button ── */
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%) !important;
        color: #fff !important;
        font-weight: 700 !important;
        font-family: 'Inter', sans-serif !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 0.62rem 1.4rem !important;
        font-size: 0.86rem !important;
        width: 100% !important;
        letter-spacing: 0.01em !important;
        transition: all 0.2s cubic-bezier(0.16,1,0.3,1) !important;
        box-shadow: 0 4px 28px rgba(99,102,241,0.45) !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 36px rgba(99,102,241,0.65) !important;
    }
    .stButton > button[kind="primary"]:active,
    .stFormSubmitButton > button:active {
        transform: translateY(0) !important;
    }

    /* ── st.status override ── */
    [data-testid="stStatusWidget"] {
        border-radius: 16px !important;
        border-color: rgba(99,102,241,0.2) !important;
    }

    /* ═══════════════════════════════════════
       RESULTS — SECTION HEADERS
    ═══════════════════════════════════════ */
    .results-divider {
        border: none;
        border-top: 1px solid rgba(30,30,50,0.9);
        margin: 2.8rem 0;
    }
    .sec-eyebrow {
        font-size: 0.66rem;
        font-weight: 800;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #6366f1;
        margin-bottom: 0.3rem;
    }
    .sec-title {
        font-size: 1.45rem;
        font-weight: 900;
        color: #e2e8f0;
        letter-spacing: -0.025em;
        margin: 0 0 0.3rem;
    }
    .sec-sub {
        font-size: 0.84rem;
        color: #475569;
        margin: 0 0 1.8rem;
        font-weight: 400;
    }

    /* ═══════════════════════════════════════
       PROFILE CARDS
    ═══════════════════════════════════════ */
    .profile-card {
        background: linear-gradient(160deg, rgba(28,28,44,0.9) 0%, rgba(20,20,38,0.9) 100%);
        border: 1px solid rgba(45,45,74,0.5);
        border-radius: 18px;
        padding: 1.6rem;
        margin-bottom: 1rem;
        transition: border-color 0.25s ease, box-shadow 0.25s ease;
    }
    .profile-card:hover {
        border-color: rgba(99,102,241,0.22);
        box-shadow: 0 8px 30px rgba(0,0,0,0.25);
    }
    .card-eyebrow {
        font-size: 0.66rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #4b5563;
        margin: 0 0 1rem;
    }
    .stat-value {
        font-size: 2.4rem;
        font-weight: 900;
        color: #e2e8f0;
        line-height: 1;
        letter-spacing: -0.04em;
    }
    .stat-label {
        color: #4b5563;
        font-size: 0.78rem;
        margin-top: 0.3rem;
        font-weight: 500;
    }
    .edu-entry {
        color: #cbd5e1;
        font-size: 0.88rem;
        line-height: 1.5;
        padding: 0.55rem 0;
        border-bottom: 1px solid rgba(45,45,74,0.4);
    }
    .edu-entry:last-child { border-bottom: none; }

    .skill-chip {
        display: inline-block;
        background: rgba(99,102,241,0.1);
        color: #a5b4fc;
        border: 1px solid rgba(99,102,241,0.18);
        border-radius: 7px;
        font-size: 0.74rem;
        font-weight: 600;
        padding: 0.22rem 0.65rem;
        margin: 0.18rem;
        letter-spacing: 0.01em;
        transition: background 0.15s;
    }
    .skill-chip:hover { background: rgba(99,102,241,0.18); }
    .lang-chip {
        display: inline-block;
        background: rgba(139,92,246,0.14);
        color: #c4b5fd;
        border: 1px solid rgba(139,92,246,0.28);
        border-radius: 7px;
        font-size: 0.74rem;
        font-weight: 600;
        padding: 0.22rem 0.65rem;
        margin: 0.18rem;
        letter-spacing: 0.01em;
    }
    .project-item {
        display: flex;
        align-items: flex-start;
        gap: 0.7rem;
        padding: 0.6rem 0;
        border-bottom: 1px solid rgba(45,45,74,0.35);
        color: #cbd5e1;
        font-size: 0.86rem;
        line-height: 1.5;
    }
    .project-item:last-child { border-bottom: none; }
    .project-dot {
        width: 6px; height: 6px;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 50%;
        flex-shrink: 0;
        margin-top: 0.45rem;
    }
    .gap-item {
        background: rgba(239,68,68,0.07);
        border: 1px solid rgba(239,68,68,0.14);
        border-radius: 10px;
        padding: 0.5rem 0.85rem;
        color: #fca5a5;
        font-size: 0.84rem;
        margin-bottom: 0.4rem;
        font-weight: 500;
    }

    /* ═══════════════════════════════════════
       JD ALIGNMENT
    ═══════════════════════════════════════ */
    .signal-item {
        display: flex;
        align-items: flex-start;
        gap: 0.55rem;
        padding: 0.55rem 0;
        border-bottom: 1px solid rgba(16,185,129,0.08);
        color: #d1fae5;
        font-size: 0.84rem;
        line-height: 1.5;
    }
    .signal-item:last-child { border-bottom: none; }
    .signal-dot { color: #34d399; flex-shrink: 0; font-size: 0.75rem; margin-top: 0.15rem; }

    /* ═══════════════════════════════════════
       COMPANY INTEL
    ═══════════════════════════════════════ */
    .intel-round {
        display: inline-block;
        background: rgba(16,185,129,0.09);
        color: #6ee7b7;
        border: 1px solid rgba(16,185,129,0.18);
        border-radius: 7px;
        font-size: 0.76rem;
        font-weight: 600;
        padding: 0.24rem 0.7rem;
        margin: 0.18rem;
    }
    .intel-notes {
        background: rgba(255,255,255,0.02);
        border-left: 3px solid rgba(99,102,241,0.4);
        border-radius: 0 10px 10px 0;
        padding: 0.9rem 1.1rem;
        color: #94a3b8;
        font-size: 0.85rem;
        line-height: 1.75;
        margin-top: 0.6rem;
    }

    /* ═══════════════════════════════════════
       DSA STATUS + CTA
    ═══════════════════════════════════════ */
    .dsa-success {
        background: rgba(16,185,129,0.07);
        border: 1px solid rgba(16,185,129,0.18);
        border-radius: 14px;
        padding: 1rem 1.4rem;
        color: #6ee7b7;
        font-weight: 600;
        font-size: 0.9rem;
        text-align: center;
        margin-bottom: 1.5rem;
        letter-spacing: 0.01em;
    }
    .dsa-warn {
        background: rgba(239,68,68,0.07);
        border: 1px solid rgba(239,68,68,0.18);
        border-radius: 14px;
        padding: 1rem 1.4rem;
        color: #fca5a5;
        font-size: 0.9rem;
        text-align: center;
    }

    /* ═══════════════════════════════════════
       EMPTY STATE
    ═══════════════════════════════════════ */
    .empty-state {
        text-align: center;
        display: none;
        padding: 0;
    }
    .empty-icon {
        font-size: 2.8rem;
        margin-bottom: 0.6rem;
        opacity: 0.2;
    }
    .empty-text {
        font-size: 0.86rem;
        color: #2d2d4a;
        font-weight: 500;
    }

    [data-testid="stFileUploader"] {
        margin-bottom: -0.2rem;
    }
    [data-testid="stFileUploader"] section {
        min-height: 76px !important;
        padding: 0.55rem 0.75rem !important;
    }
    [data-testid="stFileUploader"] section > div {
        padding: 0 !important;
    }
    [data-testid="stFileUploader"] small {
        display: none !important;
    }
    [data-testid="stTextArea"] textarea {
        min-height: 70px !important;
    }
    div[data-testid="stVerticalBlock"] > div:has([data-testid="stForm"]) {
        margin-top: 0 !important;
    }

    @media (max-height: 820px) {
        .topnav { padding-top: 0.65rem; }
        .brand-mark { width: 28px; height: 28px; }
        .hero { padding: 0.45rem 1rem 0.55rem; }
        .hero-eyebrow {
            padding: 0.26rem 0.75rem;
            margin-bottom: 0.45rem;
            font-size: 0.62rem;
        }
        .hero h1 {
            font-size: clamp(1.85rem, 3.7vw, 2.55rem);
            margin-bottom: 0.42rem;
            line-height: 1.0;
        }
        .hero-sub {
            margin-bottom: 0;
            font-size: 0.8rem;
            line-height: 1.4;
            max-width: 620px;
        }
        .hero-pills { display: none; }
        [data-testid="stForm"] { padding: 0.75rem 0.9rem 0.85rem !important; }
        .setup-card-header { margin-bottom: 0; }
        .setup-card-icon { width: 28px; height: 28px; }
        .setup-card-title { font-size: 0.92rem; }
        .setup-card-sub {
            font-size: 0.76rem;
            margin-bottom: 0.55rem;
            padding-left: 2.15rem;
        }
        [data-testid="stFileUploader"] section {
            min-height: 54px !important;
            padding: 0.35rem 0.55rem !important;
        }
        [data-testid="stTextArea"] textarea {
            min-height: 48px !important;
        }
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            padding: 0.42rem 0.7rem !important;
        }
        .stButton > button[kind="primary"],
        .stFormSubmitButton > button {
            padding: 0.52rem 1.2rem !important;
        }
    }

    @media (max-width: 700px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .topnav {
            padding-top: 0.65rem;
        }
        .nav-tag {
            font-size: 0.56rem;
        }
        .hero {
            padding: 0.7rem 0 0.8rem;
        }
        .hero-eyebrow {
            font-size: 0.58rem;
            padding: 0.24rem 0.65rem;
            margin-bottom: 0.65rem;
            letter-spacing: 0.08em;
        }
        .hero h1 {
            font-size: 2rem;
            line-height: 1.04;
            margin-bottom: 0.55rem;
        }
        .hero-sub {
            font-size: 0.82rem;
            line-height: 1.45;
            margin-bottom: 0;
        }
        .hero-pills {
            display: none;
        }
        [data-testid="stForm"] {
            padding: 0.9rem 0.85rem 1rem !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TOPNAV
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="topnav">
        <div class="brand">
            <div class="brand-mark">⚡</div>
            <span class="brand-text">Internly</span>
        </div>
        <span class="nav-tag">AI Interview Prep</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# HERO
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="hero">
        <div class="hero-eyebrow">
            <span class="hero-eyebrow-dot"></span>
            AI-Powered · Personalised · Real-time
        </div>
        <h1>Crack Your Next<br>Technical Interview</h1>
        <p class="hero-sub">
            Upload your resume, pick a target company, and get a fully personalised
            DSA mock interview modelled on how that company actually hires.
        </p>
        <div class="hero-pills">
            <span class="hero-pill">🎯 Company-specific questions</span>
            <span class="hero-pill">🧠 AI adaptive interviewer</span>
            <span class="hero-pill">📊 Detailed performance report</span>
            <span class="hero-pill">🔍 JD alignment analysis</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SETUP CARD
# ═══════════════════════════════════════════════════════════════════════════════
with st.container():
    col_l, col_c, col_r = st.columns([0.75, 2.7, 0.75])
    with col_c:
        with st.form("session_setup_form", clear_on_submit=False):
            st.markdown(
                """
                <div class="setup-card-header">
                    <div class="setup-card-icon">🎯</div>
                    <p class="setup-card-title">Set up your session</p>
                </div>
                <p class="setup-card-sub">Upload your resume and choose the role to prepare for.</p>
                """,
                unsafe_allow_html=True,
            )

            uploaded_resume = st.file_uploader(
                "Resume (PDF or DOCX)", type=["pdf", "docx"], label_visibility="visible"
            )

            c_a, c_b = st.columns(2)
            with c_a:
                target_company = st.text_input(
                    "Target Company", placeholder="e.g. Google, Stripe"
                )
            with c_b:
                target_role = st.text_input(
                    "Target Role", placeholder="e.g. SDE-2, Backend Eng."
                )

            target_jd = st.text_area(
                "Job Description (optional)",
                placeholder="Paste the JD to detect alignment signals and skill gaps...",
                height=78,
            )

            analyze_clicked = st.form_submit_button(
                "✨ Analyse Resume & Research Company", type="primary"
            )


# ── run pipeline on click ─────────────────────────────────────────────────────
if analyze_clicked:
    if not uploaded_resume or not target_company or not target_role:
        st.error("Please upload a resume and fill in both Company and Role fields.")
    else:
        suffix = Path(uploaded_resume.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(uploaded_resume.getbuffer())
            temp_path = handle.name

        # ── Staged loading with st.status ────────────────────────────────────
        with st.status("🔍 Running analysis pipeline…", expanded=True) as status:
            st.write("📄 Parsing resume and extracting profile…")
            with get_session() as session:
                st.write("🏢 Researching company interview patterns…")
                pipeline_result = run_pipeline_start(
                    session,
                    resume_file_path=temp_path,
                    target_role=target_role,
                    target_company=target_company,
                    allow_search=True,
                    job_description=target_jd,
                )
            st.write("✅ Analysis complete — building your interview session!")
            status.update(
                label="✅ Ready! Scroll down to see your profile.",
                state="complete",
                expanded=False,
            )

        st.session_state.pipeline_result = pipeline_result
        st.session_state.target_company = target_company
        st.session_state.target_role = target_role
        # reset any prior interview
        st.session_state.interview_session_id = None
        st.session_state.used_question_ids = set()
        st.session_state.active_question_index = None
        st.session_state.active_question_text = None
        st.session_state.chat_history = []
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# RESULTS SECTION
# ═══════════════════════════════════════════════════════════════════════════════
pipeline_result = st.session_state.pipeline_result

if pipeline_result:
    profile = pipeline_result.resume_profile
    intel   = pipeline_result.company_intel
    company = st.session_state.target_company
    role    = st.session_state.target_role

    st.markdown("<hr class='results-divider'>", unsafe_allow_html=True)

    # ── Section header ────────────────────────────────────────────────────────
    col_l, col_c, col_r = st.columns([1, 6, 1])
    with col_c:
        st.markdown(
            f"""
            <div>
                <div class="sec-eyebrow">📄 Resume Analysis</div>
                <div class="sec-title">{company} — {role}</div>
                <div class="sec-sub">Your personalised profile extracted by our AI evaluator.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── 3-column layout ───────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([1, 1, 1], gap="medium")

    # ── Col 1: Experience + Education + Gaps ──────────────────────────────────
    with c1:
        years  = int(profile.years_experience)
        months = int(round((profile.years_experience - years) * 12))
        if months == 12:
            years += 1; months = 0
        exp_parts = []
        if years  > 0: exp_parts.append(f"{years} yr{'s' if years != 1 else ''}")
        if months > 0 or not exp_parts: exp_parts.append(f"{months} mo{'s' if months != 1 else ''}")
        exp_text = " · ".join(exp_parts)

        st.markdown(
            f"""
            <div class="profile-card">
                <div class="card-eyebrow">👤 Experience</div>
                <div class="stat-value">{exp_text}</div>
                <div class="stat-label">of professional experience</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        import re
        if profile.education:
            parts    = [p.strip() for p in re.split(r"[;\n]", profile.education) if p.strip()]
            edu_html = "".join(f'<div class="edu-entry">📍 {p}</div>' for p in parts)
        else:
            edu_html = '<div style="color:#4b5563;font-style:italic;font-size:0.85rem;">Not specified</div>'

        st.markdown(
            f"""
            <div class="profile-card">
                <div class="card-eyebrow">🎓 Education</div>
                {edu_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if profile.notable_gaps:
            gaps_html = "".join(f'<div class="gap-item">⚠ {g}</div>' for g in profile.notable_gaps)
            st.markdown(
                f'<div class="profile-card"><div class="card-eyebrow">⚡ Notable Gaps</div>{gaps_html}</div>',
                unsafe_allow_html=True,
            )

    # ── Col 2: Skills ────────────────────────────────────────────────────────
    with c2:
        chips_html = "".join(
            f'<span class="skill-chip">{s}</span>' for s in profile.skills
        ) if profile.skills else '<span style="color:#4b5563;font-size:0.85rem;">No skills extracted</span>'

        lang_section = ""
        if getattr(profile, "target_languages", None):
            langs      = "".join(f'<span class="lang-chip">{l}</span>' for l in profile.target_languages)
            lang_section = (
                '<div class="card-eyebrow" style="margin-top:1.4rem;">💻 Proficient Languages</div>'
                f'<div style="margin-top:0.4rem">{langs}</div>'
            )

        st.markdown(
            f"""
            <div class="profile-card" style="min-height:300px">
                <div class="card-eyebrow">🛠 Skills &amp; Technologies</div>
                <div style="margin-top:0.4rem">{chips_html}</div>
                {lang_section}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Col 3: Projects ───────────────────────────────────────────────────────
    with c3:
        if profile.projects:
            projects_html = "".join(
                f'<div class="project-item"><div class="project-dot"></div>{p}</div>'
                for p in profile.projects
            )
        else:
            projects_html = '<span style="color:#4b5563;font-size:0.85rem;">No projects extracted</span>'

        st.markdown(
            f"""
            <div class="profile-card" style="min-height:300px">
                <div class="card-eyebrow">🚀 Projects</div>
                {projects_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── JD Alignment row ─────────────────────────────────────────────────────
    if getattr(profile, "alignment_signals", None) or getattr(profile, "skill_gaps", None):
        st.markdown("<hr class='results-divider'>", unsafe_allow_html=True)

        col_l, col_c, col_r = st.columns([1, 6, 1])
        with col_c:
            st.markdown(
                """
                <div>
                    <div class="sec-eyebrow">🎯 JD Alignment</div>
                    <div class="sec-title">Resume vs. Job Description</div>
                    <div class="sec-sub">Signals extracted from your resume against the target role requirements.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        ca, cb = st.columns(2, gap="medium")
        with ca:
            if getattr(profile, "alignment_signals", None):
                items = "".join(
                    f'<div class="signal-item"><span class="signal-dot">✦</span>{sig}</div>'
                    for sig in profile.alignment_signals
                )
                st.markdown(
                    f"""
                    <div class="profile-card" style="border-color:rgba(16,185,129,0.15);">
                        <div class="card-eyebrow" style="color:#059669;">💪 Alignment Signals</div>
                        {items}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        with cb:
            if getattr(profile, "skill_gaps", None):
                items = "".join(
                    f'<div class="gap-item">⚠️ {gap}</div>'
                    for gap in profile.skill_gaps
                )
                st.markdown(
                    f"""
                    <div class="profile-card" style="border-color:rgba(239,68,68,0.12);">
                        <div class="card-eyebrow" style="color:#dc2626;">🔧 Skill Gaps</div>
                        {items}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── Company Intel row ─────────────────────────────────────────────────────
    st.markdown("<hr class='results-divider'>", unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 6, 1])
    with col_c:
        st.markdown(
            f"""
            <div>
                <div class="sec-eyebrow">🏢 Company Intel</div>
                <div class="sec-title">{company}</div>
                <div class="sec-sub">Research gathered from real interview reports and community sources.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    ci1, ci2 = st.columns(2, gap="medium")

    with ci1:
        if intel and intel.interview_rounds:
            rounds_html = "".join(
                f'<span class="intel-round">{r}</span>' for r in intel.interview_rounds
            )
            st.markdown(
                f'<div class="profile-card"><div class="card-eyebrow">📋 Interview Rounds</div>{rounds_html}</div>',
                unsafe_allow_html=True,
            )
        if intel and intel.common_questions:
            qs_html = "".join(
                f'<div class="project-item"><div class="project-dot"></div>{q}</div>'
                for q in intel.common_questions
            )
            st.markdown(
                f'<div class="profile-card"><div class="card-eyebrow">❓ Commonly Asked Topics</div>{qs_html}</div>',
                unsafe_allow_html=True,
            )

    with ci2:
        if intel and intel.difficulty_notes:
            st.markdown(
                f"""
                <div class="profile-card">
                    <div class="card-eyebrow">📊 Difficulty Notes</div>
                    <div class="intel-notes">{intel.difficulty_notes}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if intel and intel.culture_notes:
            st.markdown(
                f"""
                <div class="profile-card">
                    <div class="card-eyebrow">🌱 Culture Notes</div>
                    <div class="intel-notes">{intel.culture_notes}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── DSA availability + CTA ────────────────────────────────────────────────
    st.markdown("<hr class='results-divider'>", unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        if pipeline_result.dsa_available:
            st.markdown(
                f'<div class="dsa-success">✅ {pipeline_result.dsa_message}</div>',
                unsafe_allow_html=True,
            )
            if st.button("🚀 Start Mock Interview", type="primary", key="start_interview_btn"):
                st.switch_page("pages/interview.py")
        else:
            st.markdown(
                f'<div class="dsa-warn">⚠️ {pipeline_result.dsa_message} '
                f'Please ingest DSA questions for <strong>{company}</strong> first.</div>',
                unsafe_allow_html=True,
            )

else:
    # ── Empty state ───────────────────────────────────────────────────────────
    col_l, col_c, col_r = st.columns([1, 3, 1])
    with col_c:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">📂</div>
                <div class="empty-text">Fill in the form above to get started</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
