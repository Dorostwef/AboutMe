# Joe King — AI-Native Personal Page

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Sharif University](https://img.shields.io/badge/Sharif%20University-CE4051-blue)](https://sharif.edu)

An AI-native personal portfolio and query engine designed around **strict deterministic grounding, zero hallucination, guardrail boundaries, and explainability**. Built for the **AI-Native Systems Design (CE4051)** assignment at **Sharif University of Technology**.

---

## 🌟 Key Architecture & Capabilities

1. **Zero Hallucination & Strict Grounding:**
   The AI assistant knows **nothing** about Joe King other than what is explicitly declared in [`data/profile.json`](./data/profile.json) or retrieved from the live GitHub REST API. If a fact is unlisted (e.g. `deployment_date` or `team_size` in certain projects), it refuses to estimate or guess.

2. **Core Intent Handling:**
   - **Project Summaries:** Provides verified overviews of projects (`MiniLang Compiler`, `RaftKV Store`, `Neural Code Search`).
   - **Curated Reading Suggestions:** Recommends technical literature tied to completed courses and active projects.
   - **Job Fit Evaluation:** Objectively compares visitor-described job roles against Joe King's recorded core competencies.

3. **Deterministic Guardrails & Authority Limits:**
   - **Private Data Protection:** Phone number requests are strictly intercepted and refused.
   - **Authority Boundaries:** Refuses requests to book meetings, send emails, or speak on behalf of Sharif University of Technology.
   - **Clarification Flow:** Vague queries (*"Tell me about my project"*) trigger exactly one clarifying follow-up question listing candidate projects rather than guessing.

4. **External API Integration:**
   - Connects live to the **GitHub REST API v3** to fetch repository metadata, star counts, and latest commit messages/timestamps for repositories under [`Dorostwef`](https://github.com/Dorostwef).
   - Reports `external_service_used: "GitHub REST API v3"` in the explainability trace.

5. **Creative Feature: Interactive Grounding Auditor (Idea 1):**
   - Every response comes with sentence-level **`audit_spans`**.
   - Hovering over sentences visually maps them to their source:
     - 🟢 **Record Grounded:** Sourced directly from `profile.json`.
     - 🔵 **API Grounded:** Fetched live from GitHub REST API v3.
     - 🟠 **Missing Fact Notice:** Explicit acknowledgment of unlisted data.
     - 🔴 **Guardrail Refusal:** Blocked by authority boundaries or privacy rules.
   - Includes a **One-Click Trace Copy** button formatted for reports.

---

## 📁 Repository Structure

```
AboutMe/
├── backend/
│   ├── config.py                 # Central config, env vars & proxy normalizer
│   ├── main.py                   # FastAPI app, static mounts, CORS & endpoints
│   ├── schemas.py                # Pydantic schemas (ChatRequest, AuditSpan, Trace)
│   └── services/
│       ├── profile_loader.py     # Safe profile.json loader & privacy filter
│       ├── github_service.py     # Async GitHub REST API v3 client
│       └── llm_engine.py         # Grounded prompt builder, LLM caller & trace parser
├── data/
│   ├── profile.json              # Joe King's authoritative profile record
│   └── profile.schema.json       # Formal JSON Schema (Draft 2020-12)
├── frontend/
│   ├── index.html                # Responsive UI with Guardrails banner & Chat
│   ├── styles.css                # Dark-mode modern styling
│   └── app.js                    # Chat controller & Grounding Auditor drawer
├── Dockerfile                    # Production container spec for Hamravesh Darkube
├── .dockerignore                 # Excludes .venv, git, and local cache
├── .gitignore                    # Ensures secrets and local environments never leak
├── requirements.txt              # Production Python dependencies
└── .env.example                  # Environment variable template
```

---

## 🚀 Quickstart (Local Development)

### 1. Clone & Set Up Environment

```bash
git clone git@github.com:Dorostwef/AboutMe.git
cd AboutMe

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-20b
GITHUB_TOKEN=ghp_your_github_token_here
PORT=8000
```

### 3. Run the Server

```bash
python -m backend.main
```

Open your browser at **`http://localhost:8000`**.

---

## 🧪 Testing the API via cURL

### Good Answer & Missing Fact Acknowledgment
```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Tell me about the MiniLang compiler project."}' | python3 -m json.tool
```

### Live GitHub API Query
```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the latest commit on the Dedit repository on GitHub?"}' | python3 -m json.tool
```

### Refusal (Phone Number)
```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is Joe King'\''s phone number?"}' | python3 -m json.tool
```

### Clarifying Follow-Up
```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Tell me about your project."}' | python3 -m json.tool
```

---

## 🐳 Deployment on Hamravesh (Darkube)

This repository is pre-configured for automated deployment on **Hamravesh Darkube**:

1. Log in to [console.hamravesh.com](https://console.hamravesh.com).
2. Create a new app under **Darkube** and select this GitHub repository (`Dorostwef/AboutMe`).
3. Set the Environment Variables:
   - `GROQ_API_KEY`
   - `OPENAI_BASE_URL`
   - `OPENAI_MODEL`
   - `GITHUB_TOKEN`
   - `PORT=8000`
4. Deploy the application and assign a public domain.

---

## 📄 License & Attribution

Developed for **Sharif University of Technology — AI-Native Systems Design (CE4051)**.
Owner: **Joe King** (GitHub: [`Dorostwef`](https://github.com/Dorostwef)).
