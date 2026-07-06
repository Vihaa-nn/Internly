"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { analyseResume, type AnalyseResult } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

// ─── Navbar ──────────────────────────────────────────────────────────────────

function Navbar() {
  return (
    <nav className="flex items-center justify-between px-0 py-4 border-b border-white/5 mb-0">
      <div className="flex items-center gap-2.5">
        <div
          className="logo-glow w-8 h-8 rounded-[10px] flex items-center justify-center text-lg"
          style={{ background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)" }}
        >
          ⚡
        </div>
        <span
          className="text-[1.05rem] font-black tracking-tight"
          style={{
            background: "linear-gradient(135deg, #e0e7ff 0%, #a5b4fc 70%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Internly
        </span>
      </div>
      <span className="text-[0.68rem] font-bold tracking-widest uppercase text-slate-600">
        AI Interview Prep
      </span>
    </nav>
  );
}

// ─── Hero ─────────────────────────────────────────────────────────────────────

function Hero() {
  return (
    <div className="text-center py-10 px-4">
      <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 text-[0.72rem] font-bold tracking-widest uppercase px-4 py-1.5 rounded-full mb-5">
        <span className="pulse-dot w-1.5 h-1.5 bg-indigo-500 rounded-full" />
        AI-Powered · Personalised · Real-time
      </div>
      <h1
        className="text-5xl font-black leading-tight mb-4"
        style={{
          background: "linear-gradient(160deg, #ffffff 0%, #e0e7ff 45%, #a5b4fc 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}
      >
        Crack Your Next<br />Technical Interview
      </h1>
      <p className="text-slate-500 text-[0.92rem] max-w-xl mx-auto leading-relaxed mb-6">
        Upload your resume, pick a target company, and get a fully personalised
        DSA mock interview modelled on how that company actually hires.
      </p>
      <div className="flex justify-center flex-wrap gap-2">
        {[
          "🎯 Company-specific questions",
          "🧠 AI adaptive interviewer",
          "📊 Detailed performance report",
          "🔍 JD alignment analysis",
        ].map((pill) => (
          <span
            key={pill}
            className="inline-flex items-center gap-1.5 bg-white/[0.035] border border-white/[0.07] text-slate-400 text-[0.72rem] font-medium px-3 py-1.5 rounded-full"
          >
            {pill}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── Setup form ───────────────────────────────────────────────────────────────

interface SetupFormProps {
  onResult: (result: AnalyseResult, company: string, role: string) => void;
}

function SetupForm({ onResult }: SetupFormProps) {
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!resumeFile || !company.trim() || !role.trim()) {
      setError("Please upload a resume and fill in both Company and Role fields.");
      return;
    }
    setError("");
    setLoading(true);
    setStatus("Parsing resume and extracting profile…");
    try {
      setTimeout(() => setStatus("Researching company interview patterns…"), 3000);
      const result = await analyseResume(resumeFile, company.trim(), role.trim(), jd.trim());
      setStatus("Analysis complete!");
      onResult(result, company.trim(), role.trim());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong. Is the backend running?");
    } finally {
      setLoading(false);
      setStatus("");
    }
  }

  const inputCls =
    "w-full bg-[rgba(10,10,20,0.8)] border border-[rgba(45,45,74,0.7)] rounded-xl text-slate-200 text-[0.84rem] px-3 py-2.5 outline-none focus:border-indigo-500/55 focus:ring-2 focus:ring-indigo-500/10 placeholder-slate-700 transition-all";
  const labelCls = "block text-[0.72rem] font-bold uppercase tracking-widest text-slate-600 mb-1.5";

  return (
    <div className="max-w-[720px] mx-auto">
      <form
        onSubmit={handleSubmit}
        className="bg-gradient-to-br from-[rgba(30,30,46,0.95)] to-[rgba(20,20,38,0.95)] border border-indigo-500/14 rounded-[18px] p-6 shadow-[0_18px_48px_rgba(0,0,0,0.38),0_0_60px_rgba(99,102,241,0.06)] backdrop-blur-xl"
      >
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 bg-indigo-500/15 border border-indigo-500/25 rounded-[10px] flex items-center justify-center text-base">
            🎯
          </div>
          <p className="text-[1rem] font-extrabold text-slate-200 tracking-tight">
            Set up your session
          </p>
        </div>
        <p className="text-[0.82rem] text-slate-600 mb-5 pl-11">
          Upload your resume and choose the role to prepare for.
        </p>

        {/* Resume upload */}
        <div className="mb-4">
          <label className={labelCls}>Resume (PDF or DOCX)</label>
          <div
            onClick={() => fileRef.current?.click()}
            className="flex items-center gap-3 bg-[rgba(10,10,20,0.8)] border-[1.5px] border-dashed border-[rgba(45,45,74,0.8)] rounded-[14px] p-4 cursor-pointer hover:border-indigo-500/40 transition-colors"
          >
            <span className="text-2xl">📄</span>
            <div>
              <p className="text-slate-300 text-[0.85rem] font-medium">
                {resumeFile ? resumeFile.name : "Click to upload resume"}
              </p>
              <p className="text-slate-700 text-[0.75rem]">PDF or DOCX, up to 10 MB</p>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={(e) => setResumeFile(e.target.files?.[0] ?? null)}
            />
          </div>
        </div>

        {/* Company + Role */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className={labelCls}>Target Company</label>
            <input
              className={inputCls}
              placeholder="e.g. Google, Stripe"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            />
          </div>
          <div>
            <label className={labelCls}>Target Role</label>
            <input
              className={inputCls}
              placeholder="e.g. SDE-2, Backend Eng."
              value={role}
              onChange={(e) => setRole(e.target.value)}
            />
          </div>
        </div>

        {/* JD */}
        <div className="mb-5">
          <label className={labelCls}>Job Description (optional)</label>
          <textarea
            className={`${inputCls} min-h-[72px] resize-none`}
            placeholder="Paste the JD to detect alignment signals and skill gaps…"
            value={jd}
            onChange={(e) => setJd(e.target.value)}
          />
        </div>

        {error && (
          <p className="text-red-400 text-[0.82rem] mb-3 bg-red-500/8 border border-red-500/15 rounded-xl px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 rounded-[14px] font-bold text-[0.9rem] text-white transition-all disabled:opacity-60 disabled:cursor-not-allowed hover:-translate-y-0.5"
          style={{
            background: "linear-gradient(135deg, #6366f1 0%, #7c3aed 100%)",
            boxShadow: "0 4px 28px rgba(99,102,241,0.45)",
          }}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              {status || "Analysing…"}
            </span>
          ) : (
            "✨ Analyse Resume & Research Company"
          )}
        </button>
      </form>
    </div>
  );
}

// ─── Results ──────────────────────────────────────────────────────────────────

function SectionHeader({ eyebrow, title, sub }: { eyebrow: string; title: string; sub: string }) {
  return (
    <div className="mb-6">
      <p className="text-[0.66rem] font-extrabold tracking-[0.18em] uppercase text-indigo-500 mb-1">
        {eyebrow}
      </p>
      <h2 className="text-[1.45rem] font-black text-slate-200 mb-1">{title}</h2>
      <p className="text-slate-500 text-[0.84rem]">{sub}</p>
    </div>
  );
}

function ProfileCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-gradient-to-br from-[rgba(28,28,44,0.9)] to-[rgba(20,20,38,0.9)] border border-[rgba(45,45,74,0.5)] rounded-[18px] p-6 mb-4 hover:border-indigo-500/22 transition-all ${className}`}
    >
      {children}
    </div>
  );
}

function CardEyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[0.66rem] font-bold tracking-[0.14em] uppercase text-slate-600 mb-3">
      {children}
    </p>
  );
}

interface ResultsProps {
  result: AnalyseResult;
  company: string;
  role: string;
  onStartInterview: () => void;
}

function Results({ result, company, role, onStartInterview }: ResultsProps) {
  const { resume_profile: profile, company_intel: intel } = result;

  let years = Math.floor(profile.years_experience);
  let months = Math.round((profile.years_experience - years) * 12);
  if (months === 12) { years += 1; months = 0; }
  let expText = "None";
  if (years > 0 && months > 0) expText = `${years} yr${years !== 1 ? "s" : ""} ${months} mo${months !== 1 ? "s" : ""}`;
  else if (years > 0) expText = `${years} yr${years !== 1 ? "s" : ""}`;
  else if (months > 0) expText = `${months} mo${months !== 1 ? "s" : ""}`;

  const difficultyClass: Record<string, string> = {
    easy: "bg-emerald-500/14 text-emerald-300 border-emerald-500/25",
    medium: "bg-amber-500/12 text-amber-300 border-amber-500/25",
    hard: "bg-red-500/12 text-red-300 border-red-500/22",
  };

  return (
    <div className="mt-12">
      <Separator className="bg-white/5 mb-10" />

      {/* Resume Analysis */}
      <div className="mb-2">
        <SectionHeader
          eyebrow="📄 Resume Analysis"
          title={`${company} — ${role}`}
          sub="Your personalised profile extracted by our AI evaluator."
        />
      </div>

      <div className="grid grid-cols-3 gap-5 mb-10">
        {/* Col 1: Experience + Education + Gaps */}
        <div>
          <ProfileCard>
            <CardEyebrow>👤 Experience</CardEyebrow>
            <p className="text-4xl font-black text-slate-200 leading-tight">{expText}</p>
            <p className="text-slate-600 text-[0.78rem] mt-1.5">of professional experience</p>
          </ProfileCard>

          {profile.education && (
            <ProfileCard>
              <CardEyebrow>🎓 Education</CardEyebrow>
              {profile.education
                .split(/[;\n]/)
                .filter(Boolean)
                .map((e, i) => (
                  <p key={i} className="text-slate-300 text-[0.88rem] leading-relaxed py-1.5 border-b border-[rgba(45,45,74,0.4)] last:border-0">
                    📍 {e.trim()}
                  </p>
                ))}
            </ProfileCard>
          )}

          {profile.notable_gaps.length > 0 && (
            <ProfileCard>
              <CardEyebrow>⚡ Notable Gaps</CardEyebrow>
              {profile.notable_gaps.map((g, i) => (
                <div key={i} className="bg-red-500/7 border border-red-500/14 rounded-[10px] px-3 py-2 text-red-300 text-[0.84rem] mb-2 last:mb-0 font-medium">
                  ⚠ {g}
                </div>
              ))}
            </ProfileCard>
          )}
        </div>

        {/* Col 2: Skills */}
        <div>
          <ProfileCard className="min-h-[300px]">
            <CardEyebrow>🛠 Skills & Technologies</CardEyebrow>
            <div className="flex flex-wrap mt-1">
              {profile.skills.length > 0 ? (
                profile.skills.map((s) => (
                  <span key={s} className="inline-block bg-indigo-500/10 text-indigo-300 border border-indigo-500/18 rounded-[7px] text-[0.74rem] font-semibold px-2.5 py-1 m-0.5">
                    {s}
                  </span>
                ))
              ) : (
                <span className="text-slate-600 text-[0.85rem]">No skills extracted</span>
              )}
            </div>
            {profile.target_languages.length > 0 && (
              <>
                <CardEyebrow>💻 Proficient Languages</CardEyebrow>
                <div className="flex flex-wrap">
                  {profile.target_languages.map((l) => (
                    <span key={l} className="inline-block bg-purple-500/14 text-purple-300 border border-purple-500/28 rounded-[7px] text-[0.74rem] font-semibold px-2.5 py-1 m-0.5">
                      {l}
                    </span>
                  ))}
                </div>
              </>
            )}
          </ProfileCard>
        </div>

        {/* Col 3: Projects */}
        <div>
          <ProfileCard className="min-h-[300px]">
            <CardEyebrow>🚀 Projects</CardEyebrow>
            {profile.projects.length > 0 ? (
              profile.projects.map((p, i) => (
                <div key={i} className="flex items-start gap-2.5 py-2 border-b border-[rgba(45,45,74,0.35)] last:border-0">
                  <div className="w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }} />
                  <span className="text-slate-300 text-[0.86rem] leading-relaxed">{p}</span>
                </div>
              ))
            ) : (
              <span className="text-slate-600 text-[0.85rem]">No projects extracted</span>
            )}
          </ProfileCard>
        </div>
      </div>

      {/* Company Intel */}
      <Separator className="bg-white/5 my-10" />
      <SectionHeader
        eyebrow="🏢 Company Intel"
        title={company}
        sub="Research gathered from real interview reports and community sources."
      />
      <div className="grid grid-cols-2 gap-5 mb-10">
        <div>
          {intel?.interview_rounds && intel.interview_rounds.length > 0 && (
            <ProfileCard>
              <CardEyebrow>📋 Interview Rounds</CardEyebrow>
              <div className="flex flex-wrap">
                {intel.interview_rounds.map((r) => (
                  <span key={r} className="inline-block bg-emerald-500/9 text-emerald-300 border border-emerald-500/18 rounded-[7px] text-[0.76rem] font-semibold px-2.5 py-1 m-0.5">
                    {r}
                  </span>
                ))}
              </div>
            </ProfileCard>
          )}
          {intel?.common_questions && intel.common_questions.length > 0 && (
            <ProfileCard>
              <CardEyebrow>❓ Commonly Asked Topics</CardEyebrow>
              {intel.common_questions.map((q, i) => (
                <div key={i} className="flex items-start gap-2.5 py-2 border-b border-[rgba(45,45,74,0.35)] last:border-0">
                  <div className="w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }} />
                  <span className="text-slate-300 text-[0.86rem] leading-relaxed">{q}</span>
                </div>
              ))}
            </ProfileCard>
          )}
        </div>
        <div>
          {intel?.difficulty_notes && (
            <ProfileCard>
              <CardEyebrow>📊 Difficulty Notes</CardEyebrow>
              <div className="bg-white/[0.02] border-l-[3px] border-indigo-500/40 rounded-r-[10px] px-4 py-3 text-slate-400 text-[0.85rem] leading-[1.75] mt-1.5">
                {intel.difficulty_notes}
              </div>
            </ProfileCard>
          )}
          {intel?.culture_notes && (
            <ProfileCard>
              <CardEyebrow>🌱 Culture Notes</CardEyebrow>
              <div className="bg-white/[0.02] border-l-[3px] border-indigo-500/40 rounded-r-[10px] px-4 py-3 text-slate-400 text-[0.85rem] leading-[1.75] mt-1.5">
                {intel.culture_notes}
              </div>
            </ProfileCard>
          )}
        </div>
      </div>

      {/* CTA */}
      <Separator className="bg-white/5 my-10" />
      <div className="max-w-md mx-auto text-center">
        {result.dsa_available ? (
          <button
            onClick={onStartInterview}
            className="w-full py-3.5 rounded-[14px] font-bold text-[0.95rem] text-white hover:-translate-y-0.5 transition-all"
            style={{
              background: "linear-gradient(135deg, #6366f1 0%, #7c3aed 100%)",
              boxShadow: "0 4px 28px rgba(99,102,241,0.45)",
            }}
          >
            🚀 Start Mock Interview
          </button>
        ) : (
          <div className="bg-red-500/7 border border-red-500/18 rounded-[14px] px-6 py-4 text-red-300 text-[0.9rem]">
            ⚠️ {result.dsa_message} Please ingest DSA questions for <strong>{company}</strong> first.
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function HomePage() {
  const router = useRouter();
  const [result, setResult] = useState<AnalyseResult | null>(null);
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");

  function handleResult(r: AnalyseResult, c: string, rl: string) {
    setResult(r);
    setCompany(c);
    setRole(rl);
    sessionStorage.setItem("internly_result", JSON.stringify(r));
    sessionStorage.setItem("internly_company", c);
    sessionStorage.setItem("internly_role", rl);
  }

  function handleStartInterview() {
    router.push("/interview");
  }

  return (
    <main className="max-w-[1180px] mx-auto px-6 pb-16">
      <Navbar />
      <Hero />
      <SetupForm onResult={handleResult} />
      {result && (
        <Results result={result} company={company} role={role} onStartInterview={handleStartInterview} />
      )}
    </main>
  );
}
