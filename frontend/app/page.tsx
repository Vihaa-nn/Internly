"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Target,
  Brain,
  BarChart3,
  Search,
  FileText,
  Upload,
  Sparkles,
  User,
  GraduationCap,
  AlertTriangle,
  Wrench,
  Laptop,
  Rocket,
  ClipboardList,
  HelpCircle,
  TrendingUp,
  Sprout,
  Loader2,
  Code2,
  MessageSquare,
} from "lucide-react";
import { analyseResume, type AnalyseResult } from "@/lib/api";
import { formatDisplayLabel } from "@/lib/format";
import { Separator } from "@/components/ui/separator";
import {
  BrandMark,
  BrandTitle,
  GlassCard,
  Eyebrow,
  SectionTitle,
  PrimaryCta,
} from "@/components/internly-ui";

const FEATURES = [
  { icon: Target, label: "Company-specific questions" },
  { icon: Brain, label: "AI adaptive interviewer" },
  { icon: BarChart3, label: "Detailed performance report" },
  { icon: Search, label: "JD alignment analysis" },
] as const;

const STATS = [
  { value: "DSA-first", label: "Interview focus" },
  { value: "Real-time", label: "Adaptive feedback" },
  { value: "Tailored", label: "Per company & role" },
] as const;

function LandingBackground() {
  return (
    <div className="landing-bg" aria-hidden>
      <div className="landing-bg__blob landing-bg__blob--indigo" />
      <div className="landing-bg__blob landing-bg__blob--violet" />
      <div className="landing-bg__blob landing-bg__blob--cyan" />
      <div className="landing-bg__blob landing-bg__blob--rose" />
      <div className="landing-bg__blob landing-bg__blob--emerald" />
    </div>
  );
}

function LandingNav() {
  return (
    <header className="landing-nav sticky top-0 z-30">
      <div className="max-w-[1280px] mx-auto px-5 sm:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <BrandMark />
          <BrandTitle className="text-[1.15rem]" />
        </div>
        <span className="hidden sm:inline text-[0.68rem] font-bold tracking-[0.18em] uppercase text-muted-foreground">
          AI Interview Prep
        </span>
      </div>
    </header>
  );
}

function LandingHero() {
  return (
    <div className="flex flex-col justify-center h-full max-w-xl">
      <div className="inline-flex items-center gap-2 bg-card/60 border border-border text-primary text-[0.68rem] font-bold tracking-widest uppercase px-4 py-1.5 rounded-full mb-7 w-fit backdrop-blur-sm">
        <span className="pulse-dot w-1.5 h-1.5 bg-primary rounded-full" />
        AI-Powered · Personalised · Real-time
      </div>

      <h1 className="text-[2.6rem] sm:text-5xl xl:text-[3.4rem] font-black leading-[1.06] mb-5 text-foreground tracking-tight">
        Crack Your Next
        <br />
        <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-violet-400 to-cyan-300">
          Technical Interview
        </span>
      </h1>

      <p className="text-muted-foreground text-[1.02rem] leading-relaxed mb-8 max-w-md">
        Upload your resume, pick a target company, and get a fully personalised DSA mock
        interview modelled on how that company actually hires.
      </p>

      <div className="flex flex-wrap gap-2 mb-10">
        {FEATURES.map(({ icon: Icon, label }) => (
          <span
            key={label}
            className="inline-flex items-center gap-1.5 bg-card/50 border border-border text-muted-foreground text-[0.72rem] font-medium px-3 py-2 rounded-full backdrop-blur-sm"
          >
            <Icon className="w-3.5 h-3.5 text-primary shrink-0" strokeWidth={2} />
            {label}
          </span>
        ))}
      </div>

      <div className="flex flex-wrap items-center">
        {STATS.map(({ value, label }) => (
          <div key={label} className="landing-stat mb-3 sm:mb-0">
            <p className="text-[1.35rem] font-black text-foreground leading-none">{value}</p>
            <p className="text-[0.72rem] text-muted-foreground mt-1">{label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

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
      const formattedCompany = formatDisplayLabel(company);
      const formattedRole = formatDisplayLabel(role);
      const result = await analyseResume(resumeFile, formattedCompany, formattedRole, jd.trim());
      setStatus("Analysis complete!");
      onResult(result, formattedCompany, formattedRole);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Something went wrong.";
      if (message === "Failed to fetch") {
        setError(
          "Cannot reach the backend at http://localhost:8000. Start it with: uvicorn internly.api:app --reload --port 8000"
        );
      } else {
        setError(message);
      }
    } finally {
      setLoading(false);
      setStatus("");
    }
  }

  return (
    <div className="relative w-full max-w-[460px] mx-auto lg:mx-0 lg:ml-auto">
      <span className="landing-float-badge -top-3 -left-2 sm:-left-6 text-violet-300 border-violet-800/50">
        <Code2 className="w-3.5 h-3.5 text-violet-400" />
        LeetCode integrated
      </span>
      <span className="landing-float-badge -bottom-3 -right-1 sm:-right-5 text-emerald-300 border-emerald-800/40">
        <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
        Live mock interview
      </span>

      <form onSubmit={handleSubmit} className="landing-form-card p-7 sm:p-8 w-full">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-9 h-9 bg-secondary border border-border rounded-xl flex items-center justify-center">
            <Target className="w-4 h-4 text-primary" strokeWidth={2} />
          </div>
          <p className="text-[1.1rem] font-extrabold text-foreground tracking-tight">
            Start your session
          </p>
        </div>
        <p className="text-[0.82rem] text-muted-foreground mb-6 pl-12">
          Upload your resume and choose the role to prepare for.
        </p>

        <div className="mb-4">
          <label className="field-label">Resume (PDF or DOCX)</label>
          <div
            onClick={() => fileRef.current?.click()}
            className="flex items-center gap-3 bg-card/80 border-[1.5px] border-dashed border-primary/40 rounded-[14px] p-4 cursor-pointer hover:border-primary transition-colors duration-200"
          >
            <FileText className="w-8 h-8 text-primary flex-shrink-0" strokeWidth={1.5} />
            <div className="min-w-0">
              <p className="text-foreground text-[0.85rem] font-medium truncate">
                {resumeFile ? resumeFile.name : "Click to upload resume"}
              </p>
              <p className="text-muted-foreground text-[0.75rem]">PDF or DOCX, up to 10 MB</p>
            </div>
            <Upload className="w-4 h-4 text-muted-foreground ml-auto shrink-0" />
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={(e) => setResumeFile(e.target.files?.[0] ?? null)}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="field-label">Target Company</label>
            <input
              className="field-input"
              placeholder="e.g. Google, Stripe"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            />
          </div>
          <div>
            <label className="field-label">Target Role</label>
            <input
              className="field-input"
              placeholder="e.g. SDE-2, Backend Eng."
              value={role}
              onChange={(e) => setRole(e.target.value)}
            />
          </div>
        </div>

        <div className="mb-5">
          <label className="field-label">Job Description (optional)</label>
          <textarea
            className="field-input min-h-[80px] resize-none"
            placeholder="Paste the JD to detect alignment signals and skill gaps…"
            value={jd}
            onChange={(e) => setJd(e.target.value)}
          />
        </div>

        {error && (
          <p className="text-red-400 text-[0.82rem] mb-3 bg-red-950/40 border border-red-900 rounded-xl px-3 py-2">
            {error}
          </p>
        )}

        <PrimaryCta type="submit" disabled={loading}>
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              {status || "Analysing…"}
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <Sparkles className="w-4 h-4" />
              Analyse Resume & Research Company
            </span>
          )}
        </PrimaryCta>
      </form>
    </div>
  );
}

interface ResultsProps {
  result: AnalyseResult;
  company: string;
  role: string;
  onStartInterview: () => void;
  onBack: () => void;
}

function Results({ result, company, role, onStartInterview, onBack }: ResultsProps) {
  const { resume_profile: profile, company_intel: intel } = result;

  let years = Math.floor(profile.years_experience);
  let months = Math.round((profile.years_experience - years) * 12);
  if (months === 12) { years += 1; months = 0; }
  let expText = "None";
  if (years > 0 && months > 0) expText = `${years} yr${years !== 1 ? "s" : ""} ${months} mo${months !== 1 ? "s" : ""}`;
  else if (years > 0) expText = `${years} yr${years !== 1 ? "s" : ""}`;
  else if (months > 0) expText = `${months} mo${months !== 1 ? "s" : ""}`;

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-8 gap-4">
        <SectionTitle
          eyebrow="Analysis Complete"
          title={`${formatDisplayLabel(company)} — ${formatDisplayLabel(role)}`}
          sub="Your personalised profile and company research."
        />
        <button
          type="button"
          onClick={onBack}
          className="text-primary text-[0.82rem] font-semibold hover:underline shrink-0"
        >
          ← New session
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-10">
        <div>
          <GlassCard hover className="mb-4">
            <Eyebrow className="flex items-center gap-1.5">
              <User className="w-3 h-3" /> Experience
            </Eyebrow>
            <p className="text-4xl font-black text-foreground leading-tight">{expText}</p>
            <p className="text-muted-foreground text-[0.78rem] mt-1.5">of professional experience</p>
          </GlassCard>

          {profile.education && (
            <GlassCard hover className="mb-4">
              <Eyebrow className="flex items-center gap-1.5">
                <GraduationCap className="w-3 h-3" /> Education
              </Eyebrow>
              {profile.education
                .split(/[;\n]/)
                .filter(Boolean)
                .map((e, i) => (
                  <p key={i} className="text-muted-foreground text-[0.88rem] leading-relaxed py-1.5 border-b border-border last:border-0">
                    {e.trim()}
                  </p>
                ))}
            </GlassCard>
          )}

          {profile.notable_gaps.length > 0 && (
            <GlassCard hover>
              <Eyebrow className="flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3" /> Notable Gaps
              </Eyebrow>
              {profile.notable_gaps.map((g, i) => (
                <div key={i} className="bg-red-950/40 border border-red-900 rounded-[10px] px-3 py-2 text-red-300 text-[0.84rem] mb-2 last:mb-0 font-medium">
                  {g}
                </div>
              ))}
            </GlassCard>
          )}
        </div>

        <div>
          <GlassCard hover className="min-h-[300px]">
            <Eyebrow className="flex items-center gap-1.5">
              <Wrench className="w-3 h-3" /> Skills & Technologies
            </Eyebrow>
            <div className="flex flex-wrap mt-1">
              {profile.skills.length > 0 ? (
                profile.skills.map((s) => (
                  <span key={s} className="inline-block bg-secondary text-primary border border-border rounded-[7px] text-[0.74rem] font-semibold px-2.5 py-1 m-0.5">
                    {s}
                  </span>
                ))
              ) : (
                <span className="text-muted-foreground text-[0.85rem]">No skills extracted</span>
              )}
            </div>
            {profile.target_languages.length > 0 && (
              <>
                <Eyebrow className="flex items-center gap-1.5 mt-4">
                  <Laptop className="w-3 h-3" /> Proficient Languages
                </Eyebrow>
                <div className="flex flex-wrap">
                  {profile.target_languages.map((l) => (
                    <span key={l} className="inline-block bg-violet-950/40 text-violet-300 border border-violet-800 rounded-[7px] text-[0.74rem] font-semibold px-2.5 py-1 m-0.5">
                      {l}
                    </span>
                  ))}
                </div>
              </>
            )}
          </GlassCard>
        </div>

        <div>
          <GlassCard hover className="min-h-[300px]">
            <Eyebrow className="flex items-center gap-1.5">
              <Rocket className="w-3 h-3" /> Projects
            </Eyebrow>
            {profile.projects.length > 0 ? (
              profile.projects.map((p, i) => (
                <div key={i} className="flex items-start gap-2.5 py-2 border-b border-border last:border-0">
                  <div className="w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0 bg-primary" />
                  <span className="text-muted-foreground text-[0.86rem] leading-relaxed">{p}</span>
                </div>
              ))
            ) : (
              <span className="text-muted-foreground text-[0.85rem]">No projects extracted</span>
            )}
          </GlassCard>
        </div>
      </div>

      <Separator className="bg-border my-10" />
      <SectionTitle
        eyebrow="Company Intel"
        title={formatDisplayLabel(company)}
        sub="Research gathered from real interview reports and community sources."
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-10">
        <div>
          {intel?.interview_rounds && intel.interview_rounds.length > 0 && (
            <GlassCard hover className="mb-4">
              <Eyebrow className="flex items-center gap-1.5">
                <ClipboardList className="w-3 h-3" /> Interview Rounds
              </Eyebrow>
              <div className="flex flex-wrap">
                {intel.interview_rounds.map((r) => (
                  <span key={r} className="inline-block bg-emerald-950/40 text-emerald-300 border border-emerald-800 rounded-[7px] text-[0.76rem] font-semibold px-2.5 py-1 m-0.5">
                    {r}
                  </span>
                ))}
              </div>
            </GlassCard>
          )}
          {intel?.common_questions && intel.common_questions.length > 0 && (
            <GlassCard hover>
              <Eyebrow className="flex items-center gap-1.5">
                <HelpCircle className="w-3 h-3" /> Commonly Asked Topics
              </Eyebrow>
              {intel.common_questions.map((q, i) => (
                <div key={i} className="flex items-start gap-2.5 py-2 border-b border-border last:border-0">
                  <div className="w-1.5 h-1.5 rounded-full mt-2 flex-shrink-0 bg-primary" />
                  <span className="text-muted-foreground text-[0.86rem] leading-relaxed">{q}</span>
                </div>
              ))}
            </GlassCard>
          )}
        </div>
        <div>
          {intel?.difficulty_notes && (
            <GlassCard hover className="mb-4">
              <Eyebrow className="flex items-center gap-1.5">
                <TrendingUp className="w-3 h-3" /> Difficulty Notes
              </Eyebrow>
              <div className="bg-secondary/50 border-l-[3px] border-primary/50 rounded-r-[10px] px-4 py-3 text-muted-foreground text-[0.85rem] leading-[1.75] mt-1.5">
                {intel.difficulty_notes}
              </div>
            </GlassCard>
          )}
          {intel?.culture_notes && (
            <GlassCard hover>
              <Eyebrow className="flex items-center gap-1.5">
                <Sprout className="w-3 h-3" /> Culture Notes
              </Eyebrow>
              <div className="bg-secondary/50 border-l-[3px] border-primary/50 rounded-r-[10px] px-4 py-3 text-muted-foreground text-[0.85rem] leading-[1.75] mt-1.5">
                {intel.culture_notes}
              </div>
            </GlassCard>
          )}
        </div>
      </div>

      <Separator className="bg-border my-10" />
      <div className="max-w-md mx-auto text-center pb-8">
        {result.dsa_available ? (
          <PrimaryCta onClick={onStartInterview} className="py-3.5 text-[0.95rem]">
            <span className="flex items-center justify-center gap-2">
              <Rocket className="w-4 h-4" />
              Start Mock Interview
            </span>
          </PrimaryCta>
        ) : (
          <div className="bg-red-950/40 border border-red-900 rounded-[14px] px-6 py-4 text-red-300 text-[0.9rem]">
            {result.dsa_message} Please ingest DSA questions for <strong>{company}</strong> first.
          </div>
        )}
      </div>
    </div>
  );
}

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

  function handleBack() {
    setResult(null);
    setCompany("");
    setRole("");
  }

  return (
    <div className="landing-shell">
      <LandingBackground />
      <LandingNav />

      {result ? (
        <main className="max-w-[1180px] mx-auto px-5 sm:px-8 py-8 pb-16">
          <Results
            result={result}
            company={company}
            role={role}
            onStartInterview={() => router.push("/interview")}
            onBack={handleBack}
          />
        </main>
      ) : (
        <main className="max-w-[1280px] mx-auto px-5 sm:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center min-h-[calc(100vh-4rem)] py-12 lg:py-16">
            <section>
              <LandingHero />
            </section>
            <section className="flex items-center justify-center lg:justify-end py-4">
              <SetupForm onResult={handleResult} />
            </section>
          </div>
        </main>
      )}
    </div>
  );
}
