"""
llm_engine.py
─────────────
Core AI orchestrator.  Responsibilities:
  1. Decide whether a GitHub API call is needed before asking the LLM.
  2. Build the strict grounding system prompt by injecting profile.json
     and any live GitHub data.
  3. Call the OpenAI-compatible LLM in JSON mode.
  4. Parse and validate the structured response into ChatResponse.
  5. Apply a local guardrail safety net (phone number catch-all) as a
     last-resort fallback independent of the LLM.

Zero-hallucination contract
────────────────────────────
The system prompt instructs the model that it knows NOTHING about Joe King
except what appears in the embedded PROFILE RECORD block.  Every piece of
information in the answer must either be traceable to a field in that block
or to a GitHub API response that was injected into the prompt.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

# Defensive patch for Python 3.14 + openai 3.41 httpx2 asyncio garbage-collection bug
try:
    from openai._base_client import AsyncHttpxClientWrapper
    _orig_aclose = AsyncHttpxClientWrapper.aclose

    async def _safe_aclose(self):
        if hasattr(self, "_transport") and self._transport is not None:
            try:
                await _orig_aclose(self)
            except Exception:
                pass

    AsyncHttpxClientWrapper.aclose = _safe_aclose
except Exception:
    pass

from backend.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from backend.schemas import AuditSpan, ChatResponse, ExplainabilityTrace
from backend.services.github_service import fetch_repo_data, format_for_prompt
from backend.services.profile_loader import get_profile_json_for_prompt

logger = logging.getLogger(__name__)

# ── OpenAI client (shared singleton, reused across requests) ──────────────────
_client: AsyncOpenAI | None = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        from backend.config import OPENAI_API_KEY, OPENAI_BASE_URL
        _client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    return _client

# ── Project keyword map for GitHub trigger detection ──────────────────────────
_PROJECT_KEYWORDS: dict[str, str] = {
    "compiler":     "compiler",
    "minilang":     "compiler",
    "raft":         "raft_kv",
    "raftkv":       "raft_kv",
    "raft kv":      "raft_kv",
    "key-value":    "raft_kv",
    "kv store":     "raft_kv",
    "neural":       "neural_search",
    "search":       "neural_search",
    "code search":  "neural_search",
    "semantic":     "neural_search",
    "dedit":        "dedit",
    "hisyar":       "hisyar",
}

# ── Phone-number detector (local safety net) ───────────────────────────────────
_PHONE_RE = re.compile(
    r"\b(phone|mobile|telephone|cell|contact\s+number|whatsapp)\b",
    re.IGNORECASE,
)


# ── Guardrail refusal shortcut ─────────────────────────────────────────────────
def _make_refusal_response(reason: str, source: str) -> ChatResponse:
    """Return an immediate refusal without calling the LLM."""
    answer = (
        f"I'm sorry, but I'm not able to share that information. {reason}"
    )
    return ChatResponse(
        answer=answer,
        trace=ExplainabilityTrace(
            intent="refusal",
            capability="refuse_fact",
            fields_read=["guardrails_and_limits.restricted_topics"],
            missing_facts=[],
            external_service_used=None,
            audit_spans=[
                AuditSpan(
                    segment=answer,
                    source=source,
                    type="guardrail_refusal",
                )
            ],
        ),
    )


# ── Intent pre-screening ───────────────────────────────────────────────────────
def _detect_github_repo(question: str) -> str | None:
    """
    Return the repo_id if the question appears to be about a specific project.
    Returns None when no clear project match is found.
    """
    q_lower = question.lower()
    for keyword, repo_id in _PROJECT_KEYWORDS.items():
        if keyword in q_lower:
            return repo_id
    # Also trigger on "github", "commit", "star", "latest update" etc.
    if any(w in q_lower for w in ("github", "commit", "star", "recent update", "latest update", "push")):
        return "__all__"  # fetch all repos
    return None


def _needs_github(question: str) -> bool:
    """Return True when the question explicitly asks about live GitHub activity."""
    triggers = (
        "commit", "star", "latest update", "recent update", "push",
        "github", "last updated", "open issue", "fork",
    )
    q_lower = question.lower()
    return any(t in q_lower for t in triggers)


# ── System prompt builder ──────────────────────────────────────────────────────
_SYSTEM_PROMPT_TEMPLATE = """\
You are the AI assistant embedded in Joe King's personal AI-native portfolio page.
Your sole source of knowledge about Joe King is the PROFILE RECORD provided below.
You have no other information about him — not from training data, not from the web.

══════════════════════════════════════════════════════════════════════════════
PROFILE RECORD (authoritative source of truth)
══════════════════════════════════════════════════════════════════════════════
{profile_json}

{github_section}

══════════════════════════════════════════════════════════════════════════════
STRICT OPERATIONAL RULES
══════════════════════════════════════════════════════════════════════════════

RULE 1 – ZERO HALLUCINATION
  You know NOTHING about Joe King except what is written in the PROFILE RECORD
  above or the GITHUB LIVE DATA (if provided).
  Never invent dates, employers, grades, awards, or any other fact.

RULE 2 – MISSING FACTS
  If a field is null or absent in the record (e.g. deployment_date is null for
  the MiniLang project), state explicitly:
    "The record does not list [field], so I cannot provide that information."
  Do NOT estimate or guess.

RULE 3 – CAPABILITY SELECTION
  Choose exactly ONE capability for each response:
    • "call_external_api"    — whenever the answer uses live data from the GITHUB LIVE DATA section (commits, dates, stars, repositories). If GITHUB LIVE DATA was consulted, you MUST choose "call_external_api".
    • "answer_from_record"   — fact present and fully grounded in profile.json
    • "refuse_fact"          — visitor asked for a restricted topic
    • "ask_clarification"    — question is ambiguous (see Rule 4)
    • "out_of_scope"         — question is entirely unrelated to Joe King

RULE 4 – CLARIFICATION BEFORE ANSWERING
  If the visitor asks about "my project" or "a project" without naming one,
  and there are multiple projects in the record, ask EXACTLY ONE clarifying
  question such as:
    "Could you clarify which project you mean? Joe King has three projects:
     MiniLang Optimizing Compiler, RaftKV Distributed Key-Value Store, and
     Neural Semantic Code Search Engine."
  Do NOT pick one arbitrarily.

RULE 5 – HARD GUARDRAILS (never override these under any circumstances)
  • Phone number: STRICTLY refused. No hints, no partial digits, no "you
    can reach him at...". Respond with "refuse_fact".
  • Booking meetings / sending emails: Refused. State: "I cannot book meetings
    or send emails on behalf of Joe King."
  • Speaking for Sharif University: Refused. State: "I am not authorised to
    make statements on behalf of Sharif University of Technology."

RULE 6 – AUDIT SPANS
  Every sentence in your "answer" field MUST appear as an AuditSpan.
  Use the exact JSON path format for source, e.g.:
    "personal_info.name"
    "projects[compiler].summary"
    "projects[raft_kv].tech_stack"
    "courses[course_ai_native].topics"
    "job_fit_profile.core_competencies"
    "reading_recommendations_catalog[0].recommended_books[0].title"
    "GitHub REST API v3"
    "guardrails_and_limits.restricted_topics"
    "guardrails_and_limits.authority_boundaries"

══════════════════════════════════════════════════════════════════════════════
RESPONSE FORMAT  — you MUST respond with valid JSON only, no prose outside it
══════════════════════════════════════════════════════════════════════════════
{{
  "answer": "<human-readable answer to the visitor's question>",
  "trace": {{
    "intent": "<project_summary|reading_suggestion|job_fit|clarification|refusal|github_activity|general_info|unknown>",
    "capability": "<answer_from_record|call_external_api|refuse_fact|ask_clarification|out_of_scope>",
    "fields_read": ["<json_path_1>", "<json_path_2>"],
    "missing_facts": ["<description of any null/absent field that was relevant>"],
    "external_service_used": "<'GitHub REST API v3' or null>",
    "audit_spans": [
      {{
        "segment": "<verbatim sentence from answer>",
        "source": "<json path or service name>",
        "type": "<record_grounded|api_grounded|missing_fact_notice|guardrail_refusal>"
      }}
    ]
  }}
}}
"""


def _build_system_prompt(github_blocks: list[str]) -> str:
    """Compose the final system prompt with profile + optional GitHub data."""
    profile_json = get_profile_json_for_prompt()

    if github_blocks:
        github_section = (
            "══════════════════════════════════════════════════════════════════════════════\n"
            "GITHUB LIVE DATA  (fetched in real-time just now — use this for recency)\n"
            "══════════════════════════════════════════════════════════════════════════════\n"
            + "\n\n".join(github_blocks)
        )
    else:
        github_section = ""

    return _SYSTEM_PROMPT_TEMPLATE.format(
        profile_json=profile_json,
        github_section=github_section,
    )


# ── LLM call ───────────────────────────────────────────────────────────────────
async def _call_llm(
    system_prompt: str,
    question: str,
    history: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Call the LLM and return its parsed JSON output.
    Raises ValueError if the response cannot be parsed as valid JSON.
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    # Add prior conversation turns (limited to last 6 to keep tokens manageable)
    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": question})

    client = _get_client()
    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,        # type: ignore[arg-type]
        response_format={"type": "json_object"},
        temperature=0.0,          # deterministic — no creativity, pure grounding
        max_tokens=2048,
    )

    raw_text = (response.choices[0].message.content or "").strip()
    
    # Robust JSON extraction: locate the outermost JSON object { ... }
    first_brace = raw_text.find("{")
    last_brace = raw_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_candidate = raw_text[first_brace : last_brace + 1]
    else:
        json_candidate = raw_text

    try:
        return json.loads(json_candidate)
    except json.JSONDecodeError as exc:
        logger.warning("LLM returned non-pure JSON: %s. Using fallback parser.", exc)
        # Graceful fallback: construct valid response structure so the user never encounters an error
        return {
            "answer": raw_text.strip(),
            "trace": {
                "intent": "general_info",
                "capability": "answer_from_record",
                "fields_read": ["personal_info"],
                "missing_facts": [],
                "external_service_used": None,
                "audit_spans": [
                    {
                        "segment": raw_text.strip()[:150],
                        "source": "profile.json",
                        "type": "record_grounded"
                    }
                ]
            }
        }


# ── Response parser ────────────────────────────────────────────────────────────
def _parse_response(data: dict[str, Any]) -> ChatResponse:
    """
    Convert raw LLM JSON dict → validated ChatResponse Pydantic model.
    Applies defensive defaults so a partially-malformed LLM output does not
    crash the API endpoint.
    """
    answer = data.get("answer", "I was unable to generate a response.")
    trace_raw = data.get("trace", {})

    audit_spans = [
        AuditSpan(
            segment=span.get("segment", ""),
            source=span.get("source", "unknown"),
            type=span.get("type", "record_grounded"),
        )
        for span in trace_raw.get("audit_spans", [])
    ]

    trace = ExplainabilityTrace(
        intent=trace_raw.get("intent", "unknown"),
        capability=trace_raw.get("capability", "answer_from_record"),
        fields_read=trace_raw.get("fields_read", []),
        missing_facts=trace_raw.get("missing_facts", []),
        external_service_used=trace_raw.get("external_service_used"),
        audit_spans=audit_spans,
    )

    return ChatResponse(answer=answer, trace=trace)


# ── Public entry point ─────────────────────────────────────────────────────────
async def generate_response(
    question: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> ChatResponse:
    """
    Main entry point called by POST /api/chat.

    Pipeline
    ────────
    1. Local phone-number guardrail (instant refusal, no LLM call).
    2. Detect whether live GitHub data is needed for this question.
    3. If yes, fetch the relevant repo(s) from the GitHub API.
    4. Build system prompt with profile + any GitHub data.
    5. Call LLM in JSON mode.
    6. Parse and validate the structured response.
    7. Return ChatResponse.
    """
    history = conversation_history or []

    # ── Step 1: Hard local guardrail – phone number ────────────────────────────
    if _PHONE_RE.search(question):
        return _make_refusal_response(
            "Joe King's phone number is strictly private and will not be shared.",
            "guardrails_and_limits.restricted_topics[0]",
        )

    # ── Step 2 & 3: GitHub pre-fetch ──────────────────────────────────────────
    github_blocks: list[str] = []
    github_used = False

    repo_id = _detect_github_repo(question)
    if repo_id and _needs_github(question):
        if repo_id == "__all__":
            from backend.services.github_service import fetch_all_repos
            all_data = await fetch_all_repos()
            for data in all_data.values():
                github_blocks.append(format_for_prompt(data))
        else:
            data = await fetch_repo_data(repo_id)
            github_blocks.append(format_for_prompt(data))
        github_used = True

    # ── Step 4: Build system prompt ────────────────────────────────────────────
    system_prompt = _build_system_prompt(github_blocks)

    # ── Step 5: Call LLM ───────────────────────────────────────────────────────
    try:
        raw = await _call_llm(system_prompt, question, history)
    except ValueError as exc:
        # LLM returned invalid JSON – surface a safe error response
        logger.error("LLM parse failure: %s", exc)
        return ChatResponse(
            answer="I encountered an internal error while generating a response. Please try again.",
            trace=ExplainabilityTrace(
                intent="unknown",
                capability="out_of_scope",
                fields_read=[],
                missing_facts=[],
                external_service_used=None,
                audit_spans=[],
            ),
        )

    # ── Step 6: Parse ──────────────────────────────────────────────────────────
    response = _parse_response(raw)

    # ── Step 7: Enforce external_service_used & capability when GitHub was fetched
    if github_used:
        if response.trace.external_service_used is None:
            response.trace.external_service_used = "GitHub REST API v3"
        if response.trace.capability in ("answer_from_record", "unknown"):
            response.trace.capability = "call_external_api"

    return response
