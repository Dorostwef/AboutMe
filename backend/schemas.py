"""
schemas.py
──────────
Pydantic data models shared across the entire backend.

Naming conventions
──────────────────
  ChatRequest       – what the frontend POST-body looks like.
  AuditSpan         – a single sentence from the answer tagged with its source
                      (the key data structure for Idea 1: Grounding Auditor).
  ExplainabilityTrace – the full explainability / audit record for one response.
  ChatResponse      – the complete API response returned to the frontend.
  PublicProfile     – the sanitised view of profile.json sent by GET /api/profile.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Allowed enumeration values ─────────────────────────────────────────────────
# Keeping them as plain strings (not Enum) so the JSON output stays readable
# without extra serialisation steps, and the LLM can produce them naturally.

VALID_INTENTS = frozenset({
    "project_summary",
    "reading_suggestion",
    "job_fit",
    "clarification",
    "refusal",
    "github_activity",
    "general_info",
    "unknown",
})

VALID_CAPABILITIES = frozenset({
    "answer_from_record",
    "call_external_api",
    "refuse_fact",
    "ask_clarification",
    "out_of_scope",
})

VALID_SPAN_TYPES = frozenset({
    "record_grounded",
    "api_grounded",
    "missing_fact_notice",
    "guardrail_refusal",
})


# ── Request ────────────────────────────────────────────────────────────────────

class ConversationTurn(BaseModel):
    """One prior exchange: visitor question + assistant answer."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class ChatRequest(BaseModel):
    """Body for POST /api/chat."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The visitor's natural-language question.",
    )
    conversation_history: list[ConversationTurn] = Field(
        default_factory=list,
        description="Prior turns for multi-turn context (oldest first).",
    )


# ── Grounding Auditor data structures ──────────────────────────────────────────

class AuditSpan(BaseModel):
    """
    A sentence (or phrase) from the answer, tagged with its exact data source.
    This is the core data structure powering Idea 1 (Trace Inspector).

    Fields
    ──────
    segment   – The verbatim sentence from the answer text.
    source    – Either:
                  • A JSON-path into profile.json  (e.g. "projects[compiler].summary")
                  • The external service name       (e.g. "GitHub REST API v3")
    type      – One of:
                  • "record_grounded"    → fact came from profile.json
                  • "api_grounded"       → fact came from a live external API call
                  • "missing_fact_notice"→ field exists in record but its value is null
                  • "guardrail_refusal"  → request crossed a guardrail boundary
    """
    segment: str = Field(..., description="Verbatim sentence from the answer.")
    source: str = Field(
        ...,
        description="JSON path in profile.json or external service name.",
    )
    type: str = Field(
        ...,
        description="record_grounded | api_grounded | missing_fact_notice | guardrail_refusal",
    )


class ExplainabilityTrace(BaseModel):
    """
    Full audit trail for one LLM response.
    Directly satisfies the assignment's Explainability (0.30 pts) requirement.
    """
    intent: str = Field(
        ...,
        description=(
            "project_summary | reading_suggestion | job_fit | "
            "clarification | refusal | github_activity | general_info | unknown"
        ),
    )
    capability: str = Field(
        ...,
        description=(
            "answer_from_record | call_external_api | "
            "refuse_fact | ask_clarification | out_of_scope"
        ),
    )
    fields_read: list[str] = Field(
        default_factory=list,
        description="JSON paths actually consulted from profile.json.",
    )
    missing_facts: list[str] = Field(
        default_factory=list,
        description="Fields that were null or absent in the record and therefore not reported.",
    )
    external_service_used: Optional[str] = Field(
        default=None,
        description="e.g. 'GitHub REST API v3', or null when no external call was made.",
    )
    audit_spans: list[AuditSpan] = Field(
        default_factory=list,
        description="Sentence-level grounding tags (powers the Grounding Auditor UI).",
    )


# ── Response ───────────────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    """Full response returned by POST /api/chat."""
    answer: str = Field(..., description="The human-readable answer to the visitor's question.")
    trace: ExplainabilityTrace


# ── Public profile snapshot (GET /api/profile) ─────────────────────────────────

class PublicProfile(BaseModel):
    """
    Sanitised view of profile.json with all restricted fields removed.
    Safe to send to any browser without leaking private data.
    """
    name: str
    role: str
    institution: str
    location: str
    email: str
    github_username: str
    courses: list[dict[str, Any]]
    projects: list[dict[str, Any]]
    reading_recommendations_catalog: list[dict[str, Any]]
    job_fit_profile: dict[str, Any]
    guardrails_and_limits: dict[str, Any]
