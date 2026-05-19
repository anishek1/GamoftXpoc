---
type: analysis
question: "Define the complete security plan for the Lead Intelligence Engine: authentication mechanism, role matrix, API access rules, input sanitization, encryption policy, secrets management, PII masking, prompt logging sanitization, and audit logging requirements."
date: 2026-05-19
tags: [security, auth, rbac, jwt, clerk, pii, encryption, secrets, audit, sanitization]
sources_consulted:
  - "[[analyses/governance-observability-layer]]"
  - "[[analyses/tech-stack-research]]"
  - "[[analyses/context-construction-specification]]"
  - "[[analyses/delivery-integration-layer]]"
  - "[[analyses/channel-integration-layer]]"
  - "[[analyses/enrichment-tools-integration]]"
  - "[[analyses/llm-operational-safeguards]]"
status: COMPLETE
---

# Security Planning — Epic 0.10

**Question:** Full security spec: authentication, RBAC, API access rules, input sanitization, encryption policy, secrets management, PII masking, prompt logging sanitization, and audit logging.
**Date:** 2026-05-19

This document is the authoritative security reference. It consolidates the security decisions scattered across [[analyses/governance-observability-layer]] (Section 7), [[analyses/tech-stack-research]], [[analyses/context-construction-specification]], and [[analyses/delivery-integration-layer]], and fills the gaps.

---

## Architecture Overview

```
Layer 1: Tenant Isolation    → Postgres RLS on every tenant_id table
Layer 2: Authentication      → Clerk (JWT with orgId + orgRole claims)
Layer 3: Access Control      → 4-role RBAC enforced at API endpoint level

Cross-cutting:
  Input Sanitization         → Pydantic v2 at every API boundary
  Encryption (at rest)       → AES-256-GCM on PII fields (application layer)
  Encryption (in transit)    → TLS 1.2+ on all endpoints, no plain HTTP
  Secrets Management         → AWS Secrets Manager, vault path per credential
  PII Masking                → PII stays in user message only; redacted in app logs
  Audit Logging              → access_log append-only; 5-year retention
```

The three layers are multiplicative, not additive. Each assumes the others can fail. A missing WHERE clause is caught by RLS. A spoofed identity is caught by JWT validation. A privilege escalation attempt is caught by RBAC.

---

## Story 1 — Platform Authentication and RBAC

### 1.1 Auth Mechanism — Clerk

**Decision:** Clerk is the authentication provider. (Source: [[analyses/tech-stack-research]])

**Why Clerk over alternatives:**
- Organizations API maps directly to multi-tenancy: each Gamoft tenant is a Clerk Organization. `orgId` = `tenant_id`. No custom multi-tenant logic in application code.
- 4 RBAC roles are first-class in Clerk's Organizations model.
- Free through 10K MAU — zero cost at MVP.
- Auth0 costs $600+/month minimum (rejected). Cognito requires Lambda triggers for multi-tenancy (complexity cost, rejected).

**How it works end-to-end:**

```
User opens app
  → Clerk handles login UI (hosted page or embedded component)
  → Clerk issues short-lived JWT (1 hour) + long-lived refresh token
  → JWT carries: user_id, orgId (tenant_id), orgRole (role), iat, exp
  → Every API request sends JWT in Authorization: Bearer header
  → FastAPI middleware validates JWT signature against Clerk's JWKS endpoint
  → Extracts orgId → sets app.current_tenant_id in Postgres session → RLS activates
  → Extracts orgRole → enforces RBAC at endpoint
  → Request proceeds
```

**JWT claims structure:**

```json
{
  "sub": "user_xxxxxxxx",
  "org_id": "org_gamoft_001",
  "org_role": "team_lead",
  "iat": 1747600000,
  "exp": 1747603600
}
```

| Claim | Maps to | Used for |
|---|---|---|
| `sub` | `user_id` | Audit log actor; salesperson lead assignment |
| `org_id` | `tenant_id` | RLS session variable; credential vault path scoping |
| `org_role` | `role` | RBAC enforcement at endpoint level |
| `exp` | token expiry | 1 hour — enforced by Clerk and by API middleware |

**Token lifecycle:**
- Access token: 1 hour. Validated on every request.
- Refresh token: longer-lived, rotated on use. Client uses Clerk SDK to refresh silently before expiry.
- Token revocation: handled by Clerk (session management). On role change or user suspension, Clerk revokes all active sessions for that user.

**FastAPI middleware:**

```python
from clerk_backend_api import Clerk
from fastapi import Request, HTTPException

clerk = Clerk(secret_key=settings.CLERK_SECRET_KEY)

async def verify_jwt(request: Request) -> dict:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    claims = clerk.verify_token(token)  # validates signature + expiry
    request.state.user_id = claims["sub"]
    request.state.tenant_id = claims["org_id"]
    request.state.role = claims["org_role"]
    return claims
```

**RLS activation per request:**

```python
async def set_rls_context(conn, tenant_id: str):
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, TRUE)",
        [tenant_id]
    )
```

Called immediately after JWT validation, before any query runs.

**Webhook endpoints (unauthenticated paths):**
Meta webhook endpoints (`POST /webhooks/meta/{channel}`) do not carry a JWT — Meta cannot add one. These endpoints are protected by HMAC-SHA256 signature validation instead (see Section 2.3). They bypass Clerk middleware and go through a separate HMAC verification path.

---

### 1.2 Role Matrix

Four roles. Each maps to a distinct permission boundary.

| Role | Scope | Who holds it |
|---|---|---|
| `admin` | Cross-tenant (Gamoft system) | Gamoft team only |
| `team_lead` | Single tenant (scoped by org_id) | One or more per tenant |
| `salesperson` | Single tenant — own assigned leads only | Sales reps at tenant |
| `viewer` | Single tenant — aggregated metrics only | Stakeholders, read-only |

**Full permission matrix:**

| Capability | admin | team_lead | salesperson | viewer |
|---|---|---|---|---|
| View all tenants | ✓ | — | — | — |
| Create tenant | ✓ | — | — | — |
| Manage tenant config | ✓ | Partial (own) | — | — |
| Create/manage users | ✓ | Own tenant users | — | — |
| Change user roles | ✓ | — | — | — |
| Trigger Pipeline 2 re-run | ✓ | ✓ | — | — |
| View all leads (own tenant) | ✓ | ✓ | — | — |
| View assigned leads only | ✓ | ✓ | ✓ | — |
| View lead PII (name/phone/email) | ✓ | ✓ | ✓ | — |
| Assign lead to salesperson | ✓ | ✓ | — | — |
| Submit lead feedback | ✓ | ✓ | ✓ | — |
| Create/activate prompt templates | ✓ | — | — | — |
| View prompt templates | ✓ | — | — | — |
| View quality reports (own tenant) | ✓ | ✓ | — | ✓ (aggregated) |
| View action metrics (own) | ✓ | ✓ | ✓ (own) | — |
| Approve/dismiss enforcement rec. | ✓ | ✓ | — | — |
| Trigger manual Pipeline 1 re-score | ✓ | ✓ | — | — |
| Configure webhooks (outbound) | ✓ | ✓ | — | — |
| View access_log (audit) | ✓ | — | — | — |

**team_lead is always tenant-scoped.** A team_lead at Urvee Organics cannot see Gamoft's data even with a valid token. RLS enforces this automatically via org_id.

**salesperson lead scoping** is enforced in addition to RLS:

```python
if role == "salesperson":
    query = query.where(Lead.assigned_to == user_id)
```

**viewer sees no PII, no individual leads.** All viewer-accessible endpoints return only aggregate metrics (counts, rates, averages). The application layer enforces this — viewer requests never touch the `leads` table directly.

---

### 1.3 API Access Rules — Endpoint-Level Permissions

**Format:** `METHOD /path` → `[roles that can call it]`

**Ingestion:**

| Endpoint | Roles | Notes |
|---|---|---|
| `POST /webhooks/meta/{channel}` | Public (HMAC validated) | No JWT. Validate `X-Hub-Signature-256` before any processing. |
| `POST /leads/ingest` | admin, team_lead | Programmatic lead creation (API clients) |
| `POST /leads/upload-csv` | admin, team_lead | CSV batch ingestion |

**Leads:**

| Endpoint | Roles | Notes |
|---|---|---|
| `GET /leads` | admin, team_lead, salesperson | salesperson: assigned only. viewer: denied. |
| `GET /leads/{id}` | admin, team_lead, salesperson | salesperson: own assigned only. viewer: denied. |
| `PATCH /leads/{id}/assign` | admin, team_lead | Assign to salesperson |
| `POST /leads/{id}/feedback` | admin, team_lead, salesperson | Outcome feedback submission |
| `POST /leads/{id}/rescore` | admin, team_lead | Manual Pipeline 1 trigger |

**Pipeline:**

| Endpoint | Roles | Notes |
|---|---|---|
| `POST /pipeline2/run` | admin, team_lead | Re-run onboarding pipeline |
| `GET /pipeline/status/{lead_id}` | admin, team_lead, salesperson | salesperson: own assigned only |

**Configuration:**

| Endpoint | Roles | Notes |
|---|---|---|
| `GET /tenants` | admin | List all tenants |
| `POST /tenants` | admin | Create tenant |
| `GET /tenants/{id}/config` | admin, team_lead | team_lead: own tenant only |
| `PATCH /tenants/{id}/config` | admin, team_lead | team_lead: limited fields (see §client-config-schema-defaults) |

**Users:**

| Endpoint | Roles | Notes |
|---|---|---|
| `POST /users` | admin | Create user (Clerk invitation) |
| `GET /users` | admin, team_lead | team_lead: own tenant users only |
| `PATCH /users/{id}/role` | admin | Role changes always require admin |

**Prompts:**

| Endpoint | Roles | Notes |
|---|---|---|
| `GET /prompts` | admin | |
| `POST /prompts` | admin | Create prompt version |
| `PATCH /prompts/{id}/activate` | admin | Activating a prompt is an admin-only action |

**Quality / Reporting:**

| Endpoint | Roles | Notes |
|---|---|---|
| `GET /quality/snapshots` | admin, team_lead, viewer | viewer: aggregated totals only, no per-lead data |
| `GET /reports/actions` | admin, team_lead, salesperson | salesperson: own metrics only |

**Webhooks (outbound):**

| Endpoint | Roles | Notes |
|---|---|---|
| `POST /tenants/{id}/webhooks` | admin, team_lead | Configure outbound webhook endpoint |
| `DELETE /tenants/{id}/webhooks/{webhook_id}` | admin, team_lead | |

**Enforcement:** Role check is a FastAPI dependency injected per route. Denied requests return HTTP 403 with no data leak in the response body.

```python
def require_role(*allowed_roles: str):
    async def check(request: Request):
        if request.state.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
    return Depends(check)

@router.get("/leads", dependencies=[Depends(require_role("admin", "team_lead", "salesperson"))])
async def list_leads(...):
    ...
```

---

## Story 2 — Data and API Protection Controls

### 2.1 Input Sanitization Rules

**Principle:** All input is untrusted until validated by a Pydantic model. No raw dict access on request payloads.

**Pydantic v2 as the first line of defense:**

FastAPI + Pydantic v2 validates all request bodies automatically. Unknown fields are rejected. Missing required fields return HTTP 422. Type coercion errors return HTTP 422. This eliminates an entire class of injection vectors where malformed payloads reach application logic.

```python
class LeadIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # reject unknown fields

    name: str = Field(max_length=200)
    phone: str = Field(pattern=r"^\+[1-9]\d{6,14}$")  # E.164 format
    email: EmailStr
    source: Literal["email", "whatsapp", "instagram", "sheets", "api"]
    raw_message: str = Field(max_length=10_000)
```

**String field rules (applied to all string inputs):**

| Rule | What it prevents |
|---|---|
| Max length enforced per field (Pydantic) | Payload inflation / buffer overflows |
| Reject null bytes (`\x00`) | Null byte injection in file paths / logs |
| Strip leading/trailing whitespace | Normalisation; prevents whitespace-padded duplicates |
| No `eval`/`exec` anywhere in application code | Code injection — enforced by code review policy |
| Phone: E.164 format only (`+[country][number]`) | Malformed phone data corrupting enrichment calls |
| Email: RFC 5322 via `EmailStr` (Pydantic) | Malformed email reaching SMTP / enrichment APIs |

**SQL injection:** Not applicable. The application uses SQLAlchemy ORM with parameterized queries. No raw SQL string construction in application code. Queries always use bound parameters:

```python
# Correct — parameterized
await db.execute(select(Lead).where(Lead.tenant_id == tenant_id, Lead.id == lead_id))

# Banned — string interpolation in SQL never appears in codebase
# f"SELECT * FROM leads WHERE tenant_id = '{tenant_id}'"  ← never do this
```

**Webhook payload validation (Meta inbound):**

Two-step process. Step 1 must pass before step 2 runs.

```
Step 1: HMAC validation
  Compute HMAC-SHA256(app_secret, raw_request_body)
  Compare to X-Hub-Signature-256 header value
  If mismatch → HTTP 403, log attempt, stop processing

Step 2: Schema validation
  Parse JSON body through Pydantic WebhookPayload model
  Unknown fields: ignored (Meta adds new fields without notice)
  Missing required fields: discard event, log anomaly
```

The raw request bytes must be read before JSON parsing — HMAC is computed on the raw bytes, not the parsed JSON.

**CSV upload validation:**

```
1. File type check: content-type must be text/csv or application/vnd.ms-excel
2. File size limit: 10 MB max
3. Column mapping: LLM-assisted mapping step (see b2c-data-acquisition) — no raw field names executed as code
4. Row count limit: 50,000 rows per upload
5. Each row validated through LeadRow Pydantic model before insertion
```

---

### 2.2 Encryption Policy

#### At Rest

**What is encrypted:** PII fields only. Scores, buckets, signals, pipeline metadata are not encrypted (not PII; adding encryption overhead to every analytical query is unjustified).

| Field | Table | Encrypted |
|---|---|---|
| `name` | `leads` | ✓ AES-256-GCM |
| `phone` | `leads` | ✓ AES-256-GCM |
| `email` | `leads` | ✓ AES-256-GCM |
| `location` / `address` | `leads` | ✓ AES-256-GCM |
| `raw_message` (original contact message) | `leads` | ✓ AES-256-GCM |
| `score`, `bucket`, `sub_scores` | `lead_scores` | — not PII |
| Signal values, signal names | `signal_evaluations` | — not PII |
| Pipeline stage, timestamps | `pipeline_run`, `task_execution` | — not PII |
| Prompt templates | `prompt_registry` | — not PII |

**How encryption works (application-layer):**

```
Encryption key stored in AWS Secrets Manager at path: global/db/pii_encryption_key
Key type: AES-256
Mode: GCM (authenticated encryption — detects tampering)
Key retrieval: loaded once at service startup into memory; not cached to disk
Rotation: manual (trigger rotation when key is compromised)
```

Encryption happens at the repository layer, before the ORM writes to Postgres. Decryption happens at the repository layer, after the ORM reads from Postgres. No other layer touches PII as plaintext.

**Disk encryption:** AWS RDS encrypts all data at rest by default (AWS-managed key). Application-layer encryption is in addition to disk encryption — two independent layers.

**Nonce:** A fresh random 12-byte nonce is generated per encryption operation. Stored alongside the ciphertext as `{nonce_base64}:{ciphertext_base64}`.

#### In Transit

| Connection | Requirement |
|---|---|
| Client → API | HTTPS/TLS 1.2+ mandatory. No plain HTTP. Load balancer terminates TLS; app container receives plain HTTP internally (private VPC only). |
| API → Postgres (RDS) | SSL connection required. `rds.force_ssl=1` set on parameter group. Connection string includes `sslmode=require`. |
| API → Enrichment APIs | All external APIs (Surepass, Probe42, Tracxn, NewsCatcherAPI, Serper, Anthropic) are HTTPS-only. Requests using `httpx` with `verify=True` (default). |
| API → Meta APIs | HTTPS only (Meta enforces this). |
| Internal service-to-service | Services run in the same private VPC. No public internet between Ingestion, Orchestration, and Reporting services. Inter-service calls over private IP. |
| Outbound webhooks (tenant-configured) | Enforced: HTTPS endpoints only. HTTP webhook URLs are rejected at configuration time. |

---

### 2.3 Secrets Management Plan

**Vault:** AWS Secrets Manager. $0.40/secret/month. IAM-integrated — ECS task roles control which secrets each service can read. (Source: [[analyses/tech-stack-research]])

**Path naming convention:** `{scope}/{category}/{name}`

- `global/` — shared across all tenants (LLM keys, enrichment API keys, app-level secrets)
- `{tenant_id}/` — per-tenant (channel tokens, webhook secrets)

**Full credential inventory:**

| Credential | Vault Path | Per-tenant | Rotation trigger |
|---|---|---|---|
| Anthropic API Key | `global/llm/anthropic/api_key` | No | On compromise |
| Meta App Secret (HMAC validation) | `global/meta/app_secret` | No | On compromise |
| PII encryption key | `global/db/pii_encryption_key` | No | On compromise |
| Postgres connection string | `global/db/{env}/connection_string` | No | On rotation |
| Surepass API Key | `global/enrichment/surepass/api_key` | No | Quarterly or on compromise |
| Probe42 API Key | `global/enrichment/probe42/api_key` | No | Quarterly or on compromise |
| Tracxn Access Token | `global/enrichment/tracxn/access_token` | No | Quarterly or on compromise |
| NewsCatcherAPI Token | `global/enrichment/newscatcher/api_token` | No | Quarterly or on compromise |
| Serper.dev API Key | `global/enrichment/serper/api_key` | No | Quarterly or on compromise |
| Facebook Page Token | `{tenant_id}/facebook/{page_id}/page_token` | Yes | On revocation |
| Instagram Access Token | `{tenant_id}/instagram/{ig_account_id}/access_token` | Yes | Every 60 days (automated job) |
| WhatsApp System User Token | `{tenant_id}/whatsapp/{phone_number_id}/access_token` | Yes | On compromise |
| Outbound webhook secret | `{tenant_id}/webhook/{webhook_id}/secret` | Yes | Per tenant request |
| CRM integration token | `{tenant_id}/crm/{crm_type}/access_token` | Yes | Per provider TTL |

**Rules:**

1. No credential ever appears in application code, environment variables in plain text, Postgres, or logs.
2. The database stores a vault path reference only — never the credential value.
3. Services read credentials from Secrets Manager at startup (global secrets) or at request time (per-tenant, per-credential).
4. Every credential fetch is logged by AWS Secrets Manager: `(secret_arn, principal, timestamp)`.
5. IAM service roles are least-privilege: the Ingestion service can read channel credentials only; the Orchestration service can read enrichment + LLM credentials; neither can read the other's secrets.
6. Credentials are never logged — the application layer must strip credential values before any logging operation.

**Rotation procedure:**
1. Generate new credential with the issuing service.
2. Write new value to Secrets Manager at the same path.
3. Service picks up the new value on next fetch (at-request resolution for per-tenant credentials) or on next deploy (startup-loaded global secrets).
4. Revoke old credential with the issuing service.
5. Log rotation event to `access_log`.

---

## Story 3 — LLM Data Safety Controls

### 3.1 PII Masking Rules

**Rule 1 — PII in LLM context: user message only.**

Lead contact fields (name, phone, email) appear in the `user` message of the LLM input only. They never appear in the `system` message.

The system message is the cached (static) portion of the prompt — it is shared across all leads for a given tenant and prompt version. Putting PII in the system message would corrupt the prefix cache (different PII per lead = different cache key = cache misses on every call) and would cause cross-lead data contamination if the system message is accidentally shared. (Source: [[analyses/context-construction-specification]] §PII rule)

```
SYSTEM MESSAGE (cached, never contains PII):
  - Tenant persona
  - ICP definition
  - Scoring instructions
  - Signal definitions
  - Output format spec

USER MESSAGE (uncached, per-lead):
  - lead.name, lead.phone, lead.email   ← PII lives here only
  - Signal values
  - Lead completeness score
  - Variant-specific context
```

**Rule 2 — No PII in enrichment API requests beyond what the API requires.**

Each enrichment call sends only the minimum identity field needed:

| Enrichment step | Field sent | Fields NOT sent |
|---|---|---|
| Truecaller / phone resolver | Phone number only | Name, email |
| Google Places / location | Location string only | Phone, email, name |
| GSTIN/MCA lookup (Surepass) | Company name or GSTIN only | Personal contact info |
| Probe42 | Company name only | Personal contact info |
| Apollo.io | Email or LinkedIn URL | Phone |
| Tracxn | Company name only | Personal contact info |

**Rule 3 — Viewer role never receives PII.**

All endpoints that a `viewer` can access return aggregated metrics only. The application layer enforces this with a response serializer that strips PII fields if `role == "viewer"`.

---

### 3.2 Prompt Logging Sanitization

**What gets stored in `lineage_record.input_snapshot`:**

`lineage_record.input_snapshot` stores the full LLM input JSON (system + user message). This includes PII in the user message section. This is intentional — `lineage_record` is the audit trail for scoring decisions.

`input_snapshot` is:
- Stored encrypted (PII encryption policy applies — AES-256-GCM at application layer)
- Access controlled by RBAC (accessible to admin only via audit interfaces)
- Never returned in lead detail API responses (lineage is a separate admin-only API)

**What gets written to application logs (stdout/stderr, CloudWatch):**

Application logs must never contain PII. The following substitutions are applied before any log statement that includes lead data:

```python
REDACTED_FIELDS = {"name", "phone", "email", "raw_message", "location"}

def sanitize_for_log(data: dict) -> dict:
    return {
        k: "[REDACTED]" if k in REDACTED_FIELDS else v
        for k, v in data.items()
    }
```

**Specific rules:**

| Log event | What is logged | What is redacted |
|---|---|---|
| LLM call initiated | lead_id, tenant_id, prompt_version, variant | name, phone, email, raw_message |
| LLM call completed | lead_id, token counts, latency, bucket | Full LLM input/output |
| Enrichment call initiated | lead_id, enrichment_source, step_number | phone, email passed to enrichment API |
| Enrichment call completed | lead_id, source, fields_populated | Actual field values if PII |
| Pipeline stage transition | lead_id, from_stage, to_stage, timestamp | name, phone, email |
| Retry triggered | lead_id, attempt_number, error_type | Full LLM I/O |
| Schema validation error | lead_id, field_name, error_type | Field value (may contain PII) |

**LLM provider logging:**

Anthropic logs prompts on their side for safety monitoring. This is Anthropic's standard practice. The PII-in-user-message-only rule limits what PII is exposed via this channel. Anthropic's data processing agreement covers this.

Do not use the `disable_prompt_logging` API parameter unless specifically instructed — it disables Anthropic's safety monitoring. This is a policy decision, not a default setting.

---

### 3.3 Audit Logging Requirements

**Table:** `access_log` (maps to `audit_log` S1 entity — see [[analyses/governance-observability-layer]] §3.2)

**Purpose:** Security-focused audit trail. Records every API action taken by every user. Supports: incident investigation, role change auditing, compliance reporting.

**Schema:**

```sql
CREATE TABLE access_log (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      TEXT        NOT NULL,
  user_id        UUID        NOT NULL,
  role           TEXT        NOT NULL,
  endpoint       TEXT        NOT NULL,      -- e.g. "GET /leads/{id}"
  http_method    TEXT        NOT NULL,
  resource_id    TEXT,                      -- lead_id, tenant_id, user_id, etc.
  action_result  TEXT        NOT NULL CHECK (action_result IN ('success', 'denied', 'error')),
  ip_address     INET        NOT NULL,
  user_agent     TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Append-only.** No UPDATE, no DELETE. Archival after 5 years moves to cold storage.

**What triggers an audit log entry:**

| Event type | Logged | Notes |
|---|---|---|
| Any authenticated API request | ✓ | Every request — success and denial |
| JWT validation failure | ✓ | action_result = 'denied'; user_id = null |
| RBAC denial (403) | ✓ | action_result = 'denied' |
| Lead viewed | ✓ | resource_id = lead_id |
| Lead assigned | ✓ | resource_id = lead_id |
| Feedback submitted | ✓ | resource_id = lead_id |
| Pipeline 2 re-run triggered | ✓ | resource_id = tenant_id |
| Manual Pipeline 1 re-score | ✓ | resource_id = lead_id |
| User role changed | ✓ | resource_id = target user_id |
| User created or suspended | ✓ | resource_id = target user_id |
| Prompt template activated | ✓ | resource_id = prompt_id |
| Tenant config changed | ✓ | resource_id = tenant_id |
| Webhook configured | ✓ | resource_id = webhook_id |
| Credential fetched from vault | ✓ | Logged by AWS Secrets Manager separately |
| Login event | ✓ | Via Clerk webhook → access_log |

**Security-specific events (higher priority for alerting):**

| Event | Alert condition |
|---|---|
| Role change for any user | Always alert to admin |
| 5+ RBAC denials from same user in 5 minutes | Suspicious access pattern — alert to admin |
| JWT validation failures from same IP >10 in 1 minute | Possible credential stuffing — alert |
| Prompt template activated | Always alert to admin (confirms intentional change) |
| Admin account login from new IP | Alert to admin |

**Audit log write failures:**

Following the governance layer rule: audit log write failures must NOT halt the primary operation. If `access_log` insert fails, the request completes normally. The failure is emitted as a high-priority metric (see [[analyses/governance-observability-layer]] §1). A dead letter mechanism retries failed audit log writes.

**Audit log access:**

- `admin` role only — via admin-specific API endpoints not accessible to other roles.
- `viewer`, `salesperson`, `team_lead` have no access to audit log.
- Audit log data is never included in webhook payloads or report exports.

---

## Open Decisions

All 5 previously open decisions are now resolved. See Confirmed Decisions below.

---

## Confirmed Decisions

| Decision | Basis |
|---|---|
| Auth provider: Clerk (Organizations API for multi-tenancy) | [[analyses/tech-stack-research]] |
| Secrets vault: AWS Secrets Manager | [[analyses/tech-stack-research]] |
| 3-layer security: RLS + JWT + RBAC | [[analyses/governance-observability-layer]] §7.1 |
| 4 roles: admin, team_lead, salesperson, viewer | [[analyses/governance-observability-layer]] §7.4 |
| PII fields encrypted at rest (AES-256-GCM, application layer) | [[analyses/governance-observability-layer]] §7.6 |
| PII in LLM context: user message only, never system message | [[analyses/context-construction-specification]] §PII rule |
| Credentials stored in vault — DB stores path reference only | [[analyses/governance-observability-layer]] §7.5 |
| access_log append-only, 5-year retention | [[analyses/governance-observability-layer]] §7.7 |
| Audit log write failures do not halt primary operations | [[analyses/governance-observability-layer]] §1 |
| Outbound webhooks: HTTPS only | [[analyses/delivery-integration-layer]] |
| Inbound webhooks: HMAC-SHA256 validation (Step 1 before any processing) | [[analyses/channel-integration-layer]], [[analyses/meta-integration-implementation]] |
| No PII in application logs — REDACTED substitution | This document 2026-05-19 |
| API access rules (endpoint-level RBAC matrix) | This document 2026-05-19 |
| Input sanitization: Pydantic v2 `extra="forbid"`, E.164 phone, EmailStr | This document 2026-05-19 |
| TLS 1.2+ mandatory; no plain HTTP to any endpoint | This document 2026-05-19 |
| All enrichment API calls send minimum identity field only | This document 2026-05-19 |
| **PII key rotation: manual at MVP** — Automated rotation for a custom AES-256 key requires a rotation Lambda, key versioning in application code, and a re-encryption job (2–3 days of engineering). At MVP with 3 POC tenants, the key rotates only on compromise. Manual rotation via Secrets Manager console + migration script is sufficient. Re-evaluate at 10+ tenants or SOC 2 preparation (earliest: post-Month 3). | This document 2026-05-19 |
| **Alert delivery: email at MVP, Slack webhook post-Month 1** — Security alerts (role changes, suspicious access, prompt activation, new admin IP) go to the admin role via email (AWS SES or Resend, $0.10/1000 emails, zero new infrastructure). The system chat interface (Soketi/FCM) is for salesperson lead notifications only — not admin alerts. Add Slack webhook after Month 1 for real-time patterns (5+ RBAC denials, credential stuffing detection). | This document 2026-05-19 |
| **Data retention: leads/pipeline/feedback 2 years, access_log 5 years, quality_snapshots 1 year** — DPDP Act 2023 (India, primary jurisdiction) requires retention "only as long as reasonably necessary for the stated purpose." 2 years from last update is defensible for sales relationship management. Finalize before onboarding Tenant 1 — must appear in the privacy notice. If Govmen is UK-based, UK GDPR applies; these same values are compliant under "legitimate interests" for B2B sales. | This document 2026-05-19 |
| **lineage_record.input_snapshot access: CLI script at MVP, admin API endpoint in Month 2** — Direct DB query returns ciphertext (PII is application-layer encrypted). Build `python manage.py inspect_lineage --lead-id <uuid>` at the same time as Pipeline 1 — it decrypts and pretty-prints the full LLM input/output for debugging. Promote to `GET /admin/leads/{id}/lineage` in Month 2 when team members need debugging access without server SSH. | This document 2026-05-19 |
| **Clerk session: email+password + Google OAuth enabled simultaneously** — Gamoft team (admin role) uses Google Workspace → Google OAuth. Indian SMB users (Urvee Organics salespeople) may not have Google accounts → email+password. Enable both in the Clerk dashboard (30 min, zero code changes). No magic link at MVP (email reliability in India varies; passwordless flows confuse first-time users). No SAML/enterprise SSO until a tenant with an IdP requests it. | This document 2026-05-19 |
