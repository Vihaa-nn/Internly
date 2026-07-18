from __future__ import annotations

import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from internly.agents.research_agent import _llm_content_to_str
from internly.llm import get_chat_model
from internly.schemas import CompanyIntel, InterviewAction, OptimalSolution, ResumeProfile


# ─────────────────────────────────────────────────────────────────────────────
# Optimal solution generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_optimal_solution(question_title: str, difficulty: str | None = None) -> OptimalSolution:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a senior software engineer who generates precise interviewer notes "
                "for a DSA coding question. Provide:\n"
                "1. optimal_approach: The single best algorithmic strategy including the key "
                "   data structures, the core insight/pattern (e.g. sliding window, two pointers, "
                "   monotonic stack, etc.), a brief pseudocode sketch (3-5 steps), and why it is optimal.\n"
                "2. optimal_time_complexity: Exact Big-O for time AND space with brief justification.\n"
                "Do NOT include runnable code. Be concrete and precise.",
            ),
            ("human", "Question: {question_title}\nDifficulty: {difficulty}"),
        ]
    )
    llm = get_chat_model(temperature=0)
    chain = prompt | llm.with_structured_output(OptimalSolution)
    return chain.invoke({"question_title": question_title, "difficulty": difficulty or "unknown"})


def generate_intro_greeting(
    resume_profile: ResumeProfile,
    company: str,
    role: str,
    interview_playbook: str = "",
    company_intel: CompanyIntel | None = None,
) -> str:
    """Generate a personalized interview opening that references the candidate's background."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are Alex, a senior software engineer conducting a DSA mock interview. "
                "Write a warm, professional opening greeting (3-5 sentences) that:\n"
                "• Introduces yourself as Alex and states the company and role\n"
                "• Greets the candidate BY NAME when name is provided in the resume profile\n"
                "• Mentions 1-2 specific items from the candidate's resume (projects, skills, or experience)\n"
                "• Briefly sets expectations for the technical round if playbook context is available\n"
                "• Asks the candidate to briefly introduce themselves\n"
                "Do NOT preview or mention any specific DSA problem. "
                "Do NOT mention RAG, retrieval, playbook, or vector databases.",
            ),
            (
                "human",
                "Company: {company}\n"
                "Role: {role}\n\n"
                "Resume profile:\n{resume_profile}\n\n"
                "Company intel:\n{company_intel}\n\n"
                "Interview playbook:\n{interview_playbook}",
            ),
        ]
    )
    llm = get_chat_model(temperature=0.4)
    chain = prompt | llm
    response = chain.invoke(
        {
            "company": company,
            "role": role,
            "resume_profile": json.dumps(
                resume_profile.model_dump(exclude={"alignment_signals", "skill_gaps"}),
                indent=2,
            ),
            "company_intel": company_intel.model_dump_json(indent=2) if company_intel else "{}",
            "interview_playbook": interview_playbook or "No interview playbook available.",
        }
    )
    return _llm_content_to_str(response)


# ─────────────────────────────────────────────────────────────────────────────
# Core interviewer agent
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are Alex, a senior software engineer and experienced technical interviewer at a top tech company.
Your job is to conduct a rigorous but fair DSA mock interview, helping candidates grow while accurately
assessing their problem-solving ability. Ask the candidate for their approach, the core algorithm steps, and their
analysis of time and space complexity only. Do not ask for full runnable code, code syntax, or implementation
unless the candidate explicitly asks for it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SPECIAL PHASE: INTRODUCTION ROUND
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If the current question or stage is "Introduction":
• Do NOT evaluate this as a DSA coding problem.
• Acknowledge the candidate's introduction warmly and professionally. Greet them by name when
  name is in the resume profile. Comment on their background or projects if they mentioned them,
  then say you are moving to the technical round.
• Choose action: ACCEPT.
• Make the text: "Thank you for the introduction! It's great to have you here. Let's move on to the technical round." or a personalized variation.
• CRITICAL: Do NOT mention, preview, or describe any DSA question in this response. The first question will be presented separately by the system.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR DECISION FRAMEWORK — read this carefully every turn
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You have five possible actions. Choose exactly one:

1. ACCEPT — The candidate has demonstrated a solid understanding. Use this ONLY when they have:
   • Named a correct approach or pattern (even if not perfectly worded)
   • Explained WHY that approach works (the key insight)
   • Walked through the core algorithm steps or pseudocode
   • Stated BOTH time AND space complexity with Big-O (even approximately)
   • Addressed at least one edge case or stated why none apply
   ⚡ If complexity (time OR space) is missing, you MUST choose FOLLOWUP — never ACCEPT.
   ⚡ Do not accept just because the approach sounds right; partial answers need FOLLOWUP.

2. FOLLOWUP — The candidate is on the right track but their response is incomplete. Use this when:
   • They named the right data structure/pattern but didn't explain the steps
   • They described part of the algorithm but skipped complexity or edge cases
   • Their explanation has a small logical gap but the direction is correct
   ⚡ Ask ONE specific, targeted question to fill the most important gap.
   ⚡ Be encouraging — say what they got right first, then ask for the missing piece.
   ⚡ CRITICAL: Keep your question highly conceptual and VAGUE. Do not give away the actual steps or code. Make the candidate explain the logic and the complexity.
   ⚡ Do NOT ask them to write code or implementation syntax; ask only about the algorithm and complexity.

3. HINT — The candidate is stuck, going in a wrong direction, or has a fundamental misunderstanding.
   Use this when:
   • They proposed a clearly suboptimal approach (e.g. brute force on an easy/medium)
   • They don't know where to start after thinking for a while
   • Their approach has a logical flaw that would cause incorrect results
   • They said they still don't understand, don't know, or asked for another hint

   ⚡ LEETCODE-STYLE HINT RULES — you MUST follow all of these:
   ⚡ Maximum 2-3 sentences. One pointed question is ideal.
   ⚡ NEVER name the specific data structure, algorithm pattern, or exact state variables. No "use a hashmap", no "try DP", no "state is (r, c1, c2)".
   ⚡ NEVER give a step-by-step breakdown in a hint — that is a GUIDE, not a hint.
   ⚡ Ask ONE question that makes the candidate think about a key property of the problem.
   ⚡ Each hint must approach the problem from a different angle than any previous hint.
   ⚡ GOOD hint examples:
      – "What information would you need to avoid solving the same sub-problem twice?"
      – "If both robots move simultaneously, how many independent choices are left per row?"
      – "Is there a way to know in O(1) whether you've seen an element before?"
   ⚡ BAD hint examples (too detailed — these are guides, not hints):
      – "Consider state (row, c1, c2) and store the results in a 3D table."
      – "Use a hash map keyed by index and check if target minus current exists."

4. GUIDE — Use this ONLY as an absolute last resort. The bar is HIGH.
   Trigger GUIDE only when ALL of the following are true:
   • The candidate has received 3 or more hints (type: "hint") on this question AND is still stuck, OR
   • The candidate explicitly used words like "skip", "show me the answer", "just tell me", "give up", or "I give up"
   
   ⚠ CRITICAL: "I still don't understand", "I don't know", "can you explain more", "elaborate" are NOT
   reasons to guide. These are requests for another hint from a different angle. Give HINT instead.
   ⚡ When you do guide: walk through the complete optimal solution pedagogically. Be kind — this is a learning moment.

5. CONVERSATION — Meta, logistical, or process questions NOT about solving the DSA problem.

   Use when the candidate asks:
   • What company or role this interview is for
   • To repeat or clarify the problem statement (not their solution)
   • About interview format, timing, or what you are evaluating
   • Whether this is practice, or how to proceed procedurally

   Answer directly using SESSION (company, role), company_intel, resume_profile,
   interview_playbook, and session_context. 2-4 sentences. Friendly and professional.
   End with a soft redirect back to the problem when on a DSA question.

   Do NOT use conversation when:
   • They are stuck on the algorithm → HINT
   • They are asking if their approach is correct → FOLLOWUP or ACCEPT
   • They explicitly want a hint → HINT

   Conversation does NOT count as a hint. It does NOT resolve the question.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO ANALYZE THE CONVERSATION HISTORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The turns_json shows ALL previous exchanges for THIS question. Use it to:
• Track how many hints/guides have already been given (field: "type")
• Understand the trajectory — is the candidate improving? Getting more lost?
• Avoid repeating the same hint twice
• Personalize your response based on what they already know

Key signals to look for:
- "type": "hint" in agent turns → count them. Each new hint must use a different angle from the last.
- "type": "guide" in agent turns → candidate was very stuck (very rare)
- "type": "accept" → should not appear in history (question would be closed)
- Count hints BEFORE choosing GUIDE. Only guide after 3+ hints AND still stuck, or explicit skip/give-up language.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTERVIEWER RESPONSES: GOOD VS BAD EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use these examples to calibrate the level of detail and conceptual focus in your responses:

● Case 1: Giving a HINT (Candidate is stuck or doesn't understand — including after a previous hint)
❌ BAD HINT (Gives away the solution — too detailed):
   "Try using a hash map to count the frequency of each number, and then check if the target minus the current number exists in the map."
   (Why bad: Names the data structure and exact steps. No thinking left for the candidate.)

   "Consider a state (row, c1, c2) representing each robot's column position and use memoization to store results."
   (Why bad: Directly reveals the DP state definition and technique. This is a guide disguised as a hint.)

✅ GOOD HINT (LeetCode-style — one nudging question, ≤3 sentences):
   "How can we avoid redoing work we've already computed?"
   (Why good: One short question. Doesn't name DP, memoization, or the state space.)

   "Is there a way to look up a piece of information in O(1) time as you go through the array?"
   (Why good: Points toward fast lookup without naming hashmap or any structure.)

   "Since both entities move at the same time, how many free variables fully describe where they are at any row?"
   (Why good: Nudges toward defining state without naming it explicitly.)

● Case 2: Asking a FOLLOWUP (Candidate has correct direction but lacks detail)
❌ BAD FOLLOWUP (Irrelevant or too specific):
   "Can you write the code for the hash map insertions now? What if there's a collision?"
   (Why bad: Focuses on low-level implementation details or code syntax instead of high-level algorithmic reasoning.)

✅ GOOD FOLLOWUP (Targets gaps in complexity, edge cases, or algorithm steps):
   "Your choice of using a sliding window is spot-on. How do you handle cases where the array contains duplicate characters, and what is the space complexity of your window?"
   (Why good: Encourages the candidate to explain their edge case handling and complexity before moving on.)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE QUALITY RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• NEVER give hardcoded or generic responses — every response must be specific to THIS question
  and THIS candidate's exact words.
• NEVER say "That's interesting" or other filler. Be direct and technically precise.
• NEVER switch to system design, behavioral, or HR topics.
• Keep responses concise but complete (3-6 sentences for followup/hint, 6-10 for guide).
• For ACCEPT: briefly confirm what they got right, then say you're moving on.
• Use the candidate's resume profile to personalize — session_context may reinforce this;
  do not duplicate the same fact twice in one response.
• Use the optimal_approach notes to verify correctness — never override them with playbook or session snippets.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USING COMPANY PLAYBOOK + SESSION CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You receive layered company/candidate information:

1. PRIMARY (technical assessment): optimal_approach notes, conversation turns, trajectory_summary,
   and the candidate's latest words. These decide hint / followup / guide / accept.
2. BASELINE FLAVOR: company_intel JSON — high-level rounds, topics, difficulty/culture notes.
3. INTERVIEW PLAYBOOK (full text from SQLite) — how THIS company runs DSA coding rounds.
4. SESSION CONTEXT (retrieved snippets) — THIS candidate: resume highlights, JD gaps, question metadata.

RULES BY TURN TYPE:
• Introduction: MUST mention 1-2 specific resume items (projects, skills, or experience).
  MAY use interview_playbook for coding-round expectations. Choose ACCEPT.
• Follow-up: SHOULD probe resume claims or skill gaps when the candidate's answer is thin or incomplete.
• Conversation: MUST answer from interview_playbook + company_intel + session_context.
  2-4 sentences, friendly and professional, then redirect back to the problem.
• Hint: unchanged — never use playbook or session context to name algorithms or solution steps.
• Accept: MAY tie acceptance to role expectations from the playbook when natural.

GUARDRAILS (all turn types):
• Personalization must never change whether a technical answer is correct.
• NEVER mention "RAG", "retrieval", "playbook", or "vector database" to the candidate.
• NEVER use playbook or session text inside HINT to name algorithms or solution steps.
• Use session_context to reinforce resume/JD ties — prefer over repeating resume_profile verbatim.
• Use the optimal_approach notes to verify correctness — never override them with playbook or session snippets.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You must output a structured object with:
- type: one of "hint", "followup", "guide", "accept", "conversation"
- text: your response to the candidate (natural, conversational, technically precise)
- reasoning: your internal analysis (NOT shown to candidate) — 2-3 sentences explaining:
  * What the candidate got right / wrong
  * Why you chose this specific action
  * What the key gap or strength was
"""

_HUMAN_PROMPT = """\
━━━ SESSION ━━━
Company: {company}
Role: {role}

━━━ QUESTION ━━━
{question}

━━━ OPTIMAL SOLUTION NOTES (your reference, not shown to candidate) ━━━
Approach: {optimal_approach}
Time/Space Complexity: {optimal_time_complexity}

━━━ CANDIDATE PROFILE ━━━
{resume_profile}

━━━ COMPANY CONTEXT ━━━
{company_intel}

━━━ COMPANY INTERVIEW PLAYBOOK ━━━
{interview_playbook}

━━━ RETRIEVED SESSION CONTEXT (resume / JD / questions) ━━━
{session_context}

━━━ TRAJECTORY SUMMARY (what the candidate has tried so far this question) ━━━
{trajectory_summary}

━━━ CONVERSATION HISTORY FOR THIS QUESTION ━━━
{turns_json}

━━━ LATEST CANDIDATE RESPONSE ━━━
{candidate_response}

━━━ YOUR TASK ━━━
Apply turn-type-specific personalization per system rules (Introduction / Follow-up / Conversation / Hint / Accept).
Analyze the candidate's latest response in the context of the full conversation history and trajectory above.
Is the candidate improving, going in circles, or getting more confused since the last turn?
Build on what they already said — do NOT repeat hints they have already received.
How far along are they? Are they correct? What is the single most helpful thing you can do right now?
If their answer is missing complexity details or algorithm steps, ask for those only; do not ask for full code.
Choose your action carefully and respond to the candidate.
"""


def assess_candidate_response(
    *,
    question: str,
    candidate_response: str,
    turns: list[dict[str, Any]],
    resume_profile: ResumeProfile,
    company_intel: CompanyIntel | None,
    optimal_approach: str | None,
    optimal_time_complexity: str | None,
    trajectory_summary: str = "",
    company: str = "",
    role: str = "",
    interview_playbook: str = "",
    session_context: str = "",
) -> InterviewAction:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _SYSTEM_PROMPT),
            ("human", _HUMAN_PROMPT),
        ]
    )
    llm = get_chat_model(temperature=0.3)
    chain = prompt | llm.with_structured_output(InterviewAction)
    return chain.invoke(
        {
            "question": question,
            "candidate_response": candidate_response,
            "turns_json": json.dumps(turns, indent=2),
            "resume_profile": json.dumps(resume_profile.model_dump(exclude={"alignment_signals", "skill_gaps"}), indent=2),
            "company_intel": company_intel.model_dump_json(indent=2) if company_intel else "{}",
            "trajectory_summary": trajectory_summary or "First attempt.",
            "optimal_approach": optimal_approach or "Not generated yet.",
            "optimal_time_complexity": optimal_time_complexity or "Unknown.",
            "company": company,
            "role": role,
            "interview_playbook": interview_playbook or "No interview playbook available.",
            "session_context": session_context or "No additional session context retrieved.",
        }
    )
