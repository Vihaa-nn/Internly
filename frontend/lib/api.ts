const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ResumeProfile {
  skills: string[];
  years_experience: number;
  projects: string[];
  education: string;
  notable_gaps: string[];
  target_languages: string[];
  alignment_signals: string[];
  skill_gaps: string[];
}

export interface CompanyIntel {
  interview_rounds: string[];
  common_questions: string[];
  difficulty_notes: string;
  culture_notes: string;
}

export interface AnalyseResult {
  candidate_id: number;
  dsa_available: boolean;
  dsa_message: string;
  resume_profile: ResumeProfile;
  company_intel: CompanyIntel | null;
}

export interface StartInterviewResult {
  session_id: number;
  intro_turns: Array<{ role: string; text: string; type?: string }>;
}

export interface NextQuestionResult {
  question_index: number;
  question_title: string;
  question_link: string | null;
  difficulty: string;
  used_question_ids: number[];
}

export interface TurnResult {
  type: "hint" | "followup" | "guide" | "accept";
  text: string;
}

export interface QuestionBreakdown {
  question: string;
  difficulty: string;
  outcome: "solved" | "guided" | "skipped" | "partial";
  hints_given: number;
  notes: string;
}

export interface EvaluationResult {
  technical_score: number;
  communication_score: number;
  role_fit_score: number;
  strengths: string[];
  weaknesses: string[];
  recommendation: string;
  detailed_feedback: string;
  question_breakdown: QuestionBreakdown[];
}

export interface LeetCodeResult {
  found: boolean;
  title?: string;
  difficulty?: string;
  content_html?: string;
  topic_tags?: string[];
  hints?: string[];
}

// ─── API functions ────────────────────────────────────────────────────────────

export async function analyseResume(
  resumeFile: File,
  company: string,
  role: string,
  jobDescription: string
): Promise<AnalyseResult> {
  const form = new FormData();
  form.append("resume", resumeFile);
  form.append("company", company);
  form.append("role", role);
  form.append("job_description", jobDescription);

  const res = await fetch(`${BASE}/api/analyse`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Analysis failed (${res.status})`);
  }
  return res.json();
}

export async function startInterview(candidateId: number): Promise<StartInterviewResult> {
  const res = await fetch(`${BASE}/api/interview/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_id: candidateId }),
  });
  if (!res.ok) throw new Error(`Failed to start interview (${res.status})`);
  return res.json();
}

export async function fetchNextQuestion(
  sessionId: number,
  company: string,
  usedQuestionIds: number[]
): Promise<NextQuestionResult | null> {
  const res = await fetch(`${BASE}/api/interview/next-question`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, company, used_question_ids: usedQuestionIds }),
  });
  if (!res.ok) throw new Error(`Failed to fetch question (${res.status})`);
  return res.json();
}

export async function submitTurn(
  sessionId: number,
  questionIndex: number,
  candidateResponse: string,
  candidateId: number,
  company: string,
  role: string
): Promise<TurnResult> {
  const res = await fetch(`${BASE}/api/interview/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      question_index: questionIndex,
      candidate_response: candidateResponse,
      candidate_id: candidateId,
      company,
      role,
    }),
  });
  if (!res.ok) throw new Error(`Turn failed (${res.status})`);
  return res.json();
}

export async function generateEvaluation(
  sessionId: number,
  candidateId: number
): Promise<EvaluationResult> {
  const res = await fetch(`${BASE}/api/interview/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, candidate_id: candidateId }),
  });
  if (!res.ok) throw new Error(`Evaluation failed (${res.status})`);
  return res.json();
}

export async function fetchLeetCode(link: string): Promise<LeetCodeResult> {
  const res = await fetch(`${BASE}/api/leetcode/fetch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ link }),
  });
  if (!res.ok) return { found: false };
  return res.json();
}
