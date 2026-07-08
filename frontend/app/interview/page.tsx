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
import {
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  Circle,
  ExternalLink,
  Flag,
  Loader2,
  MessageSquare,
  Puzzle,
  Send,
  Wrench,
  BarChart3,
  FileText,
  Dumbbell,
  AlertTriangle,
  ClipboardList,
  Laptop,
  Wrench as WrenchIcon,
  User,
  PanelRightOpen,
  X,
} from "lucide-react";
import {
  BrandMark,
  BrandTitle,
  GlassCard,
  Eyebrow,
  PrimaryCta,
  SecondaryBtn,
} from "@/components/internly-ui";
import { formatDisplayLabel } from "@/lib/format";
import { formatRichText } from "@/lib/format-message";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ChatMessage {
  role: "user" | "agent";
  text: string;
  type?: string;
  animateIn?: boolean;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const DIFF_CLS: Record<string, string> = {
  easy: "bg-emerald-950/60 text-emerald-300 border border-emerald-800",
  medium: "bg-amber-950/60 text-amber-300 border border-amber-800",
  hard: "bg-red-950/60 text-red-300 border border-red-800",
};

const AGENT_BADGE_CLS =
  "bg-emerald-950/50 text-emerald-300 border border-emerald-800";

function formatCompanyChatLabel(company: string): string {
  return formatDisplayLabel(company) || "Interviewer";
}

// ─── Profile drawer (slides in from the right) ────────────────────────────────

function ProfileDrawer({
  result,
  company,
  role,
  open,
  onClose,
  onBack,
}: {
  result: AnalyseResult;
  company: string;
  role: string;
  open: boolean;
  onClose: () => void;
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
    <>
      {/* Mobile backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/50 backdrop-blur-[2px] transition-opacity duration-300 lg:hidden ${
          open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
        aria-hidden={!open}
      />

      <aside
        id="profile-drawer"
        className={`profile-drawer fixed lg:relative right-0 top-0 z-50 lg:z-auto h-full flex-shrink-0 border-l border-border bg-card/95 backdrop-blur-md flex flex-col overflow-hidden transition-[width,transform] duration-300 ease-out ${
          open
            ? "w-[min(300px,88vw)] translate-x-0"
            : "w-0 translate-x-full lg:translate-x-0 border-l-0"
        }`}
        aria-hidden={!open}
      >
        <div className="w-[min(300px,88vw)] h-full flex flex-col gap-5 px-5 py-6 overflow-y-auto">
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <div className="flex items-center gap-2">
              <User className="w-4 h-4 text-primary" />
              <span className="text-[0.72rem] font-extrabold uppercase tracking-widest text-primary">
                Your Profile
              </span>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
              aria-label="Close profile panel"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="bg-secondary border border-border rounded-[12px] px-3.5 py-3">
            <p className="text-[0.72rem] text-primary font-bold tracking-wide mb-0.5">{formatDisplayLabel(role)}</p>
            <p className="text-[0.9rem] text-foreground font-extrabold tracking-tight">{formatDisplayLabel(company)}</p>
          </div>

          <div className="grid grid-cols-3 gap-1.5">
            {[
              { val: expText, lbl: "Exp" },
              { val: p.skills.length, lbl: "Skills" },
              { val: p.projects.length, lbl: "Projects" },
            ].map(({ val, lbl }) => (
              <div key={lbl} className="bg-muted/80 border border-border rounded-[10px] py-2.5 text-center">
                <p className="text-[1.05rem] font-extrabold text-foreground">{val}</p>
                <p className="text-[0.6rem] text-muted-foreground font-semibold uppercase tracking-wider mt-0.5">{lbl}</p>
              </div>
            ))}
          </div>

          {p.skills.length > 0 && (
            <div>
              <Eyebrow className="flex items-center gap-1.5 mb-2">
                <WrenchIcon className="w-3 h-3" /> Skills
              </Eyebrow>
              <div className="flex flex-wrap">
                {p.skills.slice(0, 12).map((s) => (
                  <span key={s} className="inline-block bg-secondary text-primary border border-border rounded-[6px] text-[0.68rem] font-semibold px-2 py-0.5 m-0.5">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {p.target_languages.length > 0 && (
            <div>
              <Eyebrow className="flex items-center gap-1.5 mb-2">
                <Laptop className="w-3 h-3" /> Languages
              </Eyebrow>
              <div className="flex flex-wrap">
                {p.target_languages.map((l) => (
                  <span key={l} className="inline-block bg-violet-950/40 text-violet-300 border border-violet-800 rounded-[6px] text-[0.68rem] font-semibold px-2 py-0.5 m-0.5">
                    {l}
                  </span>
                ))}
              </div>
            </div>
          )}

          {intel?.interview_rounds && intel.interview_rounds.length > 0 && (
            <div>
              <Eyebrow className="flex items-center gap-1.5 mb-2">
                <ClipboardList className="w-3 h-3" /> Interview Format
              </Eyebrow>
              <div className="flex flex-wrap">
                {intel.interview_rounds.map((r) => (
                  <span key={r} className="inline-block bg-emerald-950/40 text-emerald-300 border border-emerald-800 rounded-[6px] text-[0.68rem] font-semibold px-2 py-0.5 m-0.5">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}

          {intel?.difficulty_notes && (
            <div>
              <Eyebrow className="mb-2">Difficulty</Eyebrow>
              <p className="text-[0.76rem] text-muted-foreground leading-relaxed border-l-2 border-primary/50 pl-3">
                {intel.difficulty_notes.slice(0, 220)}{intel.difficulty_notes.length > 220 ? "…" : ""}
              </p>
            </div>
          )}

          <div className="mt-auto pt-2">
            <SecondaryBtn onClick={onBack} className="flex items-center justify-center gap-1.5 w-full">
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Analysis
            </SecondaryBtn>
          </div>
        </div>
      </aside>
    </>
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
    <div className="flex items-center gap-0 mb-6 px-4 py-3 glass-card overflow-x-auto">
      {steps.map(([label, state], idx) => (
        <div key={idx} className="flex items-center gap-0 flex-shrink-0">
          <div className="flex items-center gap-2 flex-shrink-0">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-[0.7rem] font-extrabold transition-all duration-200 ${
                state === "done"
                  ? "bg-emerald-950/60 border-2 border-emerald-600 text-emerald-300"
                  : state === "active"
                  ? "border-2 border-primary text-white bg-primary shadow-md"
                  : "bg-muted border-2 border-border text-muted-foreground"
              }`}
            >
              {state === "done" ? <Check className="w-3.5 h-3.5" /> : state === "active" ? <Circle className="w-2 h-2 fill-current" /> : <Circle className="w-3 h-3" />}
            </div>
            <span
              className={`text-[0.72rem] font-semibold ${
                state === "done" ? "text-emerald-400" : state === "active" ? "text-foreground" : "text-muted-foreground"
              }`}
            >
              {label}
            </span>
          </div>
          {idx < steps.length - 1 && (
            <div
              className={`h-0.5 w-8 mx-2 rounded flex-shrink-0 ${state === "done" ? "bg-emerald-700" : "bg-border"}`}
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
  fetchFailed,
  company,
  role,
}: {
  questionText: string | null;
  isLoadingNext: boolean;
  difficulty: string;
  link: string | null;
  tags: string[];
  contentHtml: string | null;
  fetchFailed?: boolean;
  company: string;
  role: string;
}) {
  if (isLoadingNext) {
    return (
      <GlassCard className="p-10 flex items-center justify-center gap-3 text-muted-foreground text-[0.9rem]">
        <Loader2 className="w-5 h-5 animate-spin text-primary" />
        Loading next question…
      </GlassCard>
    );
  }

  if (!questionText) {
    return (
      <GlassCard className="p-10 text-center">
        <Flag className="w-10 h-10 text-primary mx-auto mb-3" />
        <p className="text-primary font-bold text-[1rem] mb-1">All questions completed!</p>
        <p className="text-muted-foreground text-[0.85rem]">Generate your final evaluation below.</p>
      </GlassCard>
    );
  }

  if (questionText === "Introduction") {
    return (
      <GlassCard className="p-8">
        <Eyebrow>Welcome to Internly</Eyebrow>
        <h2 className="text-foreground text-[1.3rem] font-extrabold mb-5">Candidate Introduction</h2>
        <div className="text-muted-foreground text-[0.89rem] leading-[1.8] space-y-3">
          <p>Welcome to your interview at <strong className="text-foreground">{formatDisplayLabel(company)}</strong> for the <strong className="text-foreground">{formatDisplayLabel(role)}</strong> position!</p>
          <p>Before the technical challenge, please take a moment to introduce yourself in the chat on the right.</p>
          <p className="font-semibold text-foreground">Suggested topics to cover:</p>
          <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
            <li>Your professional background and technical stack</li>
            <li>Key projects you have built recently</li>
            <li>Your interest in this target role</li>
          </ul>
        </div>
        <p className="text-muted-foreground text-[0.79rem] mt-6 pt-4 border-t border-border italic leading-relaxed flex items-center gap-1.5">
          <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
          Respond in the chat on the right. The LeetCode problem will appear here once you finish your introduction.
        </p>
      </GlassCard>
    );
  }

  const diffCls = DIFF_CLS[(difficulty || "").toLowerCase()] ?? DIFF_CLS.medium;

  return (
    <GlassCard className="p-8 h-full min-h-[420px] flex flex-col">
      <Eyebrow className="flex items-center gap-1.5">
        <Puzzle className="w-3 h-3" /> DSA Challenge
      </Eyebrow>
      <div className="flex items-center gap-2.5 mb-4 flex-wrap">
        <h2 className="text-foreground text-[1.3rem] font-extrabold">{questionText}</h2>
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
            className="inline-flex items-center gap-1.5 text-orange-300 text-[0.75rem] font-bold bg-orange-950/50 border border-orange-800 rounded-[7px] px-2.5 py-1 hover:bg-orange-900/50 transition-colors duration-200 cursor-pointer"
          >
            <ExternalLink className="w-3 h-3" />
            LeetCode
          </a>
        )}
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap mb-4">
          {tags.map((t) => (
            <span key={t} className="inline-block bg-secondary text-primary border border-border rounded-[5px] text-[0.67rem] font-semibold px-2 py-0.5 mr-1.5 mb-1.5">
              {t}
            </span>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-y-auto min-h-0">
      {contentHtml ? (
        <div
          className="text-muted-foreground text-[0.89rem] leading-[1.8] lc-content mt-3"
          dangerouslySetInnerHTML={{ __html: contentHtml }}
        />
      ) : contentHtml === null ? (
        <div className="flex items-center gap-2 text-muted-foreground text-[0.84rem] mt-3">
          <Loader2 className="w-4 h-4 animate-spin text-primary" />
          Loading problem statement from LeetCode…
        </div>
      ) : link ? (
        <div className="mt-3 space-y-3">
          <p className="text-[#ececf4] text-[0.84rem]">
            {fetchFailed
              ? "Could not load the problem statement from LeetCode. Use the link below or ensure the backend is running."
              : "Could not load the full statement automatically."}
          </p>
          <a
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-primary font-semibold text-[0.85rem] hover:underline"
          >
            <ExternalLink className="w-4 h-4" />
            Open problem on LeetCode
          </a>
        </div>
      ) : (
        <p className="text-muted-foreground text-[0.84rem] italic mt-3">
          No LeetCode link for this question. Use the title above and describe your approach in chat.
        </p>
      )}
      </div>

      <p className="text-muted-foreground text-[0.79rem] mt-5 pt-4 border-t border-border italic leading-relaxed shrink-0">
        Explain your approach, data structures, and time/space complexity.
        Type <em>&quot;move on&quot;</em> or <em>&quot;skip&quot;</em> to advance to the next question.
      </p>
    </GlassCard>
  );
}

// ─── Message formatter ───────────────────────────────────────────────────────

function formatMessage(text: string): string {
  return formatRichText(text);
}

// ─── Chat Panel ───────────────────────────────────────────────────────────────

function ChatPanel({
  messages,
  questionText,
  onSend,
  loading,
  company,
}: {
  messages: ChatMessage[];
  questionText: string | null;
  onSend: (text: string) => void;
  loading: boolean;
  company: string;
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
    <div className="flex flex-col h-full glass-card p-5 min-h-[480px] lg:min-h-0">
      <Eyebrow className="flex items-center gap-1.5 mb-4">
        <MessageSquare className="w-3 h-3" /> Interview Chat
      </Eyebrow>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 min-h-0" style={{ maxHeight: "calc(100vh - 380px)" }}>
        {messages.map((msg, i) => {
          if (msg.role === "user") {
            return (
              <div key={i} className="flex justify-end">
                <div className="max-w-[78%] chat-user-bubble rounded-[18px_18px_4px_18px] px-4 py-3 text-[0.88rem] leading-relaxed font-medium">
                  {msg.text}
                </div>
              </div>
            );
          }
          const isLast = i === messages.length - 1;
          const badgeLabel = formatCompanyChatLabel(company);
          return (
            <div key={i} className={`flex justify-start items-start gap-2.5 ${isLast && msg.animateIn ? "msg-slide-in" : ""}`}>
              <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-1 bg-secondary text-primary">
                <Bot className="w-4 h-4" />
              </div>
              <div className="max-w-[80%]">
                <span className={`inline-block text-[0.6rem] font-extrabold tracking-widest px-2 py-0.5 rounded-[5px] mb-1.5 ${AGENT_BADGE_CLS}`}>
                  {badgeLabel}
                </span>
                <div
                  className={`chat-agent-bubble rich-text rounded-[4px_18px_18px_18px] px-4 py-3 text-[0.88rem] leading-[1.7] ${isLast && msg.animateIn ? "cursor-fade" : ""}`}
                  dangerouslySetInnerHTML={{ __html: formatMessage(msg.text) }}
                />
              </div>
            </div>
          );
        })}
        {loading && (
          <div className="flex justify-start items-start gap-2.5">
            <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-1 bg-secondary text-primary">
              <Bot className="w-4 h-4" />
            </div>
            <div className="chat-agent-bubble rounded-[4px_18px_18px_18px] px-4 py-3">
              <div className="flex gap-1.5 items-center">
                {[0, 150, 300].map((d) => (
                  <div
                    key={d}
                    className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"
                    style={{ animationDelay: `${d}ms` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

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
            className="field-input flex-1 resize-none disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="btn-cta self-end px-5 py-3 rounded-[12px] font-bold text-[0.88rem] disabled:opacity-40 flex items-center gap-1.5"
          >
            <Send className="w-4 h-4" />
            Send
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Evaluation ───────────────────────────────────────────────────────────────

const OUTCOME_CONFIG: Record<string, { label: string; color: string }> = {
  solved:  { label: "Solved",  color: "bg-emerald-950/60 text-emerald-300 border-emerald-700" },
  partial: { label: "Partial", color: "bg-amber-950/60 text-amber-300 border-amber-700" },
  guided:  { label: "Guided",  color: "bg-red-950/60 text-red-300 border-red-700" },
  skipped: { label: "Skipped", color: "bg-slate-800/80 text-slate-300 border-slate-600" },
};

const DIFF_COLORS: Record<string, string> = {
  easy:   "bg-emerald-950/60 text-emerald-300 border border-emerald-800",
  medium: "bg-amber-950/60 text-amber-300 border border-amber-800",
  hard:   "bg-red-950/60 text-red-300 border border-red-800",
};

function QuestionBreakdownCard({ qb }: { qb: QuestionBreakdown }) {
  const outcome = OUTCOME_CONFIG[qb.outcome] ?? OUTCOME_CONFIG.partial;
  const diffCls = DIFF_COLORS[(qb.difficulty || "").toLowerCase()] ?? DIFF_COLORS.medium;
  return (
    <div className="bg-muted/50 border border-border rounded-[12px] p-4">
      <div className="flex items-center gap-2 flex-wrap mb-2">
        <span className="text-foreground text-[0.88rem] font-semibold">{qb.question}</span>
        {qb.difficulty && (
          <span className={`text-[0.64rem] font-bold px-2 py-0.5 rounded-[5px] ${diffCls}`}>
            {qb.difficulty}
          </span>
        )}
        <span className={`text-[0.64rem] font-bold px-2 py-0.5 rounded-[5px] border ${outcome.color}`}>
          {outcome.label}
        </span>
        {qb.hints_given > 0 && (
          <span className="text-[0.64rem] text-muted-foreground font-semibold">
            {qb.hints_given} hint{qb.hints_given !== 1 ? "s" : ""}
          </span>
        )}
      </div>
      {qb.notes && (
        <p className="text-muted-foreground text-[0.82rem] leading-relaxed">{qb.notes}</p>
      )}
    </div>
  );
}

function EvalCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`glass-card p-5 ${className}`}>
      {children}
    </div>
  );
}

function EvalLabel({ children, color = "text-primary", className = "" }: { children: React.ReactNode; color?: string; className?: string }) {
  return (
    <h4 className={`text-[0.64rem] font-extrabold uppercase tracking-widest mb-3 ${color} ${className}`}>
      {children}
    </h4>
  );
}

function EvaluationPanel({
  ev,
  alignmentSignals,
  skillGaps,
  achievements,
  hasJobDescription,
}: {
  ev: EvaluationResult;
  alignmentSignals: string[];
  skillGaps: string[];
  achievements: string[];
  hasJobDescription: boolean;
}) {
  const jdAlignmentItems = hasJobDescription ? alignmentSignals : [];
  const resumeStrengthItems = [
    ...achievements,
    ...(!hasJobDescription ? alignmentSignals : []),
  ];
  const strengthItems = [...resumeStrengthItems, ...ev.strengths];

  return (
    <div className="space-y-5 pb-8">
      <Eyebrow className="flex items-center gap-1.5">
        <BarChart3 className="w-3 h-3" /> Final Report
      </Eyebrow>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { score: ev.technical_score, label: "Technical", sub: "Problem solving" },
          { score: ev.communication_score, label: "Communication", sub: "Clarity & reasoning" },
          { score: ev.role_fit_score, label: "Role Fit", sub: "Resume alignment" },
        ].map(({ score, label, sub }) => (
          <GlassCard key={label} className="p-5 text-center">
            <p className="text-[3rem] font-black leading-none mb-1 text-primary">
              {score}<span className="text-[1rem] text-muted-foreground">/10</span>
            </p>
            <p className="text-foreground text-[0.78rem] font-bold uppercase tracking-wider">{label}</p>
            <p className="text-muted-foreground text-[0.68rem] mt-0.5">{sub}</p>
          </GlassCard>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="space-y-3">
          <p className="text-[0.62rem] font-extrabold tracking-[0.16em] uppercase text-muted-foreground pb-1 border-b border-border flex items-center gap-1.5">
            <FileText className="w-3 h-3" /> Resume Evaluation
          </p>

          {jdAlignmentItems.length > 0 && (
            <EvalCard className="border-emerald-800/50!">
              <EvalLabel color="text-emerald-400">JD Alignment Strengths</EvalLabel>
              <div className="space-y-1.5">
                {jdAlignmentItems.map((s, i) => (
                  <div key={i} className="flex items-start gap-2 text-emerald-200 text-[0.83rem] leading-relaxed">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                    {s}
                  </div>
                ))}
              </div>
            </EvalCard>
          )}

          {skillGaps.length > 0 && (
            <EvalCard className="border-red-800/50!">
              <EvalLabel color="text-red-400">Skill Gaps vs JD</EvalLabel>
              <div className="space-y-1.5">
                {skillGaps.map((g, i) => (
                  <div key={i} className="bg-red-950/40 border border-red-900/60 rounded-[8px] px-3 py-1.5 text-red-200 text-[0.83rem]">
                    {g}
                  </div>
                ))}
              </div>
            </EvalCard>
          )}

          {strengthItems.length > 0 && (
            <EvalCard>
              <EvalLabel className="flex items-center gap-1.5">
                <Dumbbell className="w-3 h-3 inline" /> Strengths
              </EvalLabel>
              <div className="space-y-1.5">
                {strengthItems.map((s, i) => (
                  <p key={i} className="text-foreground text-[0.85rem] leading-snug flex items-start gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                    {s}
                  </p>
                ))}
              </div>
            </EvalCard>
          )}
        </div>

        <div className="space-y-3">
          <p className="text-[0.62rem] font-extrabold tracking-[0.16em] uppercase text-muted-foreground pb-1 border-b border-border flex items-center gap-1.5">
            <Puzzle className="w-3 h-3" /> Interview Performance
          </p>

          {ev.question_breakdown.length > 0 && (
            <EvalCard>
              <EvalLabel className="flex items-center gap-1.5">
                <ClipboardList className="w-3 h-3 inline" /> Question Breakdown
              </EvalLabel>
              <div className="space-y-2">
                {ev.question_breakdown.map((qb, i) => (
                  <QuestionBreakdownCard key={i} qb={qb} />
                ))}
              </div>
            </EvalCard>
          )}

          {ev.weaknesses.length > 0 && (
            <EvalCard>
              <EvalLabel className="flex items-center gap-1.5">
                <Wrench className="w-3 h-3 inline" /> Areas to Improve
              </EvalLabel>
              <div className="space-y-1.5">
                {ev.weaknesses.map((w, i) => (
                  <p key={i} className="text-foreground text-[0.85rem] leading-snug flex items-start gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
                    {w}
                  </p>
                ))}
              </div>
            </EvalCard>
          )}
        </div>
      </div>

      <EvalCard>
        <EvalLabel>Recommendation</EvalLabel>
        <p className="text-foreground text-[0.95rem] font-bold mb-3 tracking-tight">{ev.recommendation}</p>
        <div
          className="eval-prose text-[0.86rem]"
          dangerouslySetInnerHTML={{ __html: formatRichText(ev.detailed_feedback) }}
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
  const [lcFetchFailed, setLcFetchFailed] = useState(false);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [turnLoading, setTurnLoading] = useState(false);
  const [evaluation, setEvaluation] = useState<EvaluationResult | null>(null);
  const [evalLoading, setEvalLoading] = useState(false);
  const [initDone, setInitDone] = useState(false);
  const [fetchingNext, setFetchingNext] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const usedQuestionIdsRef = useRef<number[]>([]);
  const loadNextQuestionRef = useRef<() => Promise<void>>(async () => {});

  useEffect(() => {
    usedQuestionIdsRef.current = usedQuestionIds;
  }, [usedQuestionIds]);

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
      setCompany(formatDisplayLabel(c));
      setRole(formatDisplayLabel(r));
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
    if (!activeQuestionLink) {
      setLcContentHtml("");
      setLcFetchFailed(false);
      return;
    }
    setLcContentHtml(null);
    setLcFetchFailed(false);
    let cancelled = false;
    fetchLeetCode(activeQuestionLink)
      .then((lc: LeetCodeResult) => {
        if (cancelled) return;
        if (lc.found && lc.content_html) {
          setLcContentHtml(lc.content_html);
          setActiveQuestionTags(lc.topic_tags ?? []);
          if (lc.difficulty) setActiveQuestionDifficulty(lc.difficulty);
          setLcFetchFailed(false);
        } else {
          setLcContentHtml("");
          setLcFetchFailed(true);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLcContentHtml("");
          setLcFetchFailed(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeQuestionLink]);

  useEffect(() => {
    if (!profileOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setProfileOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [profileOpen]);

  const loadNextQuestion = useCallback(async () => {
    setFetchingNext(true);
    try {
      if (!sessionId) return;

      const next = await fetchNextQuestion(
        sessionId,
        company,
        usedQuestionIdsRef.current
      );
      if (next) {
        setUsedQuestionIds(next.used_question_ids);
        setActiveQuestionIndex(next.question_index);
        setActiveQuestionText(next.question_title);
        setActiveQuestionLink(next.question_link);
        setActiveQuestionDifficulty(next.difficulty);
        setActiveQuestionTags([]);
        setLcContentHtml(null);
        setLcFetchFailed(false);
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
        setActiveQuestionLink(null);
        setLcContentHtml("");
      }
    } catch (err: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          text:
            err instanceof Error
              ? `Could not load the next question: ${err.message}`
              : "Could not load the next question. Please try again.",
          type: "guide",
        },
      ]);
    } finally {
      setFetchingNext(false);
    }
  }, [sessionId, company]);

  useEffect(() => {
    loadNextQuestionRef.current = loadNextQuestion;
  }, [loadNextQuestion]);

  async function handleSend(text: string) {
    if (!sessionId || candidateId === null || fetchingNext || turnLoading) return;
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
        setFetchingNext(true);
        setActiveQuestionLink(null);
        setLcContentHtml("");
        const scheduleNext = () => {
          void loadNextQuestionRef.current();
        };
        if (activeQuestionText === "Introduction") {
          scheduleNext();
        } else {
          setTimeout(scheduleNext, 800);
        }
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
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const isIntro = activeQuestionText === "Introduction";
  const isDone = activeQuestionText === null && !fetchingNext;

  const showReport = Boolean(evaluation);
  const showInterviewPanels = !showReport;

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <div className="flex items-center justify-between px-4 sm:px-8 py-4 border-b border-border bg-card/40 backdrop-blur-sm gap-3 shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <BrandMark />
            <BrandTitle />
          </div>
          <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
            <div className="hidden sm:flex items-center gap-2 text-muted-foreground text-[0.8rem] flex-wrap justify-end">
              Interviewing for
              <span className="bg-secondary text-primary border border-border rounded-[6px] px-2.5 py-0.5 font-semibold text-[0.78rem]">{formatDisplayLabel(role)}</span>
              at
              <span className="bg-secondary text-primary border border-border rounded-[6px] px-2.5 py-0.5 font-semibold text-[0.78rem]">{formatDisplayLabel(company)}</span>
            </div>
            <button
              type="button"
              onClick={() => setProfileOpen((v) => !v)}
              className={`inline-flex items-center gap-1.5 rounded-[10px] px-3 py-2 text-[0.78rem] font-semibold border transition-colors ${
                profileOpen
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-secondary text-primary border-border hover:border-primary/50"
              }`}
              aria-expanded={profileOpen}
              aria-controls="profile-drawer"
            >
              <PanelRightOpen className="w-4 h-4" />
              <span className="hidden sm:inline">Profile</span>
            </button>
          </div>
        </div>

        <div
          className={`flex-1 flex flex-col px-4 sm:px-6 py-4 min-h-0 ${
            showReport || isDone ? "overflow-y-auto" : "overflow-hidden"
          }`}
        >
          {!showReport && (
            <ProgressTracker completed={questionsCompleted} isIntro={isIntro} isDone={isDone && !fetchingNext} />
          )}

          {showInterviewPanels && (
            <div className="flex flex-1 min-h-0 mt-4 gap-5 overflow-hidden">
              <div className="flex flex-1 flex-col lg:flex-row gap-5 min-h-0 min-w-0">
                <div className="flex-1 lg:basis-1/2 min-w-0 min-h-[280px] lg:min-h-0 overflow-y-auto">
                  <QuestionCard
                    questionText={activeQuestionText}
                    isLoadingNext={fetchingNext}
                    difficulty={activeQuestionDifficulty}
                    link={activeQuestionLink}
                    tags={activeQuestionTags}
                    contentHtml={lcContentHtml}
                    fetchFailed={lcFetchFailed}
                    company={company}
                    role={role}
                  />
                </div>

                <div className="flex-1 lg:basis-1/2 min-w-0 min-h-[340px] lg:min-h-0 flex flex-col">
                  <ChatPanel
                    messages={messages}
                    questionText={activeQuestionText}
                    onSend={handleSend}
                    loading={turnLoading || fetchingNext}
                    company={company}
                  />
                </div>
              </div>

              <ProfileDrawer
                result={analyseResult}
                company={company}
                role={role}
                open={profileOpen}
                onClose={() => setProfileOpen(false)}
                onBack={() => router.push("/")}
              />
            </div>
          )}

          {/* Evaluation / generate report */}
          {(isDone || evaluation) && (
            <div className={`border-t border-border pt-4 ${showInterviewPanels ? "mt-4" : "mt-0"}`}>
              {!evaluation ? (
                <>
                  <p className="text-center text-muted-foreground text-[0.88rem] mb-4">
                    All questions completed — you can now generate your final evaluation report.
                  </p>
                  <PrimaryCta onClick={handleEvaluate} disabled={evalLoading} className="py-3.5 text-[0.95rem]">
                    {evalLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Evaluating your performance…
                      </span>
                    ) : (
                      <span className="flex items-center justify-center gap-2">
                        <BarChart3 className="w-4 h-4" />
                        Generate Final Evaluation
                      </span>
                    )}
                  </PrimaryCta>
                </>
              ) : (
                <EvaluationPanel
                  ev={evaluation}
                  alignmentSignals={analyseResult?.resume_profile.alignment_signals ?? []}
                  skillGaps={analyseResult?.resume_profile.skill_gaps ?? []}
                  achievements={analyseResult?.resume_profile.achievements ?? []}
                  hasJobDescription={analyseResult?.job_description_provided ?? false}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
