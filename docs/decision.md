# Decision Log — Review Pulse AI Agent (MCP)

A running log of important **technical** and **business** decisions. Each entry captures the context, the decision, alternatives considered, and the rationale. Add new decisions at the top.

> Format: ADR-style (Architecture Decision Record). Status: Proposed | Accepted | Superseded.

---

## ADR-001 — Use MCP servers for Google Docs & Gmail (not raw Google APIs)
- **Status:** Accepted
- **Type:** Technical / Business
- **Context:** The agent must create a Google Doc and a Gmail draft. Options were direct Google REST APIs/SDKs vs. MCP servers.
- **Decision:** All Google Docs and Gmail interactions go through **MCP servers**.
- **Alternatives considered:** Direct Google REST APIs; client SDKs.
- **Rationale:** Tool-driven and portable; consistent with the milestone's MCP architecture; keeps integration decoupled from provider-specific API code; easier for the agent to discover and call tools.
- **Consequences:** Requires running/configuring Docs and Gmail MCP servers; capabilities are bounded by the tools those servers expose.

---

## ADR-002 — Public review exports only (no scraping)
- **Status:** Accepted
- **Type:** Business / Compliance
- **Context:** Reviews can be obtained via public exports or by scraping.
- **Decision:** Use **public review exports only**; no scraping behind logins.
- **Rationale:** Compliance and ToS safety; reproducible inputs.
- **Consequences:** Data freshness depends on available exports.

---

## ADR-003 — Mandatory PII scrubbing before LLM/artifacts
- **Status:** Accepted
- **Type:** Technical / Compliance
- **Context:** Reviews may contain usernames, emails, phone numbers, IDs.
- **Decision:** Scrub PII **before** any LLM call or artifact generation; enforce a final no-PII check on outputs.
- **Rationale:** Privacy requirement ("No PII in any artifacts").
- **Consequences:** Adds a processing step; needs verification/logging.

---

## ADR-004 — Cap themes at 5, surface top 3
- **Status:** Accepted
- **Type:** Product
- **Context:** The note must be scannable and ≤250 words.
- **Decision:** Group into **max 5 themes**; present **top 3** in the note.
- **Rationale:** Keeps output focused and within word limits.
- **Consequences:** Lower-priority themes may be omitted from the note.

---

## ADR-005 — Gmail output is a draft (not auto-send)
- **Status:** Accepted
- **Type:** Product / Safety
- **Context:** The deliverable is an email to self/alias.
- **Decision:** Create a **draft** only; do not auto-send.
- **Rationale:** Human review before any send; avoids accidental delivery.
- **Consequences:** A manual send step remains (by design).

---

## ADR-006 — Python runtime with MCP Python SDK
- **Status:** Accepted
- **Type:** Technical
- **Context:** Phase 0 requires an MCP client, tool discovery, and a runnable project skeleton. Runtime choice was open (Python vs. Node/TypeScript).
- **Decision:** Use **Python 3.11+** with the official **`mcp` Python SDK** and `pydantic-settings` for configuration.
- **Alternatives considered:** Node/TypeScript with `@modelcontextprotocol/sdk`.
- **Rationale:** Strong MCP client/server support in Python; async stdio transport is well documented; aligns with common FastMCP server ecosystem for Google Workspace.
- **Consequences:** Project uses `pyproject.toml`, `src/groww_pulse/` layout, and asyncio for MCP connectivity.

---

## ADR-007 — MCP server strategy (local mock + Google remote)
- **Status:** Accepted
- **Type:** Technical
- **Context:** Google Docs and Gmail must be accessed via MCP. Google offers remote Workspace MCP servers; local development needs connectivity without full OAuth setup.
- **Decision:**
  - **Local profile (`MCP_PROFILE=local`):** Two stdio MCP servers — mock Google Docs (`docs_create`, `docs_append`) and mock Gmail (`gmail_draft_create`) bundled in `src/groww_pulse/mcp/servers/`.
  - **Remote profile (`MCP_PROFILE=remote`):** Google Workspace remote MCP — Gmail (`create_draft`) and Drive/Docs (`create_file`, `read_file_content`) per [Google's MCP configuration guide](https://developers.google.com/workspace/guides/configure-mcp-servers).
- **Alternatives considered:** Single combined workspace MCP server only; direct Google APIs.
- **Rationale:** Local mocks unblock Phase 0 tool discovery and CI; remote config matches production architecture with separate logical servers for Docs and Gmail.
- **Consequences:** `config/mcp_servers.local.json` and `config/mcp_servers.remote.json`; tool aliases map mock names to official Google tool names.

---

## ADR-008 — Groq LLM for theme analysis and note generation
- **Status:** Accepted
- **Type:** Technical
- **Context:** Phases 3–5 require an LLM for theming, insight selection, and note drafting.
- **Decision:** Use **Groq** with **`llama-3.3-70b-versatile`**. Optional **`llama-3.1-8b-instant`** for faster note drafts.
- **Alternatives considered:** OpenAI GPT-4o-mini; Anthropic Claude; local models.
- **Rationale:** Fast inference for weekly batch runs; OpenAI-compatible API; sufficient quality on pre-aggregated review packets.
- **Consequences:** Requires `GROQ_API_KEY`; hybrid pipeline (deterministic pre-aggregation + 3 Groq calls); structured JSON outputs.

---

## ADR-009 — JSON file store for normalized reviews
- **Status:** Accepted
- **Type:** Technical
- **Context:** Phase 1 must persist normalized reviews for re-runs without re-importing. Storage format was open.
- **Decision:** Use a **JSON file** at `data/normalized/groww_reviews.json` with a lightweight `ReviewStore` wrapper.
- **Alternatives considered:** SQLite; in-memory only.
- **Rationale:** Simple, human-readable, sufficient for weekly batch volume; easy to inspect during development.
- **Consequences:** Phase 1 writes/reads JSON; may revisit SQLite if volume or query needs grow.

---

## ADR-010 — Regex-based PII scrubbing with mandatory verification gate
- **Status:** Accepted
- **Type:** Technical / Compliance
- **Context:** Phase 2 must remove emails, phones, usernames, and IDs before any LLM call; outputs must be provably PII-free.
- **Decision:** Use **deterministic regex scrubbing** with redaction tokens (`[REDACTED_EMAIL]`, etc.), then run a **post-scrub verifier**. Pipeline fails if any PII remains (mandatory gate).
- **Alternatives considered:** NER-based PII detection; manual review only.
- **Rationale:** Predictable, auditable, no extra ML dependency; verification log satisfies compliance proof.
- **Consequences:** Phase 2 reads `data/normalized/`, writes `data/scrubbed/` + `pii_scrub_report.json`; downstream stages must consume scrubbed store only.

---

## ADR-011 — Hybrid pre-LLM aggregation before Groq calls
- **Status:** Accepted
- **Type:** Technical / Product
- **Context:** Scrubbed dataset has ~1,156 reviews (~39k tokens). Sending all reviews to Groq is costly and noisy; ~37% don't match simple keyword buckets.
- **Decision:** Deterministic pre-pass (stats + seed buckets + 10–15 samples per theme) → compact theme packets to Groq. Severity ranking (volume × low-star %) for top 3.
- **Alternatives considered:** Full corpus to Groq; BERTopic-only clustering; pure keywords without Groq refinement.
- **Rationale:** Small Groq context (~75–90 samples); seed buckets match Groww product areas; Groq refines labels and handles general/unassigned reviews.
- **Consequences:** Phase 3 implements pre-aggregation before Groq; three Groq calls (themes → insights → note).

---

## Open Decisions (To Be Decided)
- **Scheduling mechanism** for the weekly run (manual vs. cron/scheduler) — decide in Phase 8.

> Update each open item to a numbered ADR once decided.
