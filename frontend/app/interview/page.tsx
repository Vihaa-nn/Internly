"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  startInterview,
  fetchNextQuestion,
  submitTurn,
  generateEvaluation,
  fetchLeetCode,
  type AnalyseResult,
  type TurnResult,
  type EvaluationResult,
  type QuestionBreakdown,
  type LeetCodeResult,
} from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ChatMessage {
  role: "user" | "agent";
  text: string;
  type?: string;
  animateIn?: boolean;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const DIFF_CLS: Record<string, string> = {
  easy: "bg-emerald-500/14 text-emerald-300 border border-emerald-500/25",
  medium: "bg-amber-500/12 text-amber-300 border border-amber-500/25",
  hard: "bg-red-500/12 text-red-300 border border-red-500/22",
};

const BADGE_CLS: Record<string, string> = {
  hint: "bg-amber-500/14 text-amber-300 border border-amber-500/22",
  followup: "bg-indigo-500/13 text-indigo-300 border border-indigo-500/22",
  guide: "bg-red-500/11 text-red-300 border border-red-500/20",
  accept: "bg-emerald-500/11 text-emerald-300 border border-emerald-500/20",
};

// ─── Sidebar ─────────────────────────────────────────────────────────────────

function Sidebar({
  result,
  company,
  role,
  onBack,
}: {
  result: AnalyseResult;
  company: string;
  role: string;
  onBack: () => void;
}) {
  const { resume_profile: p, company_intel: intel } = result;
  let years = Math.floor(p.years_experience);
  let months = Math.round((p.years_experience - years) * 12);
  if (months === 12) { years += 1; months = 0; }
  let expText = "None";
  if (years > 0 && months > 0) expText = `${years}yr ${months}mo`;
  else if (years > 0) expText = `${years}yr`;
  else if (months > 0) expText = `${months}mo`;

  return (
    <aside
      className="w-[260px] flex-shrink-0 border-r border-[rgba(45,45,74,0.5)] flex flex-col gap-5 px-5 py-6 overflow-y-auto"
      style={{ background: "rgba(12,12,22,0.92)", backdropFilter: "blur(16px)" }}
    >
      {/* Brand */}
      <div className="flex items-center gap-2.5 pb-4 border-b border-[rgba(45,45,74,0.5)]">
        <div
          className="w-[30px] h-[30px] rounded-[8px] flex items-center justify-center text-[0.95rem] flex-shrink-0"
          style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 14px rgba(99,102,241,0.4)" }}
        >
          ⚡
        </div>
        <span
          className="text-[1rem] font-black tracking-tight"
          style={{
            background: "linear-gradient(135deg,#e0e7ff,#a5b4fc)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Internly
        </span>
      </div>

      {/* Session info */}
      <div className="bg-indigo-500/7 border border-indigo-500/12 rounded-[12px] px-3.5 py-3">
        <p className="text-[0.72rem] text-indigo-300 font-bold tracking-wide mb-0.5">{role}</p>
        <p className="text-[0.9rem] text-slate-200 font-extrabold tracking-tight">{company}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-1.5">
        {[
          { val: expText, lbl: "Exp" },
          { val: p.skills.length, lbl: "Skills" },
          { val: p.projects.length, lbl: "Projects" },
        ].map(({ val, lbl }) => (
          <div key={lbl} className="bg-white/[0.03] border border-[rgba(45,45,74,0.4)] rounded-[10px] py-2.5 text-center">
            <p className="text-[1.05rem] font-extrabold text-slate-200">{val}</p>
            <p className="text-[0.6rem] text-slate-600 font-semibold uppercase tracking-wider mt-0.5">{lbl}</p>
          </div>
        ))}
      </div>

      {/* Skills */}
      {p.skills.length > 0 && (
        <div>
          <p className="text-[0.6rem] font-extrabold tracking-[0.16em] uppercase text-slate-600 mb-2">🛠 Skills</p>
          <div className="flex flex-wrap">
            {p.skills.slice(0, 12).map((s) => (
              <span key={s} className="inline-block bg-indigo-500/9 text-indigo-300 border border-indigo-500/16 rounded-[6px] text-[0.68rem] font-semibold px-2 py-0.5 m-0.5">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Languages */}
      {p.target_languages.length > 0 && (
        <div>
          <p className="text-[0.6rem] font-extrabold tracking-[0.16em] uppercase text-slate-600 mb-2">💻 Languages</p>
          <div className="flex flex-wrap">
            {p.target_languages.map((l) => (
              <span key={l} className="inline-block bg-purple-500/12 text-purple-300 border border-purple-500/22 rounded-[6px] text-[0.68rem] font-semibold px-2 py-0.5 m-0.5">
                {l}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Company format */}
      {intel?.interview_rounds && intel.interview_rounds.length > 0 && (
        <div>
          <p className="text-[0.6rem] font-extrabold tracking-[0.16em] uppercase text-slate-600 mb-2">📋 Interview Format</p>
          <div className="flex flex-wrap">
            {intel.interview_rounds.map((r) => (
              <span key={r} className="inline-block bg-emerald-500/8 text-emerald-300 border border-emerald-500/16 rounded-[6px] text-[0.68rem] font-semibold px-2 py-0.5 m-0.5">
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Difficulty */}
      {intel?.difficulty_notes && (
        <div>
          <p className="text-[0.6rem] font-extrabold tracking-[0.16em] uppercase text-slate-600 mb-2">📊 Difficulty</p>
          <p className="text-[0.76rem] text-slate-500 leading-relaxed border-l-2 border-indigo-500/35 pl-3">
            {intel.difficulty_notes.slice(0, 220)}{intel.difficulty_notes.length > 220 ? "…" : ""}
          </p>
        </div>
      )}

      <div className="mt-auto">
        <button
          onClick={onBack}
          className="w-full py-2 rounded-[10px] text-[0.82rem] text-slate-500 border border-[rgba(45,45,74,0.6)] hover:border-indigo-500/40 hover:text-indigo-300 transition-all"
        >
          ← Back to Analysis
        </button>
      </div>
    </aside>
  );
}

// ─── Progress Tracker ─────────────────────────────────────────────────────────

function ProgressTracker({ completed, isIntro, isDone }: { completed: number; isIntro: boolean; isDone: boolean }) {
  const steps: Array<[string, "done" | "active" | "pending"]> = [];
  steps.push(["Intro", isIntro ? "active" : "done"]);
  for (let i = 1; i <= completed; i++) steps.push([`Q${i}`, "done"]);
  if (!isIntro && !isDone) steps.push([`Q${completed + 1}`, "active"]);
  steps.push(isDone ? ["Done", "active"] : ["…", "pending"]);

  return (
    <div className="flex items-center gap-0 mb-6 px-4 py-3 bg-white/[0.02] border border-[rgba(45,45,74,0.4)] rounded-[14px] overflow-x-auto">
      {steps.map(([label, state], idx) => (
        <div key={idx} className="flex items-center gap-0 flex-shrink-0">
          <div className="flex items-center gap-2 flex-shrink-0">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-[0.7rem] font-extrabold transition-all ${
                state === "done"
                  ? "bg-emerald-500/20 border-2 border-emerald-500/40 text-emerald-300"
                  : state === "active"
                  ? "border-2 border-indigo-500/60 text-white"
                  : "bg-white/[0.04] border-2 border-[rgba(45,45,74,0.6)] text-slate-600"
              }`}
              style={
                state === "active"
                  ? { background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 12px rgba(99,102,241,0.5)" }
                  : undefined
              }
            >
              {state === "done" ? "✓" : state === "active" ? "●" : "○"}
            </div>
            <span
              className={`text-[0.72rem] font-semibold ${
                state === "done" ? "text-emerald-400" : state === "active" ? "text-slate-200" : "text-slate-600"
              }`}
            >
              {label}
            </span>
          </div>
          {idx < steps.length - 1 && (
            <div
              className={`h-0.5 w-8 mx-2 rounded flex-shrink-0 ${state === "done" ? "bg-emerald-500/35" : "bg-[rgba(45,45,74,0.5)]"}`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Question Card ────────────────────────────────────────────────────────────

function QuestionCard({
  questionText,
  isLoadingNext,
  difficulty,
  link,
  tags,
  contentHtml,
  company,
  role,
}: {
  questionText: string | null;
  isLoadingNext: boolean;
  difficulty: string;
  link: string | null;
  tags: string[];
  contentHtml: string | null;
  company: string;
  role: string;
}) {
  if (isLoadingNext) {
    return (
      <div className="bg-gradient-to-br from-[rgba(28,28,44,0.95)] to-[rgba(20,20,38,0.95)] border border-[rgba(45,45,74,0.55)] rounded-[18px] p-10 flex items-center justify-center gap-3 text-slate-500 text-[0.9rem]">
        <span className="inline-block w-5 h-5 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin flex-shrink-0" />
        Loading next question…
      </div>
    );
  }

  if (!questionText) {
    return (
      <div className="bg-gradient-to-br from-[rgba(28,28,44,0.95)] to-[rgba(20,20,38,0.95)] border border-[rgba(45,45,74,0.55)] rounded-[18px] p-10 text-center">
        <div className="text-[2.2rem] mb-3">🏁</div>
        <p className="text-indigo-400 font-bold text-[1rem] mb-1">All questions completed!</p>
        <p className="text-slate-600 text-[0.85rem]">Generate your final evaluation below.</p>
      </div>
    );
  }

  if (questionText === "Introduction") {
    return (
      <div className="bg-gradient-to-br from-[rgba(28,28,44,0.95)] to-[rgba(20,20,38,0.95)] border border-[rgba(45,45,74,0.55)] rounded-[18px] p-8">
        <p className="text-[0.64rem] font-extrabold tracking-[0.17em] uppercase text-indigo-500 mb-4">👋 Welcome to Internly</p>
        <h2 className="text-slate-200 text-[1.3rem] font-extrabold mb-5">Candidate Introduction</h2>
        <div className="text-slate-300 text-[0.89rem] leading-[1.8] space-y-3">
          <p>Welcome to your interview at <strong className="text-slate-100">{company}</strong> for the <strong className="text-slate-100">{role}</strong> position!</p>
          <p>Before the technical challenge, please take a moment to introduce yourself in the chat on the right.</p>
          <p className="font-semibold text-slate-200">Suggested topics to cover:</p>
          <ul className="list-disc pl-5 space-y-1 text-slate-400">
            <li>Your professional background and technical stack</li>
            <li>Key projects you have built recently</li>
            <li>Your interest in this target role</li>
          </ul>
        </div>
        <p className="text-slate-600 text-[0.79rem] mt-6 pt-4 border-t border-[rgba(30,30,50,0.9)] italic leading-relaxed">
          💬 Respond to the interviewer&apos;s greeting in the chat panel on the right.
        </p>
      </div>
    );
  }

  const diffCls = DIFF_CLS[(difficulty || "").toLowerCase()] ?? DIFF_CLS.medium;

  return (
    <div className="bg-gradient-to-br from-[rgba(28,28,44,0.95)] to-[rgba(20,20,38,0.95)] border border-[rgba(45,45,74,0.55)] rounded-[18px] p-8">
      <p className="text-[0.64rem] font-extrabold tracking-[0.17em] uppercase text-indigo-500 mb-4">🧩 DSA Challenge</p>
      <div className="flex items-center gap-2.5 mb-4 flex-wrap">
        <h2 className="text-slate-200 text-[1.3rem] font-extrabold">{questionText}</h2>
        {difficulty && (
          <span className={`text-[0.68rem] font-bold px-2.5 py-1 rounded-[7px] ${diffCls}`}>
            {difficulty}
          </span>
        )}
        {link && (
          <a
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-orange-400 text-[0.75rem] font-bold bg-orange-500/9 border border-orange-500/22 rounded-[7px] px-2.5 py-1 hover:bg-orange-500/18 transition-colors"
          >
            🔗 LeetCode
          </a>
        )}
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap mb-4">
          {tags.map((t) => (
            <span key={t} className="inline-block bg-indigo-500/9 text-indigo-400 border border-indigo-500/18 rounded-[5px] text-[0.67rem] font-semibold px-2 py-0.5 mr-1.5 mb-1.5">
              {t}
            </span>
          ))}
        </div>
      )}

      {contentHtml ? (
        <div
          className="text-slate-300 text-[0.89rem] leading-[1.8] lc-content mt-3"
          dangerouslySetInnerHTML={{ __html: contentHtml }}
          style={{ overflowY: "auto", maxHeight: "380px" }}
        />
      ) : contentHtml === null ? (
        <div className="flex items-center gap-2 text-slate-600 text-[0.84rem] mt-3">
          <span className="inline-block w-4 h-4 border-2 border-slate-700 border-t-indigo-500 rounded-full animate-spin" />
          Loading problem statement…
        </div>
      ) : (
        <p className="text-slate-600 text-[0.84rem] italic mt-3">
          Full problem statement could not be loaded. Open the LeetCode link above, read the problem, then describe your approach here.
        </p>
      )}

      <p className="text-slate-600 text-[0.79rem] mt-5 pt-4 border-t border-[rgba(30,30,50,0.9)] italic leading-relaxed">
        💬 Explain your approach, data structures, and time/space complexity.
        Type <em>&quot;move on&quot;</em> or <em>&quot;skip&quot;</em> to advance to the next question.
      </p>
    </div>
  );
}

// ─── Message formatter (minimal markdown → HTML) ─────────────────────────────

function formatMessage(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    // **bold**
    .replace(/\*\*(.+?)\*\*/g, "<strong class='text-slate-100 font-semibold'>$1</strong>")
    // newlines → paragraphs
    .split(/\n\n+/)
    .map((para) => `<p class="mb-2 last:mb-0">${para.replace(/\n/g, "<br/>")}</p>`)
    .join("");
}

// ─── Chat Panel ───────────────────────────────────────────────────────────────

function ChatPanel({
  messages,
  questionText,
  onSend,
  loading,
}: {
  messages: ChatMessage[];
  questionText: string | null;
  onSend: (text: string) => void;
  loading: boolean;
}) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSend() {
    const t = input.trim();
    if (!t || loading) return;
    setInput("");
    onSend(t);
  }

  return (
    <div className="flex flex-col h-full">
      <p className="text-[0.64rem] font-extrabold tracking-[0.17em] uppercase text-indigo-500 mb-4">💬 Interview Chat</p>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-0" style={{ maxHeight: "calc(100vh - 380px)" }}>
        {messages.map((msg, i) => {
          if (msg.role === "user") {
            return (
              <div key={i} className="flex justify-end">
                <div
                  className="max-w-[78%] text-white rounded-[18px_18px_4px_18px] px-4 py-3 text-[0.88rem] leading-relaxed font-medium"
                  style={{
                    background: "linear-gradient(135deg,#6366f1,#7c3aed)",
                    boxShadow: "0 4px 20px rgba(99,102,241,0.28)",
                  }}
                >
                  {msg.text}
                </div>
              </div>
            );
          }
          const isLast = i === messages.length - 1;
          const badgeCls = BADGE_CLS[msg.type ?? "followup"] ?? BADGE_CLS.followup;
          return (
            <div key={i} className={`flex justify-start items-start gap-2.5 ${isLast && msg.animateIn ? "msg-slide-in" : ""}`}>
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-[0.78rem] flex-shrink-0 mt-1"
                style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 10px rgba(99,102,241,0.35)" }}
              >
                🤖
              </div>
              <div className="max-w-[80%]">
                <span className={`inline-block text-[0.6rem] font-extrabold uppercase tracking-widest px-2 py-0.5 rounded-[5px] mb-1.5 ${badgeCls}`}>
                  Company Interviewer
                </span>
                <div
                  className={`bg-[rgba(28,28,44,0.95)] border border-[rgba(45,45,74,0.5)] text-slate-300 rounded-[4px_18px_18px_18px] px-4 py-3 text-[0.88rem] leading-[1.7] ${isLast && msg.animateIn ? "cursor-fade" : ""}`}
                  dangerouslySetInnerHTML={{ __html: formatMessage(msg.text) }}
                />
              </div>
            </div>
          );
        })}
        {loading && (
          <div className="flex justify-start items-start gap-2.5">
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-[0.78rem] flex-shrink-0 mt-1"
              style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }}
            >
              🤖
            </div>
            <div className="bg-[rgba(28,28,44,0.95)] border border-[rgba(45,45,74,0.5)] rounded-[4px_18px_18px_18px] px-4 py-3">
              <div className="flex gap-1.5 items-center">
                {[0, 150, 300].map((d) => (
                  <div
                    key={d}
                    className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce"
                    style={{ animationDelay: `${d}ms` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      {questionText && (
        <div className="mt-4 flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Describe your approach or pseudocode…"
            rows={3}
            disabled={loading}
            className="flex-1 bg-[rgba(20,20,38,0.9)] border border-[rgba(45,45,74,0.7)] rounded-[14px] text-slate-200 text-[0.9rem] px-4 py-3 outline-none focus:border-indigo-500/50 focus:ring-2 focus:ring-indigo-500/10 placeholder-slate-700 resize-none transition-all disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="self-end px-5 py-3 rounded-[12px] font-bold text-white text-[0.88rem] disabled:opacity-40 hover:-translate-y-0.5 transition-all"
            style={{ background: "linear-gradient(135deg,#6366f1,#7c3aed)", boxShadow: "0 4px 20px rgba(99,102,241,0.35)" }}
          >
            Send
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Evaluation ───────────────────────────────────────────────────────────────

const OUTCOME_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  solved:  { label: "Solved",  color: "bg-emerald-500/14 text-emerald-300 border-emerald-500/25", icon: "✅" },
  partial: { label: "Partial", color: "bg-amber-500/12 text-amber-300 border-amber-500/25",       icon: "⚡" },
  guided:  { label: "Guided",  color: "bg-red-500/12 text-red-300 border-red-500/22",             icon: "📖" },
  skipped: { label: "Skipped", color: "bg-slate-500/12 text-slate-400 border-slate-500/22",       icon: "⏭" },
};

const DIFF_COLORS: Record<string, string> = {
  easy:   "bg-emerald-500/14 text-emerald-300 border border-emerald-500/25",
  medium: "bg-amber-500/12 text-amber-300 border border-amber-500/25",
  hard:   "bg-red-500/12 text-red-300 border border-red-500/22",
};

function QuestionBreakdownCard({ qb }: { qb: QuestionBreakdown }) {
  const outcome = OUTCOME_CONFIG[qb.outcome] ?? OUTCOME_CONFIG.partial;
  const diffCls = DIFF_COLORS[(qb.difficulty || "").toLowerCase()] ?? DIFF_COLORS.medium;
  return (
    <div className="bg-[rgba(14,14,28,0.7)] border border-[rgba(45,45,74,0.4)] rounded-[12px] p-4">
      <div className="flex items-center gap-2 flex-wrap mb-2">
        <span className="text-slate-200 text-[0.88rem] font-semibold">{qb.question}</span>
        {qb.difficulty && (
          <span className={`text-[0.64rem] font-bold px-2 py-0.5 rounded-[5px] ${diffCls}`}>
            {qb.difficulty}
          </span>
        )}
        <span className={`text-[0.64rem] font-bold px-2 py-0.5 rounded-[5px] border ${outcome.color}`}>
          {outcome.icon} {outcome.label}
        </span>
        {qb.hints_given > 0 && (
          <span className="text-[0.64rem] text-slate-600 font-semibold">
            {qb.hints_given} hint{qb.hints_given !== 1 ? "s" : ""}
          </span>
        )}
      </div>
      {qb.notes && (
        <p className="text-slate-400 text-[0.82rem] leading-relaxed">{qb.notes}</p>
      )}
    </div>
  );
}

function EvalCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-[rgba(20,20,38,0.8)] border border-[rgba(45,45,74,0.45)] rounded-[14px] p-5 ${className}`}>
      {children}
    </div>
  );
}

function EvalLabel({ children, color = "text-slate-600" }: { children: React.ReactNode; color?: string }) {
  return (
    <h4 className={`text-[0.64rem] font-extrabold uppercase tracking-widest mb-3 ${color}`}>
      {children}
    </h4>
  );
}

function EvaluationPanel({
  ev,
  alignmentSignals,
  skillGaps,
}: {
  ev: EvaluationResult;
  alignmentSignals: string[];
  skillGaps: string[];
}) {
  return (
    <div className="space-y-5">
      <p className="text-[0.64rem] font-extrabold tracking-[0.17em] uppercase text-indigo-500">📊 Final Report</p>

      {/* Score cards */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { score: ev.technical_score, label: "Technical", sub: "Problem solving" },
          { score: ev.communication_score, label: "Communication", sub: "Clarity & reasoning" },
          { score: ev.role_fit_score, label: "Role Fit", sub: "Resume + performance" },
        ].map(({ score, label, sub }) => (
          <div key={label} className="bg-gradient-to-br from-[rgba(28,28,44,0.95)] to-[rgba(20,20,38,0.95)] border border-[rgba(45,45,74,0.5)] rounded-[16px] p-5 text-center">
            <p
              className="text-[3rem] font-black leading-none mb-1"
              style={{
                background: "linear-gradient(135deg,#6366f1,#8b5cf6)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              {score}<span className="text-[1rem] text-slate-600">/10</span>
            </p>
            <p className="text-slate-200 text-[0.78rem] font-bold uppercase tracking-wider">{label}</p>
            <p className="text-slate-600 text-[0.68rem] mt-0.5">{sub}</p>
          </div>
        ))}
      </div>

      {/* Two panels: Resume Evaluation | Interview Performance */}
      <div className="grid grid-cols-2 gap-4">

        {/* LEFT — Resume Evaluation */}
        <div className="space-y-3">
          <p className="text-[0.62rem] font-extrabold tracking-[0.16em] uppercase text-slate-500 pb-1 border-b border-white/5">
            📄 Resume Evaluation
          </p>

          {/* JD Alignment */}
          {alignmentSignals.length > 0 && (
            <EvalCard className="border-emerald-500/15!">
              <EvalLabel color="text-emerald-600">✦ JD Alignment Strengths</EvalLabel>
              <div className="space-y-1.5">
                {alignmentSignals.map((s, i) => (
                  <div key={i} className="flex items-start gap-2 text-emerald-100 text-[0.83rem] leading-relaxed">
                    <span className="text-emerald-400 text-[0.7rem] mt-0.5 flex-shrink-0">✦</span>
                    {s}
                  </div>
                ))}
              </div>
            </EvalCard>
          )}

          {/* Skill Gaps */}
          {skillGaps.length > 0 && (
            <EvalCard className="border-red-500/12!">
              <EvalLabel color="text-red-500">⚠ Skill Gaps vs JD</EvalLabel>
              <div className="space-y-1.5">
                {skillGaps.map((g, i) => (
                  <div key={i} className="bg-red-500/7 border border-red-500/14 rounded-[8px] px-3 py-1.5 text-red-300 text-[0.83rem]">
                    {g}
                  </div>
                ))}
              </div>
            </EvalCard>
          )}

          {/* Strengths */}
          {ev.strengths.length > 0 && (
            <EvalCard>
              <EvalLabel>💪 Strengths</EvalLabel>
              <div className="space-y-1.5">
                {ev.strengths.map((s, i) => (
                  <p key={i} className="text-slate-300 text-[0.85rem] leading-snug">✅ {s}</p>
                ))}
              </div>
            </EvalCard>
          )}
        </div>

        {/* RIGHT — Interview Performance */}
        <div className="space-y-3">
          <p className="text-[0.62rem] font-extrabold tracking-[0.16em] uppercase text-slate-500 pb-1 border-b border-white/5">
            🧩 Interview Performance
          </p>

          {/* Per-question breakdown */}
          {ev.question_breakdown.length > 0 && (
            <EvalCard>
              <EvalLabel>📋 Question Breakdown</EvalLabel>
              <div className="space-y-2">
                {ev.question_breakdown.map((qb, i) => (
                  <QuestionBreakdownCard key={i} qb={qb} />
                ))}
              </div>
            </EvalCard>
          )}

          {/* Areas to improve */}
          {ev.weaknesses.length > 0 && (
            <EvalCard>
              <EvalLabel>🔧 Areas to Improve</EvalLabel>
              <div className="space-y-1.5">
                {ev.weaknesses.map((w, i) => (
                  <p key={i} className="text-slate-300 text-[0.85rem] leading-snug">⚠ {w}</p>
                ))}
              </div>
            </EvalCard>
          )}
        </div>
      </div>

      {/* Recommendation + detailed feedback — full width */}
      <EvalCard>
        <EvalLabel>📝 Recommendation</EvalLabel>
        <p className="text-slate-100 text-[0.95rem] font-bold mb-3 tracking-tight">{ev.recommendation}</p>
        <div
          className="text-slate-400 text-[0.86rem] leading-[1.8]"
          dangerouslySetInnerHTML={{ __html: formatMessage(ev.detailed_feedback) }}
        />
      </EvalCard>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function InterviewPage() {
  const router = useRouter();

  // Load session state from sessionStorage
  const [analyseResult, setAnalyseResult] = useState<AnalyseResult | null>(null);
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");

  const [sessionId, setSessionId] = useState<number | null>(null);
  const [candidateId, setCandidateId] = useState<number | null>(null);
  const [usedQuestionIds, setUsedQuestionIds] = useState<number[]>([]);
  const [questionsCompleted, setQuestionsCompleted] = useState(0);

  const [activeQuestionText, setActiveQuestionText] = useState<string | null>(null);
  const [activeQuestionIndex, setActiveQuestionIndex] = useState<number>(0);
  const [activeQuestionLink, setActiveQuestionLink] = useState<string | null>(null);
  const [activeQuestionDifficulty, setActiveQuestionDifficulty] = useState("");
  const [activeQuestionTags, setActiveQuestionTags] = useState<string[]>([]);
  const [lcContentHtml, setLcContentHtml] = useState<string | null>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [turnLoading, setTurnLoading] = useState(false);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [evalLoading, setEvalLoading] = useState(false);
  const [initDone, setInitDone] = useState(false);
  const [fetchingNext, setFetchingNext] = useState(false);

  // Load result from sessionStorage
  useEffect(() => {
    const raw = sessionStorage.getItem("internly_result");
    const c = sessionStorage.getItem("internly_company") ?? "";
    const r = sessionStorage.getItem("internly_role") ?? "";
    if (!raw) { router.push("/"); return; }
    try {
      const parsed: AnalyseResult = JSON.parse(raw);
      setAnalyseResult(parsed);
      setCandidateId(parsed.candidate_id);
      setCompany(c);
      setRole(r);
    } catch {
      router.push("/");
    }
  }, [router]);

  // Init interview session once candidate_id is known
  useEffect(() => {
    if (!candidateId || initDone) return;
    setInitDone(true);

    startInterview(candidateId).then((res) => {
      setSessionId(res.session_id);
      setActiveQuestionText("Introduction");
      setActiveQuestionIndex(0);
      setLcContentHtml("");
      const introMsgs: ChatMessage[] = res.intro_turns.map((t) => ({
        role: t.role === "candidate" ? "user" : "agent",
        text: t.text,
        type: t.type ?? "followup",
      }));
      setMessages(introMsgs);
    }).catch(() => router.push("/"));
  }, [candidateId, initDone, router]);

  // Fetch LeetCode content when question link changes
  useEffect(() => {
    if (!activeQuestionLink) { setLcContentHtml(""); return; }
    setLcContentHtml(null); // loading
    fetchLeetCode(activeQuestionLink).then((lc: LeetCodeResult) => {
      if (lc.found) {
        setLcContentHtml(lc.content_html ?? "");
        setActiveQuestionTags(lc.topic_tags ?? []);
        if (lc.difficulty) setActiveQuestionDifficulty(lc.difficulty);
      } else {
        setLcContentHtml("");
      }
    });
  }, [activeQuestionLink]);

  const loadNextQuestion = useCallback(async () => {
    if (!sessionId || fetchingNext) return;
    setFetchingNext(true);
    try {
      const next = await fetchNextQuestion(sessionId, company, usedQuestionIds);
      if (next) {
        setUsedQuestionIds(next.used_question_ids);
        setActiveQuestionIndex(next.question_index);
        setActiveQuestionText(next.question_title);
        setActiveQuestionLink(next.question_link);
        setActiveQuestionDifficulty(next.difficulty);
        setActiveQuestionTags([]);
        setLcContentHtml(null);
        setMessages((prev) => [
          ...prev,
          {
            role: "agent",
            text: `Here is our next technical question: **${next.question_title}**. Please review the problem description on the left, then outline your approach.`,
            type: "followup",
            animateIn: true,
          },
        ]);
      } else {
        setActiveQuestionText(null);
      }
    } finally {
      setFetchingNext(false);
    }
  }, [sessionId, company, usedQuestionIds, fetchingNext]);

  async function handleSend(text: string) {
    if (!sessionId || candidateId === null) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setTurnLoading(true);
    try {
      const action: TurnResult = await submitTurn(
        sessionId,
        activeQuestionIndex,
        text,
        candidateId,
        company,
        role
      );
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: action.text, type: action.type, animateIn: true },
      ]);

      if (action.type === "accept" || action.type === "guide") {
        if (activeQuestionText !== "Introduction") {
          setQuestionsCompleted((n) => n + 1);
        }
        setActiveQuestionText(null);
        // Load next question after a short pause
        setTimeout(() => loadNextQuestion(), 800);
      }
    } catch (err: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: err instanceof Error ? `Error: ${err.message}` : "Something went wrong.", type: "guide" },
      ]);
    } finally {
      setTurnLoading(false);
    }
  }

  async function handleEvaluate() {
    if (!sessionId || candidateId === null) return;
    setEvalLoading(true);
    try {
      const ev = await generateEvaluation(sessionId, candidateId);
      setEvaluation(ev);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Evaluation failed.");
    } finally {
      setEvalLoading(false);
    }
  }

  if (!analyseResult) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="inline-block w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
      </div>
    );
  }

  const isIntro = activeQuestionText === "Introduction";
  const isDone = activeQuestionText === null && !fetchingNext;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar result={analyseResult} company={company} role={role} onBack={() => router.push("/")} />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <div className="flex items-center justify-between px-8 py-4 border-b border-[rgba(30,30,50,0.9)]">
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-[9px] flex items-center justify-center text-[1rem] flex-shrink-0"
              style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 16px rgba(99,102,241,0.4)" }}
            >
              ⚡
            </div>
            <span
              className="text-[1.05rem] font-black tracking-tight"
              style={{
                background: "linear-gradient(135deg,#e0e7ff,#a5b4fc)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              Internly
            </span>
          </div>
          <div className="flex items-center gap-2 text-slate-600 text-[0.8rem]">
            Interviewing for
            <span className="bg-indigo-500/10 text-indigo-300 border border-indigo-500/18 rounded-[6px] px-2.5 py-0.5 font-semibold text-[0.78rem]">{role}</span>
            at
            <span className="bg-indigo-500/10 text-indigo-300 border border-indigo-500/18 rounded-[6px] px-2.5 py-0.5 font-semibold text-[0.78rem]">{company}</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-8 py-6">
          <ProgressTracker completed={questionsCompleted} isIntro={isIntro} isDone={isDone && !fetchingNext} />

          {/* Two-column layout — question + chat only */}
          <div className="grid grid-cols-[5fr_4fr] gap-6 items-start">
            {/* Left: Question */}
            <QuestionCard
              questionText={activeQuestionText}
              isLoadingNext={fetchingNext}
              difficulty={activeQuestionDifficulty}
              link={activeQuestionLink}
              tags={activeQuestionTags}
              contentHtml={lcContentHtml}
              company={company}
              role={role}
            />

            {/* Right: Chat */}
            <ChatPanel
              messages={messages}
              questionText={activeQuestionText}
              onSend={handleSend}
              loading={turnLoading || fetchingNext}
            />
          </div>

          {/* Full-width evaluation section — only shown when interview is complete */}
          {(isDone || evaluation) && (
            <div className="border-t border-[rgba(30,30,50,0.9)] mt-6 pt-6">
              {!evaluation ? (
                <>
                  <p className="text-center text-slate-400 text-[0.88rem] mb-4">
                    🎉 All questions completed — you can now generate your final evaluation report.
                  </p>
                  <button
                    onClick={handleEvaluate}
                    disabled={evalLoading}
                    className="w-full py-3.5 rounded-[12px] font-bold text-white text-[0.95rem] disabled:opacity-50 hover:-translate-y-0.5 transition-all"
                    style={{
                      background: "linear-gradient(135deg,#6366f1,#7c3aed)",
                      boxShadow: "0 4px 22px rgba(99,102,241,0.4)",
                    }}
                  >
                    {evalLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Evaluating your performance…
                      </span>
                    ) : (
                      "📊 Generate Final Evaluation"
                    )}
                  </button>
                </>
              ) : (
                <EvaluationPanel
                  ev={evaluation}
                  alignmentSignals={analyseResult?.resume_profile.alignment_signals ?? []}
                  skillGaps={analyseResult?.resume_profile.skill_gaps ?? []}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
