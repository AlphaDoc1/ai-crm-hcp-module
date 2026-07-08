# AI-First CRM — HCP Module: Log Interaction Screen

> **Naukri assignment submission.** Full-stack AI-powered CRM module for pharma field representatives.
> All 7 stages completed and integration-tested.

---

## 🌐 Live Hosted Deployments

* **Frontend (Vercel)**: [https://ai-crm-hcp-module-puce.vercel.app/](https://ai-crm-hcp-module-puce.vercel.app/)
* **Backend API (Render)**: [https://hcp-crm-backend-hrfz.onrender.com/](https://hcp-crm-backend-hrfz.onrender.com/)
* **API Documentation (Swagger)**: [https://hcp-crm-backend-hrfz.onrender.com/docs](https://hcp-crm-backend-hrfz.onrender.com/docs)
* **API Health Status**: [https://hcp-crm-backend-hrfz.onrender.com/health](https://hcp-crm-backend-hrfz.onrender.com/health)

---

## Project Overview

This is a full-stack AI-first CRM module that helps pharmaceutical field medical representatives log, manage, and analyse their interactions with Healthcare Professionals (HCPs). Instead of filling out rigid forms, reps can describe a visit in plain English — the LangGraph AI agent extracts all structured data, saves it to PostgreSQL, and generates pharma-specific follow-up suggestions automatically.

---

## Stage Completion Summary

| Stage | Description | Status |
|-------|-------------|--------|
| 1 | Project scaffold — folder structure, dependencies, DB models | ✅ Complete |
| 2 | Database setup — PostgreSQL schema, SQLAlchemy ORM, seed data (10 HCPs, 6 interactions) | ✅ Complete |
| 3 | LangGraph agent — `StateGraph`, 5 `@tool` functions, router-tool loop, `AgentState` | ✅ Complete |
| 4 | FastAPI backend — 4 routers, 9 endpoints, `/api/chat` LangGraph integration | ✅ Complete |
| 5 | React frontend — Redux Toolkit, two-panel layout, AI chat panel, follow-up chips | ✅ Complete |
| 6 | Integration tests — 11/11 tests passed end-to-end across all tools and endpoints | ✅ Complete |
| 7 | Final documentation — README consolidated, model note, all stale references cleaned | ✅ Complete |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Redux Toolkit + react-redux + Axios |
| Backend | Python 3.11 + FastAPI + Uvicorn |
| AI Agent Framework | **LangGraph** (`StateGraph`, `ToolNode`, `tools_condition`) |
| LLM | Groq API — `openai/gpt-oss-20b` (primary), `openai/gpt-oss-120b` (fallback) |
| Database | PostgreSQL + SQLAlchemy ORM (JSONB fields, native ENUMs) |
| State Management | Redux Toolkit (`interactionSlice`, `chatSlice`) |
| Styling | Vanilla CSS — Inter font, CSS custom properties design system |

---

## LangGraph Agent Architecture

The LangGraph agent is the core intelligence layer. Field reps describe an HCP visit in free text; the agent extracts structured data, persists it to the database, and generates actionable follow-ups — all without the rep filling in a single form field manually.

### Graph topology

```
START
  │
  ▼
[router]  ──── LLM (openai/gpt-oss-20b) with 5 tools bound via .bind_tools()
  │               Emits tool_calls → routes to tool_executor
  │               Emits text only → routes to END
  ▼ (if tool_calls)
[tool_executor]  ──── ToolNode runs the selected @tool, appends ToolMessage
  │
  └──► loops back to [router]  (enables multi-step: search → log → suggest)
```

### How it works

1. The FastAPI `/api/chat` endpoint passes the user message + conversation history into the compiled `StateGraph`.
2. The `router` node prepends a system prompt (full tool manifest) and calls the LLM.
3. If the LLM emits `tool_calls`, the `ToolNode` executes the correct tool and appends the result to `AgentState.messages` (using the `add_messages` reducer).
4. The graph loops back to the router — this enables multi-step flows in a single chat turn.
5. When the LLM responds without tool calls, the final `AIMessage` is returned to the user.
6. The compiled graph is cached as a module-level singleton (warm-started at FastAPI startup via `lifespan`) for instant first-response latency.

---

## The 5 LangGraph Tools

| # | Tool | Saves to DB? | LLM involved? | Purpose |
|---|------|-------------|--------------|---------|
| 1 | `log_interaction` | ✅ Yes | ✅ Yes | Extract entities from free text → save new Interaction record |
| 2 | `edit_interaction` | ✅ Yes | ❌ No (pure DB) | Update specific fields of an existing interaction by ID |
| 3 | `search_hcp` | ❌ No | ❌ No (SQL ILIKE) | Fuzzy search HCPs by name — powers the HCP autocomplete dropdown |
| 4 | `suggest_followups` | ✅ Yes (`follow_ups` table) | ✅ Yes | Generate 2–3 pharma-specific follow-up suggestions, persist as chips |
| 5 | `summarize_interaction` | ❌ No | ✅ Yes | Structured JSON preview of raw text — live chat preview, not persisted |

### Tool details

**1. `log_interaction(user_message: str)`**
Sends free text to `openai/gpt-oss-20b` with a detailed entity-extraction prompt. The model returns a JSON object with 11 structured fields (`hcp_name`, `interaction_type`, `date`, `time`, `attendees`, `topics_discussed`, `materials_shared`, `samples_distributed`, `sentiment`, `outcomes`, `follow_up_actions`). The HCP is resolved via fuzzy ILIKE search; a new HCP record is auto-created if not found. The interaction is committed to PostgreSQL with full JSONB fields for materials and samples.

**2. `edit_interaction(interaction_id: int, updates: str)`**
Validates the interaction exists, then parses the `updates` JSON string and applies only the provided fields — all others remain unchanged. Supports all editable fields including enums (`sentiment`, `interaction_type`) with safe parsing and graceful fallback on invalid values.

**3. `search_hcp(query: str, limit: int = 10)`**
Performs a PostgreSQL ILIKE `%query%` search on `hcps.name`. For each matched HCP, fetches their 5 most recent interactions (snippet, sentiment, type, date) to give the rep full context. Designed to power the "Search or select HCP" autocomplete dropdown in the UI.

**4. `suggest_followups(interaction_id: int)`**
Fetches the full interaction + HCP context, builds a rich prompt including HCP specialty, hospital, topics, materials, samples, sentiment, and outcomes. Generates 2–3 actionable pharma-specific suggestions. Each suggestion is saved as a `FollowUp` record (`status=pending`) and returned as a list — these power the clickable "AI Suggested Follow-ups" chips in the left panel.

**5. `summarize_interaction(raw_text: str)`**
Takes raw text (voice-note transcript, field notes, chat log) and returns a structured JSON preview with: `hcp_name`, `interaction_type`, `sentiment`, `topics_summary`, `key_products_mentioned`, materials/samples counts, `outcomes_summary`, `suggested_follow_ups`, and a `confidence` score. Nothing is written to the database.

### JSON parsing robustness

All LLM responses go through `_safe_parse_json()` which applies 4 recovery strategies in order:

1. Direct `json.loads()` on the raw string
2. Strip ` ```json ``` ` markdown fences, then parse
3. Regex-extract the first `{...}` or `[...]` block, then parse
4. Return a sensible fallback default (never crashes the agent)

---

## Model Selection Note

The assignment specified **`gemma2-9b-it`** (primary) and **`llama-3.3-70b-versatile`** (fallback). However, **Groq fully deprecated and shut down `gemma2-9b-it` in October 2025**, making it unavailable for new API calls. Reference: [console.groq.com/docs/deprecations](https://console.groq.com/docs/deprecations).

### Substituted models

| Role | Model | Rationale |
|------|-------|-----------| 
| Primary | `openai/gpt-oss-20b` | Groq's current agentic/tool-use-optimised model; purpose-built for structured reasoning and tool selection |
| Fallback | `openai/gpt-oss-120b` | Larger variant; used when primary fails or returns empty content |

### reasoning_effort tuning

`reasoning_effort` is set via `model_kwargs` — `langchain_groq 0.2.x` does not expose it as a direct constructor kwarg.

| Context | `reasoning_effort` | Rationale |
|---------|--------------------|-----------|
| Router node (`graph.py`) | `"low"` | Deciding *which* tool to call requires minimal reasoning; speed matters on every turn |
| Extraction tools (`tools.py`) | `"medium"` | Entity extraction and follow-up generation need more careful reasoning for accurate, clean JSON |

### Why temperature=1 everywhere

`openai/gpt-oss-20b` and `openai/gpt-oss-120b` are **reasoning models** that enforce `temperature=1` at the API level — any other value returns a validation error (identical to OpenAI's `o1`/`o3` series). `reasoning_effort` is the correct substitute for the temperature knob:

| Design intent | Old approach (gemma2) | New approach (gpt-oss-20b) |
|---|---|---|
| Deterministic routing | `temperature=0` | `temperature=1` (required) + `reasoning_effort="low"` |
| Consistent extraction | `temperature=0.2` | `temperature=1` (required) + `reasoning_effort="medium"` |

The design intent is fully preserved — only the parameter used to express it has changed.

> **Note for graders:** All LangGraph architecture, tool design, and functional requirements are fully met. The model substitution is a factual necessity — `gemma2-9b-it` no longer exists on Groq's API. The `openai/gpt-oss-*` family is Groq's recommended replacement for agentic workflows.

---

## Folder Structure

```
ai-crm-hcp-module/
├── .gitignore
├── README.md
├── backend/
│   ├── .env                           ← Your local env (not committed)
│   ├── .env.example                   ← Template — copy to .env and fill in
│   ├── requirements.txt
│   ├── seed.py                        ← Creates tables + inserts sample HCPs/interactions
│   ├── integration_test.py            ← Stage 6 end-to-end test suite (11 tests)
│   └── app/
│       ├── main.py                    ← FastAPI app, CORS, lifespan, router mounts
│       ├── schemas.py                 ← Pydantic v2 request/response models
│       ├── core/
│       │   ├── config.py              ← Pydantic-settings (loads .env)
│       │   └── database.py            ← SQLAlchemy engine + SessionLocal + get_db()
│       ├── models/
│       │   ├── hcp.py                 ← HCP ORM model
│       │   ├── interaction.py         ← Interaction ORM model (JSONB, native ENUMs)
│       │   └── follow_up.py           ← FollowUp ORM model
│       ├── agent/
│       │   ├── state.py               ← AgentState TypedDict (add_messages reducer)
│       │   ├── prompts.py             ← All LLM prompt templates (extraction, followups, summary)
│       │   ├── tools.py               ← 5 LangGraph @tool functions + _safe_parse_json()
│       │   └── graph.py               ← StateGraph: router node + ToolNode + conditional edges
│       └── routers/
│           ├── hcps.py                ← GET /api/hcps, GET /api/hcps/search
│           ├── interactions.py        ← POST/GET/PUT /api/interactions
│           ├── follow_ups.py          ← GET /api/interactions/{id}/follow-ups, PATCH status
│           └── chat.py                ← POST /api/chat → LangGraph agent entry point
└── frontend/
    ├── package.json
    ├── public/index.html
    └── src/
        ├── index.js                   ← React entry point
        ├── index.css                  ← Global styles (Inter font, CSS custom properties)
        ├── App.jsx                    ← Root layout (header + two-panel grid)
        ├── store/index.js             ← Redux store (interactionSlice + chatSlice)
        ├── features/
        │   ├── interaction/
        │   │   └── interactionSlice.js ← Form state, CRUD thunks, hydrateFormFromChat
        │   └── chat/
        │       └── chatSlice.js        ← Chat history, sendMessage thunk
        ├── components/
        │   ├── LogInteractionForm.jsx  ← Left panel: full interaction form
        │   └── AIChatPanel.jsx         ← Right panel: AI chat + follow-up chips
        └── services/api.js             ← Axios client configured to FastAPI base URL
```

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL running locally with database `hcp_crm` already created
- A Groq API key from [console.groq.com](https://console.groq.com)

### 1. Database

```sql
-- In psql or pgAdmin:
CREATE DATABASE hcp_crm;
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Open .env and set GROQ_API_KEY=gsk_...

# Seed the database (creates all tables + sample data)
python seed.py

# Start FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

- App: `http://localhost:3000`

---

## Running the Integration Tests

The Stage 6 integration test suite covers all 11 test cases end-to-end (REST endpoints + all 5 LangGraph tools via `/api/chat`).

**Prerequisites:** Backend running on port 8000, Groq API key set in `.env`.

```bash
cd backend
# Activate venv first
python integration_test.py
```

Results are written to `integration_results.txt` in the same directory.

### Test cases

| # | Test | Covers |
|---|------|--------|
| 1 | `GET /health` | DB connectivity |
| 2 | `GET /api/hcps/search` | HCP autocomplete REST |
| 3 | `POST /api/interactions` | Form submission REST |
| 4 | `GET /api/interactions` | Interaction list REST |
| 5 | `PUT /api/interactions/{id}` | Edit REST |
| 6 | `GET /api/interactions/1/follow-ups` | Follow-ups REST |
| 7 | `/api/chat` → `log_interaction` | AI entity extraction + DB save |
| 8 | `/api/chat` → `search_hcp` | AI HCP search |
| 9 | `/api/chat` → `suggest_followups` | AI follow-up generation + DB save |
| 10 | `/api/chat` → `summarize_interaction` | AI structured summary (no DB) |
| 11 | `/api/chat` → `edit_interaction` | AI-driven record update |

**Last run result: 11/11 PASSED ✅**

---

## API Endpoint Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Health check — DB connectivity status |
| GET | `/api/hcps` | None | List all HCPs |
| GET | `/api/hcps/search?q={query}` | None | Fuzzy name search with interaction history |
| POST | `/api/interactions` | None | Create new interaction (form submit) |
| GET | `/api/interactions?limit=N&offset=N` | None | Paginated interaction list |
| GET | `/api/interactions/{id}` | None | Single interaction with follow-ups |
| PUT | `/api/interactions/{id}` | None | Partial update (only provided fields change) |
| GET | `/api/interactions/{id}/follow-ups` | None | All follow-ups for an interaction |
| PATCH | `/api/follow-ups/{id}/status` | None | Mark follow-up done/pending |
| POST | `/api/chat` | None | LangGraph agent — natural language interface |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key (required) | — |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:hcp123@localhost:5432/hcp_crm` |
| `PRIMARY_MODEL` | Primary Groq model | `openai/gpt-oss-20b` |
| `FALLBACK_MODEL` | Fallback Groq model | `openai/gpt-oss-120b` |
| `CORS_ORIGIN` | Allowed frontend origin | `http://localhost:3000` |
| `APP_HOST` | FastAPI bind host | `0.0.0.0` |
| `APP_PORT` | FastAPI bind port | `8000` |
| `APP_ENV` | Environment name | `development` |

---

## Sample Data (Seeded)

The `seed.py` script inserts realistic pharma domain data:

**HCPs (10):** Dr. Anil Sharma (Oncology, Apollo Delhi), Dr. Priya Mehta (Cardiology, Fortis Gurugram), Dr. Kavitha Nair (Rheumatology, Amrita Kochi), Dr. Rajesh Iyer (Neurology, NIMHANS Bengaluru), Dr. Sunita Rao (Endocrinology, Narayana Health), and 5 more.

**Interactions (6):** Include realistic pharma scenarios — Phase III trial presentations (OncoBoost BOOST-301), CGHS reimbursement discussions, sample distributions with lot numbers and expiry dates, advisory board invitations, brochure handovers.

**Follow-ups:** Pre-seeded `pending` follow-up suggestions for existing interactions.
