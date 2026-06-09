---
type: analysis
question: "Final developer scope for Epic 2 — Tenant Onboarding and Pipeline 2"
date: 2026-06-05
tags: [epic-2, onboarding, pipeline-2, scope, developer-spec]
status: FINAL — approved for Sprint 2 development
---

# Epic 2 — Developer Scope

**What this builds:** Chat-based tenant onboarding (Stage 3) that feeds a 4-step background pipeline producing all scoring configuration used by the Rating Agent.

---

## Scope Boundary

**All files live inside `modules/tenant_onboarding/`. Nothing outside.**

Out of scope for this epic:
- Epic 1 — auth, Clerk JWT, RBAC, multi-tenancy shell
- Epic 3 — lead ingestion, channel connectors, webhooks, two-stage filter
- Epic 4 — Pipeline 1 core: enrichment, signal extraction, Rating Agent runtime, scoring execution
- Epic 5 — delivery, salesperson UI, dashboard, reporting, lead feed
- Frontend chat UI — consumed via the API; not built here

---

## Architectural Decisions (Locked)

| # | Decision | Resolution |
|---|---|---|
| 1 | Signal evaluation in Rating Agent | **Option A** — Signal Extractor (Epic 4) pre-computes signal values and passes a `{signal_values: {dim: float}}` dict to the Rating Agent. The Rating Agent does not evaluate raw event JSON. `rating_template.py` uses `{signal_values}` as a placeholder — no signal extraction logic in the prompt. |
| 2 | Tone scope in Rating Agent | **Excluded** — `tone` is stored in PersonaObject but is not injected into `rating_template.py`. Rating Agent output has no `salesperson_note` field. |
| 3 | Prompt building | **Inlined into `pipeline.py` Step 4** — no separate `prompt_builder.py` file. Step 4 reads `rating_template.py`, fills placeholders with PersonaObject + IcpDefinition + Signal[], validates, stores in `prompt_registry`. |
| 4 | Question set | **Single hybrid — 11 questions, no routing.** No selector question. No B2B/B2C/Hybrid split. Persona Agent infers business type from answers. |

---

## Folder Structure

```
modules/tenant_onboarding/
├── __init__.py
├── router.py               FastAPI onboarding API endpoints
├── worker.py               Registers Pipeline 2 as a background job
├── pipeline.py             4-step orchestrator + Step 4 prompt fill + retry policy
├── onboarding_agent.py     Chat session manager — Phase 2 Q&A
├── doc_processor.py        Phase 1 — PDF/deck upload → field extraction via LLM
├── questions.py            Single hybrid question set (11 questions)
├── prompt_registry.py      Prompt versioning: store, activate, rollback
├── persona_cache.py        TTLCache(15 min) + Postgres NOTIFY invalidation
├── activation.py           Stage 5 readiness check + FIFO lead queue drain
├── sonnet_client.py        Anthropic claude-sonnet-4-6 wrapper
├── agents/
│   ├── __init__.py
│   ├── persona_agent.py    Pipeline 2 Step 1
│   ├── icp_agent.py        Pipeline 2 Step 2
│   └── signal_agent.py     Pipeline 2 Step 3
├── prompts/
│   ├── __init__.py
│   ├── persona_system.py   Persona Agent system prompt (static)
│   ├── icp_system.py       ICP Agent system prompt (static)
│   ├── signal_system.py    Signal Agent system prompt (static)
│   └── rating_template.py  Rating Agent prompt template (filled per tenant)
├── schemas/
│   ├── __init__.py
│   ├── persona.py          PersonaObject Pydantic model
│   ├── icp.py              IcpDefinition Pydantic model
│   ├── signal.py           Signal[] Pydantic model
│   └── onboarding.py       OnboardingSession + answer schemas
├── db/
│   ├── __init__.py
│   ├── models.py           SQLAlchemy models
│   └── repository.py       Async CRUD operations
└── tests/
    ├── unit/
    └── integration/
```

---

## Task List

Tasks are ordered by dependency. Each task must be complete before dependent tasks begin.

### Group A — Foundation & Chat Interface

| Task | File(s) | Responsibility | Depends on |
|---|---|---|---|
| A1 | `db/models.py` | SQLAlchemy ORM models: `Tenant`, `OnboardingSession`, `Persona`, `IcpDefinition`, `Signal`, `PromptRegistry`, `ChannelConnection` | — |
| A2 | `db/repository.py` | Async CRUD for all A1 models. No business logic. | A1 |
| A3 | `questions.py` | `HYBRID_QUESTIONS`: list of 11 dicts with fields `id`, `text`, `maps_to`, `skippable`. No routing. | — |
| A4 | `schemas/*.py` | Pydantic v2 models: `PersonaObject`, `IcpDefinition`, `Signal`, `OnboardingSession`, `QuestionAnswer` | — |
| A5 | `sonnet_client.py` | Async wrapper for `claude-sonnet-4-6`. Accepts system + user messages; returns structured JSON. Retries on rate limit (max 3, exponential backoff). Raises `SonnetClientError` on hard failure. | — |
| A6 | `doc_processor.py` | Phase 1: accepts uploaded file (PDF/PPTX/DOCX), calls Sonnet to extract structured answers, returns `dict[question_id, str]` for matched questions only. | A3, A5 |
| A7 | `onboarding_agent.py` | Phase 2: manages chat session state; iterates `HYBRID_QUESTIONS` sequentially; skips questions pre-answered by `doc_processor`; persists session state per tenant; marks session complete when all questions answered or skipped; emits warning if > 3 skipped. | A2, A3, A4, A6 |
| A8 | `router.py` | FastAPI endpoints: `POST /onboarding/session` (start), `POST /onboarding/answer` (submit one answer), `GET /onboarding/status` (current stage + pipeline progress), `POST /onboarding/activate` (trigger Stage 5). All routes require authenticated tenant. | A7 |

### Group B — Pipeline 2 Agents

Pipeline 2 runs asynchronously after the onboarding session is submitted. Steps 1→2→3 are strictly serial. Step 4 runs immediately after Step 3.

| Task | File(s) | Responsibility | Depends on |
|---|---|---|---|
| B1 | `prompts/persona_system.py` + `agents/persona_agent.py` | Step 1: sends onboarding answers to Sonnet with persona system prompt → receives and validates `PersonaObject` JSON → stores via repository. Validates: `scoring_weights` sum = 1.0; `hot_min` > `warm_min`. | A2, A4, A5 |
| B2 | `prompts/icp_system.py` + `agents/icp_agent.py` | Step 2: sends `PersonaObject` to Sonnet with ICP system prompt → receives and validates `IcpDefinition` JSON → stores. Input: output of B1. | B1 |
| B3 | `prompts/signal_system.py` + `agents/signal_agent.py` | Step 3: sends `PersonaObject` + `IcpDefinition` to Sonnet with signal system prompt → receives and validates `Signal[]` JSON → stores. Per-dimension signal weights must sum to 1.0. | B2 |
| B4 | `pipeline.py` + `worker.py` | Orchestrates Steps 1→2→3→4 in sequence. **Step 4 (inlined):** reads `rating_template.py`, fills `{persona}`, `{icp}`, `{signal_definitions}` placeholders, stores filled prompt in `prompt_registry` as a new version with `is_active = True`. Retry policy: 1 retry per step on failure. On 2nd failure: halt pipeline, set `pipeline_status = failed`, alert admin, notify tenant. Only the failing tenant's pipeline halts — others unaffected. | B1, B2, B3, C1 |

### Group C — Prompt Template, Registry & Activation

| Task | File | Responsibility | Depends on |
|---|---|---|---|
| C1 | `prompts/rating_template.py` | Rating Agent system prompt template. Static scaffolding with three variable placeholders: `{persona}` (PersonaObject JSON), `{icp}` (IcpDefinition JSON), `{signal_definitions}` (Signal[] JSON). **No `{tone}` placeholder. No `salesperson_note` in output schema.** Signal values passed at runtime by Epic 4 Signal Extractor — not in this template. | — |
| C2 | `prompt_registry.py` | `store(tenant_id, prompt_str, pipeline_run_id) → version_id`: saves new prompt, sets `is_active = True`, deactivates prior version. `rollback(tenant_id, version_id)`: reactivates a prior version. `get_active(tenant_id) → str`: returns current active prompt. | A1, A2 |
| C3 | `persona_cache.py` | `TTLCache(maxsize=500, ttl=900)`. Cache key: `(tenant_id, prompt_template_version)`. Listens for Postgres `NOTIFY tenant_persona_updated` → force-flushes affected tenant key. Used by Epic 4 Rating Agent to avoid per-request DB reads. | C2 |
| C4 | `activation.py` | Stage 5 logic. Readiness check: (1) pipeline status = complete AND (2) ≥ 1 `ChannelConnection.status = active` for this tenant. If both pass: atomically sets `tenant.status = active`, enables Pipeline 1, drains FIFO queue of `captured` leads in order. If pipeline still running: returns pending status. If pipeline failed: returns failure reason, directs tenant to resubmit onboarding. | A2, C2 |

### Group T — Tests

| Task | What it covers | Depends on |
|---|---|---|
| T1 | **Unit tests:** `PersonaObject` weight sum validation; `hot_min > warm_min` enforcement; Signal[] per-dimension weight sum; `prompt_registry` rollback restores correct version; `persona_cache` TTL expiry and force-flush via NOTIFY. | B1–B3, C2, C3 |
| T2 | **Integration test:** Full Pipeline 2 run against a fixture `OnboardingSession` → assert `Persona`, `IcpDefinition`, `Signal[]` all stored → assert `prompt_registry` has one active prompt for the tenant → assert `activation.py` flips `tenant.status = active` when readiness conditions met. | B4, C4 |

---

## Summary

| Group | Tasks | Files |
|---|---|---|
| A — Foundation | A1–A8 | 8 files |
| B — Agents | B1–B4 | 8 files (4 agents + 4 prompts, paired per step) |
| C — Registry & Activation | C1–C4 | 4 files |
| T — Tests | T1–T2 | unit/ + integration/ |
| **Total** | **18 tasks** | **20 files** |

---

## Data Flow

```
OnboardingSession answers
    │
    ├─ [A6] doc_processor   (Phase 1 — optional)
    └─ [A7] onboarding_agent (Phase 2 — Q&A)
                │
                ▼ submitted → pipeline queued
         [B1] Persona Agent  → PersonaObject  → DB
                │
         [B2] ICP Agent      → IcpDefinition  → DB
                │
         [B3] Signal Agent   → Signal[]        → DB
                │
         [B4 Step 4] Fill rating_template.py
                │
                ▼
         prompt_registry (versioned, is_active = True)
                │
         [C3] persona_cache  ← Postgres NOTIFY on update
                │
         [C4] activation     → tenant.status = active
                              → drain captured lead queue
```

---

## Key Constraints

- **Pipeline 2 is async.** Tenant must not be blocked waiting for it. Stage 4 (connector setup) runs in parallel.
- **Incoming events during Pipeline 2:** Written as `lead` + `event` with `pipeline_stage = captured`. Not scored until `tenant.status = active`.
- **Pipeline failure must surface.** A persistent UI banner must appear on whatever screen the tenant is on: *"Scoring setup failed — your business profile needs review."* Clicking navigates back to Stage 3, pre-filled with prior answers.
- **Pipeline 2 failure is tenant-scoped.** Other tenants are unaffected.
- **`prompt_registry` always has exactly one `is_active = True` record per tenant.** Storing a new version deactivates the previous one atomically.
- **All LLM calls go through `sonnet_client.py`.** No direct Anthropic SDK calls outside that file.
- **`rating_template.py` is the only template file.** It contains the Rating Agent system prompt scaffold. It is not a Python f-string — it is a template with named placeholders filled by `pipeline.py` Step 4 at pipeline runtime.
