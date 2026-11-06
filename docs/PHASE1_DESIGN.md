# Phase 1: Architecture, Data Schema, and Integrations

## 1. Personal Profile Record & Schema
- **Data File**: `data/profile.json`
- **Schema File**: `data/profile.schema.json`
- **Owner**: Amirreza Dorosti
- **Student Number**: `403110466`
- **GitHub Username**: `Dorostwef`
- **Visibility Rules**:
  - All public profile fields marked `"visibility": "public"`.
  - Phone number explicitly marked `"visibility": "restricted"` and `"status": "refuse_to_share"`.
- **Authority Guardrails**:
  - Refuses to book meetings or calendar events.
  - Refuses to send emails.
  - Refuses to speak on behalf of Sharif University of Technology.
  - Refuses to disclose phone number.
- **Intentionally Missing Fields**:
  - `projects[compiler].deployment_date`: `null` (tests refusal on unrecorded facts).
  - `projects[compiler].team_size`: `null`.
  - Multiple projects included (`compiler`, `raft_kv`, `neural_search`) to ensure ambiguous queries like *"Tell me about my project"* trigger a single clarifying question.

---

## 2. GitHub API Connector Specification

### Service Name in Trace
`"GitHub REST API v3"`

### Target Endpoints
1. **Repository Meta**:
   ```http
   GET https://api.github.com/repos/Dorostwef/{repo}
   Accept: application/vnd.github.v3+json
   User-Agent: AboutMe-AI-Agent
   ```
   - **Fields extracted**: `stargazers_count`, `forks_count`, `updated_at`, `language`, `open_issues_count`.

2. **Recent Commit Activity**:
   ```http
   GET https://api.github.com/repos/Dorostwef/{repo}/commits?per_page=1
   ```
   - **Fields extracted**: `sha` (shortened to 7 chars), `commit.message`, `commit.committer.date`.

### Resilience & Fallback
- If `GITHUB_TOKEN` is present in environment variables, add `Authorization: Bearer <GITHUB_TOKEN>` (5,000 requests/hr).
- If unauthenticated (60 requests/hr), or if the repo is private/unavailable, the connector returns a clean fallback status so the agent can inform the visitor without crashing:
  ```json
  {
    "service": "GitHub REST API v3",
    "status": "unavailable_or_not_found",
    "note": "Public repository stats could not be reached"
  }
  ```

---

## 3. Idea 1: Trace Inspector / Grounding Auditor (Creative Feature)

### Core Mechanism
The backend agent returns answers augmented with segment-level audit spans:

```json
{
  "intent": "project_summary",
  "capability": "answer_from_record",
  "fields_read": [
    "projects[0].name",
    "projects[0].summary",
    "projects[0].tech_stack",
    "projects[0].deployment_date"
  ],
  "missing_facts": [
    "projects[0].deployment_date is null in record"
  ],
  "audit_spans": [
    {
      "segment": "MiniLang is an optimizing compiler for a statically-typed toy language.",
      "source": "projects[compiler].summary",
      "type": "record_grounded"
    },
    {
      "segment": "It is built with Rust and targets x86-64 assembly.",
      "source": "projects[compiler].tech_stack",
      "type": "record_grounded"
    },
    {
      "segment": "The record does not list a deployment date.",
      "source": "projects[compiler].deployment_date",
      "type": "missing_fact_notice"
    }
  ],
  "answer": "MiniLang is an optimizing compiler for a statically-typed toy language. It is built with Rust and targets x86-64 assembly. The record does not list a deployment date."
}
```

### UI Interaction (Grounding Auditor Panel)
1. **Interactive Sentence Highlighting**:
   - Hovering over any sentence in the response highlights its source in the **Explainability Drawer**.
   - Color indicators:
     - 🟢 **Green**: Grounded directly from `profile.json`.
     - 🔵 **Blue**: Grounded from external live API (`GitHub REST API v3`).
     - 🟠 **Amber**: Missing fact or unrecorded field acknowledgment.
     - 🔴 **Red**: Guardrail refusal (e.g., requested phone number or unauthorized authority).
2. **One-Click Trace Copy**:
   - Visitors and course evaluators can click a single button to copy the exact markdown trace required for the 3 submission reports.
