from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from internly.db.database import get_session, init_db
from internly.pipeline import run_pipeline_start

st.set_page_config(
    page_title="Internly – Resume Analyzer",
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background: #0f0f13; }

    /* hide default streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }

    /* ── hero area ── */
    .hero {
        text-align: center;
        padding: 3.5rem 1rem 2rem;
    }
    .hero-badge {
        display: inline-block;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: #fff;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        padding: 0.3rem 0.9rem;
        border-radius: 999px;
        margin-bottom: 1.2rem;
    }
    .hero h1 {
        font-size: clamp(2.2rem, 5vw, 3.5rem);
        font-weight: 800;
        background: linear-gradient(135deg, #e0e7ff 0%, #a5b4fc 50%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.15;
        margin: 0 0 1rem;
    }
    .hero p {
        color: #94a3b8;
        font-size: 1.05rem;
        max-width: 560px;
        margin: 0 auto 2.5rem;
        line-height: 1.7;
    }

    /* ── upload card ── */
    .upload-card {
        background: linear-gradient(145deg, #1e1e2e, #16162a);
        border: 1px solid #2d2d4a;
        border-radius: 20px;
        padding: 2.5rem;
        max-width: 620px;
        margin: 0 auto;
        box-shadow: 0 20px 60px rgba(99,102,241,0.08);
    }
    .upload-card h3 {
        color: #e2e8f0;
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0 0 1.5rem;
    }

    /* ── form inputs ── */
    .stTextInput > div > div > input {
        background: #1a1a2e !important;
        border: 1px solid #2d2d4a !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
        font-family: 'Inter', sans-serif !important;
        padding: 0.65rem 1rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
    }
    .stTextInput label { color: #94a3b8 !important; font-size: 0.85rem !important; }

    /* ── file uploader ── */
    .stFileUploader > div {
        background: #1a1a2e !important;
        border: 1.5px dashed #2d2d4a !important;
        border-radius: 12px !important;
    }
    .stFileUploader label { color: #94a3b8 !important; font-size: 0.85rem !important; }

    /* ── primary button ── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #7c3aed 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.8rem !important;
        font-size: 0.95rem !important;
        width: 100% !important;
        letter-spacing: 0.02em !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 20px rgba(99,102,241,0.35) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 8px 28px rgba(99,102,241,0.5) !important;
    }

    /* ── result profile cards ── */
    .section-header {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #6366f1;
        margin-bottom: 1.5rem;
    }
    .profile-card {
        background: linear-gradient(145deg, #1e1e2e, #16162a);
        border: 1px solid #2d2d4a;
        border-radius: 16px;
        padding: 1.8rem;
        margin-bottom: 1.2rem;
    }
    .profile-card h4 {
        color: #94a3b8;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin: 0 0 0.9rem;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: 800;
        color: #e2e8f0;
        line-height: 1;
    }
    .stat-label { color: #64748b; font-size: 0.8rem; margin-top: 0.25rem; }

    .skill-chip {
        display: inline-block;
        background: rgba(99,102,241,0.15);
        color: #a5b4fc;
        border: 1px solid rgba(99,102,241,0.3);
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 500;
        padding: 0.25rem 0.75rem;
        margin: 0.2rem 0.2rem 0.2rem 0;
    }
    .project-item {
        background: rgba(255,255,255,0.03);
        border: 1px solid #2d2d4a;
        border-radius: 10px;
        padding: 0.65rem 0.9rem;
        margin-bottom: 0.5rem;
        color: #cbd5e1;
        font-size: 0.88rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .project-dot {
        width: 6px; height: 6px;
        background: #6366f1;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .gap-item {
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.2);
        border-radius: 10px;
        padding: 0.5rem 0.9rem;
        color: #fca5a5;
        font-size: 0.85rem;
        margin-bottom: 0.4rem;
    }
    .intel-round {
        display: inline-block;
        background: rgba(16,185,129,0.12);
        color: #6ee7b7;
        border: 1px solid rgba(16,185,129,0.25);
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 500;
        padding: 0.3rem 0.75rem;
        margin: 0.2rem;
    }
    .intel-notes {
        background: rgba(255,255,255,0.03);
        border-left: 3px solid #6366f1;
        border-radius: 0 8px 8px 0;
        padding: 0.8rem 1rem;
        color: #94a3b8;
        font-size: 0.87rem;
        line-height: 1.6;
        margin-top: 0.5rem;
    }

    /* ── CTA start interview button ── */
    .cta-block {
        text-align: center;
        margin: 2.5rem 0 1rem;
    }
    .stButton > button.start-btn {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        box-shadow: 0 4px 20px rgba(16,185,129,0.35) !important;
    }
    .stButton > button.start-btn:hover {
        box-shadow: 0 8px 28px rgba(16,185,129,0.5) !important;
    }

    /* ── dsa unavailable banner ── */
    .dsa-warn {
        background: rgba(239,68,68,0.08);
        border: 1px solid rgba(239,68,68,0.25);
        border-radius: 12px;
        padding: 1rem 1.4rem;
        color: #fca5a5;
        font-size: 0.9rem;
        text-align: center;
        margin-top: 1.5rem;
    }
    .divider {
        border: none;
        border-top: 1px solid #1e1e2e;
        margin: 2rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# HERO / UPLOAD SECTION
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <div class="hero">
        <div class="hero-badge">AI-Powered Interview Prep</div>
        <h1>Crack Your Next Interview<br>with Internly</h1>
        <p>Upload your resume, pick your target company, and get a personalized
        DSA mock interview tailored to how that company actually hires.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container():
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown('<div class="upload-card">', unsafe_allow_html=True)
        st.markdown('<h3>🎯 Set up your session</h3>', unsafe_allow_html=True)

        uploaded_resume = st.file_uploader(
            "Resume (PDF or DOCX)", type=["pdf", "docx"], label_visibility="visible"
        )
        target_company = st.text_input(
            "Target Company", placeholder="e.g. Google, Amazon, Microsoft"
        )
        target_role = st.text_input(
            "Target Role", placeholder="e.g. Software Engineer, SDE-2"
        )

        analyze_clicked = st.button(
            "✨ Analyze Resume & Research Company", type="primary"
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ── run pipeline on click ─────────────────────────────────────────────────────
if analyze_clicked:
    if not uploaded_resume or not target_company or not target_role:
        st.error("Please upload a resume and fill in both Company and Role fields.")
    else:
        suffix = Path(uploaded_resume.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(uploaded_resume.getbuffer())
            temp_path = handle.name

        with st.spinner("🔍 Analyzing resume & researching company — this takes ~20 seconds..."):
            with get_session() as session:
                st.session_state.pipeline_result = run_pipeline_start(
                    session,
                    resume_file_path=temp_path,
                    target_role=target_role,
                    target_company=target_company,
                    allow_search=True,
                )
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

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # ── section label ──────────────────────────────────────────────────────────
    col_l, col_c, col_r = st.columns([1, 6, 1])
    with col_c:
        st.markdown(
            f'<p class="section-header">📄 Resume Analysis — {company} · {role}</p>',
            unsafe_allow_html=True,
        )

    # ── layout: 3 columns ──────────────────────────────────────────────────────
    c1, c2, c3 = st.columns([1, 1, 1], gap="medium")

    # ── col 1 : Experience + Education + Gaps ─────────────────────────────────
    with c1:
        # experience stat formatting
        years = int(profile.years_experience)
        months = int(round((profile.years_experience - years) * 12))
        if months == 12:
            years += 1
            months = 0
        
        exp_parts = []
        if years > 0:
            exp_parts.append(f"{years} yr{'s' if years != 1 else ''}")
        if months > 0 or not exp_parts:
            exp_parts.append(f"{months} mo{'s' if months != 1 else ''}")
        exp_text = ", ".join(exp_parts)

        st.markdown(
            f"""
            <div class="profile-card">
                <h4>👤 Experience</h4>
                <div class="stat-value" style="font-size:1.6rem; font-weight:800; color:#e2e8f0;">{exp_text}</div>
                <div class="stat-label">of professional experience</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # education parsing
        edu_html = ""
        if profile.education:
            import re
            parts = [p.strip() for p in re.split(r'[;\n]', profile.education) if p.strip()]
            for part in parts:
                edu_html += f'<div style="color:#e2e8f0; font-size:0.9rem; line-height:1.5; margin-bottom:0.6rem; padding-bottom:0.6rem; border-bottom:1px solid #2d2d4a;">📍 {part}</div>'
            # remove last border bottom decoration
            if edu_html:
                edu_html = edu_html[:edu_html.rfind('border-bottom:1px solid #2d2d4a;')] + 'border-bottom:none;">' + edu_html[edu_html.rfind('">')+2:]
        else:
            edu_html = '<div style="color:#64748b; font-style:italic;">Not specified</div>'

        st.markdown(
            f"""
            <div class="profile-card">
                <h4>🎓 Education</h4>
                <div>
                    {edu_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # gaps
        if profile.notable_gaps:
            gaps_html = "".join(
                f'<div class="gap-item">⚠ {g}</div>' for g in profile.notable_gaps
            )
            st.markdown(
                f'<div class="profile-card"><h4>⚡ Notable Gaps</h4>{gaps_html}</div>',
                unsafe_allow_html=True,
            )

    # ── col 2 : Skills ────────────────────────────────────────────────────────
    with c2:
        chips_html = "".join(
            f'<span class="skill-chip">{s}</span>' for s in profile.skills
        ) if profile.skills else '<span style="color:#64748b">No skills extracted</span>'

        st.markdown(
            f"""
            <div class="profile-card" style="min-height:280px">
                <h4>🛠 Skills & Technologies</h4>
                <div style="margin-top:0.5rem">{chips_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── col 3 : Projects ──────────────────────────────────────────────────────
    with c3:
        if profile.projects:
            projects_html = "".join(
                f'<div class="project-item"><div class="project-dot"></div>{p}</div>'
                for p in profile.projects
            )
        else:
            projects_html = '<span style="color:#64748b">No projects extracted</span>'

        st.markdown(
            f"""
            <div class="profile-card" style="min-height:280px">
                <h4>🚀 Projects</h4>
                {projects_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Company Intel row ──────────────────────────────────────────────────────
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 6, 1])
    with col_c:
        st.markdown(
            f'<p class="section-header">🏢 Company Intel — {company}</p>',
            unsafe_allow_html=True,
        )

    ci1, ci2 = st.columns(2, gap="medium")

    with ci1:
        if intel and intel.interview_rounds:
            rounds_html = "".join(
                f'<span class="intel-round">{r}</span>' for r in intel.interview_rounds
            )
            st.markdown(
                f'<div class="profile-card"><h4>📋 Interview Rounds</h4>{rounds_html}</div>',
                unsafe_allow_html=True,
            )
        if intel and intel.common_questions:
            qs_html = "".join(
                f'<div class="project-item"><div class="project-dot"></div>{q}</div>'
                for q in intel.common_questions
            )
            st.markdown(
                f'<div class="profile-card"><h4>❓ Commonly Asked Topics</h4>{qs_html}</div>',
                unsafe_allow_html=True,
            )

    with ci2:
        if intel and intel.difficulty_notes:
            st.markdown(
                f"""
                <div class="profile-card">
                    <h4>📊 Difficulty Notes</h4>
                    <div class="intel-notes">{intel.difficulty_notes}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if intel and intel.culture_notes:
            st.markdown(
                f"""
                <div class="profile-card">
                    <h4>🌱 Culture Notes</h4>
                    <div class="intel-notes">{intel.culture_notes}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── DSA availability status ────────────────────────────────────────────────
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        if pipeline_result.dsa_available:
            st.markdown(
                f"""
                <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);
                     border-radius:12px;padding:1rem 1.4rem;text-align:center;margin-bottom:1.5rem;">
                    <span style="color:#6ee7b7;font-weight:600;">✅ {pipeline_result.dsa_message}</span>
                </div>
                """,
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
    # ── landing empty state ────────────────────────────────────────────────────
    col_l, col_c, col_r = st.columns([1, 3, 1])
    with col_c:
        st.markdown(
            """
            <div style="text-align:center; padding: 2rem 0; color:#2d2d4a;">
                <div style="font-size:3rem;margin-bottom:0.5rem;">📂</div>
                <div style="color:#334155;font-size:0.9rem;">
                    Fill in the form above to get started
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
