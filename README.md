# Groww Review Pulse

AI agent that turns **Groww (Stocks, Mutual Funds & Gold)** App Store and Play Store reviews into a weekly one-page pulse, writes it to **Google Docs**, and creates a **Gmail draft** — all Google integrations via **MCP servers**.

## Project structure

```
├── config/                 # MCP server configuration
│   ├── mcp_servers.local.json   # Local mock servers (Phase 0 default)
│   └── mcp_servers.remote.json  # Google Workspace remote MCP
├── data/
│   ├── sample/             # Sample Groww review exports (Phase 0/1 input)
│   └── normalized/         # Normalized review store (Phase 1 output)
├── docs/                   # Architecture, plan, eval, decisions
├── src/groww_pulse/        # Application source
│   ├── mcp/                # MCP client, discovery, mock servers
│   ├── phase0/             # Phase 0 verification
│   └── phase1/             # Phase 1 ingestion & normalization
└── tests/
    └── phase1/             # Phase 1 tests and fixtures
```

## Quick start (Phase 0)

### 1. Install

```powershell
cd "c:\AI Agent & MCP"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Configure environment

```powershell
copy .env.example .env
```

By default `MCP_PROFILE=local` uses bundled mock Google Docs and Gmail MCP servers (stdio) so you can verify connectivity without OAuth.

### 3. Run Phase 0 verification

```powershell
groww-pulse-phase0
```

Or:

```powershell
python -m groww_pulse.phase0.verify
```

This checks:

- Project runs cleanly
- Google Docs MCP server connects and lists tools
- Gmail MCP server connects and lists tools
- Required tools exist (`docs_create`, `docs_append`, `gmail_draft_create`)
- Sample Groww review exports load from `data/sample/`

## MCP profiles

| Profile | Config file | Use case |
|---------|-------------|----------|
| `local` | `config/mcp_servers.local.json` | Development; bundled mock MCP servers |
| `remote` | `config/mcp_servers.remote.json` | Production; Google Workspace remote MCP |

Switch profile:

```powershell
$env:MCP_PROFILE = "remote"
```

### Remote Google Workspace MCP (production)

Google provides separate remote MCP servers per product:

- **Gmail:** `https://gmailmcp.googleapis.com/mcp/v1` — tool `create_draft`
- **Google Docs (via Drive):** `https://drivemcp.googleapis.com/mcp/v1` — tools `create_file`, `read_file_content`

Setup requires a Google Cloud project, enabled APIs, OAuth consent screen, and client credentials. See [Configure Google Workspace MCP servers](https://developers.google.com/workspace/guides/configure-mcp-servers).

> HTTP transport for remote MCP is configured in `mcp_servers.remote.json`. Phase 0 verification currently uses stdio (local profile). Remote HTTP client support will be added when OAuth is configured.

## Sample data

Representative public-style Groww review exports (synthetic, no PII):

- `data/sample/groww_app_store_reviews.csv`
- `data/sample/groww_play_store_reviews.csv`

Required columns: `rating`, `title`, `text`, `date`.

## Documentation

- [Problem statement](Problemstatment.md)
- [Architecture](docs/architecture.md)
- [Implementation plan](docs/implementationplan.md)
- [Evaluation criteria](docs/eval.md)
- [Decision log](docs/decision.md)

## Phase 1 — Ingestion & Normalization

Import and normalize Groww review exports into a unified schema:

```powershell
# Fetch real public reviews, then ingest (recommended)
groww-pulse-phase1-run

# Ingest only (uses files already in data/sample/)
groww-pulse-phase1
```

**Fetch sources (no login):**
- **App Store** — Apple public Customer Reviews RSS (up to ~500 recent reviews)
- **Play Store** — public Google Play listing via `google-play-scraper`

Output is written to `data/normalized/groww_reviews.json`.

Configurable via `.env`:
- `SAMPLE_DATA_DIR` — input directory (default: `data/sample`)
- `RECENCY_WEEKS` — rolling window, clamped to 8–12 (default: 10)

## Phase 2 — PII Scrubbing

Scrub emails, phone numbers, usernames, and IDs from normalized reviews (mandatory gate before LLM):

```powershell
groww-pulse-phase2
```

Requires Phase 1 output at `data/normalized/groww_reviews.json`.

**Outputs:**
- `data/scrubbed/groww_reviews.json` — PII-safe reviews
- `data/scrubbed/pii_scrub_report.json` — verification log (categories removed)

## Development status

| Phase | Status |
|-------|--------|
| 0 — Foundations & Environment | Implemented |
| 1 — Ingestion & Normalization | Implemented |
| 2 — PII Scrubbing | Implemented |
| 3 — Theme Analysis (Groq) | Implemented |
| 4 — Insight Selection (Groq) | Implemented |
| 5 — Weekly Note Generation | Implemented |
| 6 — Google Docs Delivery (MCP) | Implemented |
| 7 — Gmail Draft Delivery (MCP) | Implemented |
| 8 — Orchestration & End-to-End | Implemented |
| 9 — Backend API (Render) | Implemented |
| 10 — Insights Dashboard (Vercel) | Planned |

## Phase 8 — Orchestration & End-to-End

Run the full weekly pipeline with one command: **fetch → ingest → scrub → Groq analysis → Google Doc → Gmail draft**.

```powershell
# Full live run (fetch + Groq + MCP delivery)
groww-pulse

# Same as above (explicit phase entry point)
groww-pulse-phase8
```

**Flags:**

| Flag | Effect |
|------|--------|
| `--no-fetch` | Skip live App Store / Play Store fetch; use existing `data/sample/` files |
| `--no-groq` | Deterministic fallbacks instead of Groq (dev only) |
| `--no-deliver` | Skip Google Doc and Gmail draft steps |
| `--force-delivery` | Deliver even if this week already succeeded (default skips duplicate Doc/draft) |

**Example — local dry run without delivery:**

```powershell
groww-pulse-phase8 --no-fetch --no-deliver
```

**Required `.env` for live runs:**

```env
GROQ_API_KEY=...
MCP_PROFILE=remote
GOOGLE_DOC_ID=...
GMAIL_RECIPIENT=...
```

**Outputs:**

| File | Description |
|------|-------------|
| `data/analysis/weekly_run.json` | Latest run log (phases, timings, artifacts) |
| `data/analysis/run_history.json` | Historical runs (idempotency / audit) |
| `data/analysis/themes.json` | Theme analysis |
| `data/analysis/insights.json` | Top 3 themes, quotes, actions |
| `data/analysis/weekly_note.md` | ≤250-word weekly pulse |
| `data/analysis/doc_delivery.json` | Google Doc link |
| `data/analysis/draft_delivery.json` | Gmail draft metadata |

**GitHub Actions scheduler**

Workflow: `.github/workflows/weekly-pulse.yml`

- **Schedule:** every Monday **9:00 AM IST** (`cron: 30 3 * * 1` UTC)
- **Manual run:** Actions tab → *Weekly Groww Pulse* → *Run workflow*
- **Secrets:** `GROQ_API_KEY`, `GOOGLE_DOC_ID`, `GMAIL_RECIPIENT`
- **Artifacts:** uploaded for 90 days after each run

**Re-run a failed job:** open the failed workflow run → *Re-run all jobs*, or trigger `workflow_dispatch` manually after fixing secrets/config.

**Inspect logs:** GitHub Actions run log for CI; locally check `data/analysis/weekly_run.json` for per-phase status and errors.

## Phase 9 — Backend API (Render)

Read-only FastAPI service exposing PII-safe weekly insights for the Vercel dashboard.

```powershell
pip install -e ".[api]"
groww-pulse-phase9
groww-pulse-api
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (Render) |
| GET | `/api/v1/pulse/latest` | Latest weekly pulse |
| GET | `/api/v1/pulse/weeks` | Week index |
| GET | `/api/v1/pulse/weeks/{week_range}` | Pulse for a week |
| GET | `/api/v1/runs` | Run history summaries |
| GET | `/api/v1/runs/{run_id}` | Single run metadata |
| POST | `/api/v1/admin/sync` | Upload artifacts (`X-API-Key`) |

**Deploy on Render:** use `render.yaml` (Web Service + 1GB disk at `/var/data/analysis`).

**Sync artifacts after pipeline:**

```powershell
groww-pulse-phase9-sync
groww-pulse-phase9-sync --remote-url https://groww-pulse-api.onrender.com
```

**Environment:** `API_DATA_DIR`, `CORS_ORIGINS`, `API_KEY` (see `.env.example`).
