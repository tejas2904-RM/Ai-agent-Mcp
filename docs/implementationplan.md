# Phase-wise Implementation Plan — Groww Review Pulse AI Agent (MCP)

This plan breaks delivery into incremental phases. Each phase explains **what we are doing and why** (not how to code it). Every phase has a goal, the work involved, what it produces, what it depends on, and the main risks to watch. Testing and exit criteria for every phase live in `eval.md`.

The product under analysis throughout is **Groww — Stocks, Mutual Funds & Gold**.

---

## Phase 0 — Foundations & Environment
**Goal:** Stand up the project skeleton and prove we can talk to both MCP servers before any real logic is built.

**What we are doing**
- Agree on the overall project structure and where data, docs, and working files live.
- Decide and record the runtime, the LLM, and the specific MCP servers for Google Docs and Gmail (these are tracked as open items in `decision.md`).
- Establish connectivity to the **Google Docs MCP server** and the **Gmail MCP server**, including whatever auth/setup each requires.
- Perform **tool discovery** — list the tools each MCP server exposes and confirm the ones we need exist (create a document, write content, create a draft).
- Place one representative **public Groww review export** in the project so later phases have realistic data to work against.

**Why it matters:** MCP connectivity and tool availability are the biggest external unknowns. Proving them first de-risks everything downstream.

**Produces:** a runnable skeleton, confirmed MCP connectivity, and sample data.

**Depends on:** nothing (entry point).

**Risks / watch-outs:** MCP auth/setup friction; tool names/capabilities differing from expectations.

---

## Phase 1 — Review Ingestion & Normalization
**Goal:** Turn raw, public Groww review exports from both stores into one clean, consistent dataset.

**What we are doing**
- Take **public review exports only** (CSV/JSON) for Groww from the App Store and Play Store — explicitly no scraping behind logins.
- Read each export and pull out the fields we care about: **rating, title, text, date**, and tag the **source** (app_store / play_store).
- Reconcile the two stores' different formats/column names into a **single unified schema** so the rest of the pipeline doesn't care where a review came from.
- Apply the **8–12 week recency window** so we only analyze recent sentiment.
- Handle messy data gracefully: skip and log malformed/incomplete rows, remove obvious duplicates, and standardize dates and ratings.
- Save the cleaned dataset to the local store so analysis can run (and re-run) without re-importing.

**Why it matters:** Consistent, trustworthy input is the foundation for good themes and quotes. Garbage in would undermine every later phase.

**Produces:** a normalized, store-agnostic Groww review dataset for the chosen window.

**Depends on:** Phase 0.

**Risks / watch-outs:** inconsistent export formats; timezone/date parsing; accidentally dropping valid reviews during filtering.

---

## Phase 2 — PII Scrubbing
**Goal:** Guarantee that no personally identifiable information flows past this point — into the LLM or any artifact.

**What we are doing**
- Scan every review's title and text for **usernames, emails, phone numbers, and IDs**.
- Remove or mask anything identifying, while preserving the meaning of the review so themes/quotes remain useful.
- Treat scrubbing as a **mandatory gate**: nothing continues unless the dataset has been scrubbed.
- Keep a verification record (what categories were found/removed) so we can prove compliance.

**Why it matters:** The brief forbids PII in any artifact. Doing this before the LLM stage means no later step can leak personal data, even accidentally.

**Produces:** a PII-safe version of the review dataset.

**Depends on:** Phase 1.

**Risks / watch-outs:** missing less-obvious PII (e.g., names inside free text); over-scrubbing that strips meaning from quotes.

---

## Phase 3 — Theme Analysis (Groq LLM Agent)
**Goal:** Understand what Groww users are actually talking about and organize it — using **Groq** on a **600-review cap** and **rate-limit-safe** pre-aggregated packets.

### Groq model limits (`llama-3.3-70b-versatile`)
| Limit | Quota | Weekly run budget | Guardrail |
|-------|-------|-------------------|-----------|
| RPM | 30 | 3 calls (+ optional 1 retry) | Sequential only; never parallel |
| RPD | 1,000 | 3–4 calls max | Log every call in `groq_usage.json` |
| TPM | 12,000 | ≤6,000 per call (in+out) | **3s pause** between calls |
| TPD | 100,000 | ≤8,000 total (~8%) | Pre-aggregate; never send raw corpus |

**What we are doing**

**Step A — Pre-LLM (deterministic, no API call)**
- Load `data/scrubbed/groww_reviews.json` (currently 1,156 reviews).
- **Cap to 600 reviews:** sort by `date` descending, keep most recent 600; log 556 dropped in `run_metadata.json`.
- Compute stats on the 600 subset: rating mix, source split, date range.
- Seed **5 Groww buckets** via keyword signals + **General experience** pool for unassigned (~37%).
- Per bucket: `review_count`, `avg_rating`, `low_star_pct`, `source_split`.
- Select **up to 8 representative samples per bucket** (≤48 reviews total sent to Groq).
- Build **6 theme packets** (stats + samples) — never the full 600 reviews.
- **Pre-call token estimate:** if Call #1 input would exceed 3,500 tokens, drop samples (8→6 per bucket) before any API call.

**Step B — Groq call #1 (theme analysis)**
- **Model:** `llama-3.3-70b-versatile`.
- **Input budget:** ~3,000–3,500 tokens (6 packets + system prompt).
- **Output cap:** `max_tokens=800` (structured JSON, ≤5 themes).
- **Validate** estimated in+out ≤6,000 before sending.
- **Wait 3s** before Phase 4 call (TPM rolling-window safety).

**Data insight (600-review subset, proportional to current corpus):**
| Seed theme | ~Volume | Avg rating | Low-star % | Priority signal |
|------------|---------|------------|------------|-----------------|
| Trading & orders | 27% | 3.07 | 44% | Highest volume |
| App UX & support | 15% | 3.32 | 37% | Steady complaints |
| Payments & withdrawals | 10% | **2.42** | **62%** | **Most severe** |
| Mutual funds & SIP | 8% | 3.72 | 28% | Mostly positive |
| Onboarding & KYC | 3% | 2.45 | 58% | Small but painful |
| General / unassigned | 37% | — | — | Generic praise/complaints |

**Why it matters:** 600 raw reviews ≈ 20k tokens — one call would burn **~20% of daily TPD** and risk TPM. Pre-aggregation + 8 samples/bucket keeps Call #1 at ~3.5k tokens (~30% of the 12K TPM ceiling per call).

**Produces:** `data/analysis/themes.json`, `data/analysis/groq_usage.json` (per-call token log), `data/analysis/run_metadata.json` (cap + drop counts).

**Depends on:** Phase 2.

**Risks / watch-outs:** 37% unassigned reviews; Groq 429 rate errors — exponential backoff (30s, 60s), max 2 retries per call; JSON parse failures — regenerate once; TPM breach — enforce 3s inter-call delay and pre-call token validation.

---

## Phase 4 — Insight Selection (Groq LLM)
**Goal:** Distill theme analysis into exactly the highlights the weekly note needs.

**What we are doing**
- **Rank themes** locally using severity score (volume × low-star % × rating penalty).
  - Expected top 3: **Payments & withdrawals**, **Trading & orders**, **App UX & support**.
- **Groq call #2 — insight selection:**
  - **Model:** `llama-3.3-70b-versatile`.
  - **Input budget:** ~1,000–1,200 tokens (top 3 summaries + 8 samples each = 24 reviews max).
  - **Output cap:** `max_tokens=600` (JSON: top 3 themes, 3 verbatim quotes, 3 action ideas).
  - **Validate** estimated in+out ≤1,800 before sending.
  - **Wait 3s** before Phase 5 call.
- Deterministic post-check: quotes must exist verbatim in Phase 3 sample set.

**Why it matters:** Call #2 is ~1.8k tokens total (in+out) — well under 12K TPM; full 3-call run uses ~6–8k TPD (~8% of quota), leaving room for dev re-runs and one note retry.

**Produces:** `data/analysis/insights.json` (+ append to `groq_usage.json`).

**Depends on:** Phase 3.

**Risks / watch-outs:** hallucinated quotes; vague action ideas; PII re-scan on quote text; 429 errors — same backoff as Phase 3.

---

## Phase 5 — Weekly Note Generation (Groq LLM)
**Goal:** Produce the one-page Groww weekly pulse (≤250 words).

**What we are doing**
- **Groq call #3 — note generation:**
  - **Model:** `llama-3.3-70b-versatile`.
  - **Input budget:** ~500–700 tokens (structured insights JSON only — no raw reviews).
  - **Output cap:** `max_tokens=400`.
  - **Validate** estimated in+out ≤1,100 before sending.
- Deterministic validation: word count ≤250, 3 sections present, PII re-scan.
- **Optional Groq call #4:** regenerate note if validation fails (~700 in / 400 out, validate ≤1,100).

**Weekly Groq budget summary:**
| Call | Phase | Input (est.) | Output cap | In+out (est.) |
|------|-------|--------------|------------|---------------|
| #1 | 3 | ~3,500 | 800 | ~4,300 |
| #2 | 4 | ~1,200 | 600 | ~1,800 |
| #3 | 5 | ~600 | 400 | ~1,000 |
| #4 (optional) | 5 retry | ~700 | 400 | ~1,100 |
| **Total** | | **~6,000** | **~1,800** | **~6–8k / 100k TPD** |

**Limit compliance checklist (every weekly run):**
- [ ] Exactly 3 Groq calls (4 only on note-validation retry)
- [ ] No call exceeds 6,000 tokens in+out
- [ ] 3s pause between calls #1 → #2 → #3
- [ ] Total TPD logged in `groq_usage.json` stays under 8,000
- [ ] Zero raw-review payloads sent to Groq (packets only)

**Why it matters:** Fixed 3-call pipeline with hard token caps and inter-call delays stays within all four Groq limits (30 RPM / 1K RPD / 12K TPM / 100K TPD) with room for one retry and multiple dev re-runs per day.

**Produces:** `data/analysis/weekly_note.md` (+ final `groq_usage.json` totals).

**Depends on:** Phase 4.

**Risks / watch-outs:** note exceeds 250 words — trim locally or use call #4 retry.

---

## Phase 6 — Google Docs Delivery (via MCP)
**Goal:** Publish the weekly note as a Google Doc using the **Google Docs MCP server**.

**What we are doing**
- Use the Docs MCP tool to **create a new document** for the week and **write the formatted note** into it.
- Give the document a clear, consistent title (product + week range) so weekly docs are easy to find.
- Capture the resulting **document link** for use in the email and the run log.
- Keep this strictly MCP-based — no direct Google Docs API calls.

**Why it matters:** A Google Doc is a shareable, durable home for the weekly pulse that stakeholders can read and comment on.

**Produces:** a Google Doc containing the weekly pulse, plus its link.

**Depends on:** Phase 5 and Phase 0 (MCP connectivity).

**Risks / watch-outs:** formatting fidelity through the MCP tool; auth/permissions on document creation.

---

## Phase 7 — Gmail Draft Delivery (via MCP)
**Goal:** Put the weekly note in the inbox as a **draft** using the **Gmail MCP server**.

**What we are doing**
- Use the Gmail MCP tool to **create a draft** addressed to yourself/an alias.
- Include the weekly note in the body and/or a link to the Google Doc from Phase 6.
- Give it a clear, consistent subject (e.g., "Groww Weekly Review Pulse — <week range>").
- **Never auto-send** — the deliverable is explicitly a draft for human review.
- Keep this strictly MCP-based — no direct Gmail API calls.

**Why it matters:** Delivering to the inbox closes the loop ("send yourself a draft"), while keeping a human in control before anything is actually sent.

**Produces:** a Gmail draft containing the note (and/or Doc link).

**Depends on:** Phase 5/6 and Phase 0 (MCP connectivity).

**Risks / watch-outs:** accidental send instead of draft; correct recipient (self/alias); body rendering of the note/link.

---

## Phase 8 — Orchestration & End-to-End
**Goal:** Make the whole thing run reliably as one repeatable weekly workflow.

**What we are doing**
- Connect every stage through the MCP client/orchestrator so a single trigger runs **fresh ingestion → scrub → analysis → note → Doc → Gmail draft**.
- **Fetch latest review data on every run** — Phase 1 ingestion runs at the start of each workflow so the pulse always reflects the most recent public exports (8–12 week window), not stale files from a prior week.
- Add sensible **error handling and retries** so transient issues (e.g., a flaky MCP call) don't abort the whole run.
- Maintain a **run log** capturing key counts, the chosen themes, and the produced artifacts (Doc link, draft).
- Make runs **idempotent** for a given week so re-running doesn't create confusing duplicates.
- **Schedule the weekly run with GitHub Actions** — workflow triggers every **Monday at 9:00 AM IST** (`03:30 UTC`, cron `30 3 * * 1`). Secrets (`GROQ_API_KEY`, `GOOGLE_DOC_ID`, `GMAIL_RECIPIENT`, `MCP_PROFILE=remote`, etc.) live in the repo's GitHub Actions secrets; the workflow invokes the single orchestrator entry point.
- Document manual run (`groww-pulse` or equivalent), how to re-run a failed job, and how to inspect run logs/artifacts.

**Why it matters:** The value is in a dependable weekly cadence, not a one-off. Orchestration turns the pieces into a product; GitHub Actions provides a zero-ops scheduler that always pulls fresh data before analysis.

**Produces:** a single-command/scheduled, repeatable Groww weekly pulse workflow; `.github/workflows/weekly-pulse.yml` (or equivalent) for the Monday 9:00 AM IST run.

**Depends on:** Phases 1–7.

**Risks / watch-outs:** partial failures mid-pipeline; duplicate artifacts on re-run; unclear operating instructions; GitHub Actions secret rotation; cold-start latency on the remote MCP server (Render); ingestion source availability on Monday mornings.

---

## Phase 9 — Backend API Deployment (Render)
**Goal:** Expose PII-safe weekly insights and run metadata through a production **REST API** hosted on **[Render](https://render.com)** so the dashboard (and other clients) can read the latest pulse without touching pipeline internals.

**What we are doing**
- Build a thin **read-only API layer** (e.g. FastAPI) that serves artifacts produced by Phases 3–8: themes, insights, weekly note summary, run log, Doc/draft links.
- Deploy the backend as a **Render Web Service** with health checks (`/health`), versioned routes (e.g. `/api/v1/latest`, `/api/v1/runs`, `/api/v1/weeks/{week_range}`).
- **Never expose raw reviews or PII** — only scrubbed, aggregated outputs already validated by the pipeline.
- Wire **environment variables** on Render (`GROQ_API_KEY` only if on-demand re-runs are supported later; primarily paths/DB connection strings, `CORS_ORIGINS` for Vercel, optional object-store keys if artifacts are synced from GitHub Actions).
- Configure **CORS** to allow the Vercel dashboard origin; use API key or similar lightweight auth for non-public endpoints if needed.
- Optionally persist/sync analysis JSON from GitHub Actions artifacts into **Render disk or attached storage** so the API survives ephemeral CI runners.
- Document deploy steps: `render.yaml` or Render dashboard, build/start commands, secret rotation, and rollback.

**Why it matters:** The weekly pipeline runs on a schedule; stakeholders need a stable HTTPS endpoint to fetch the latest insights without cloning the repo or reading local `data/` files.

**Produces:** a live Render backend URL (e.g. `https://groww-pulse-api-uss6.onrender.com`) serving PII-safe insight payloads.

**Depends on:** Phases 3–8 (analysis artifacts and run log schema).

**Risks / watch-outs:** serving stale data if CI artifacts are not synced; cold starts on Render free tier; accidental exposure of non-public fields; CORS misconfiguration; coupling API schema too tightly to internal JSON filenames.

---

## Phase 10 — Insights Dashboard (Next.js on Vercel)
**Goal:** Ship a **Next.js** insights dashboard on **[Vercel](https://vercel.com)** that visualizes the weekly Groww Review Pulse — themes, quotes, action ideas, note preview, and links to the Google Doc / run history.

**Frontend principle:** **Next.js** (App Router) is the **mandated** frontend stack for this project — not a generic React SPA. Vercel is the deployment target; Next.js is the framework.

**Approved UI reference (Google Stitch):** The visual design is **locked** to two Stitch screens in project `6374599666648079093`. Implementation must match these mocks and the colour scheme below — do not invent a new palette or layout.

| Screen | Stitch path | Next.js route | Purpose |
|--------|-------------|---------------|---------|
| Main dashboard | `screens/490cfa088c134c2abffc140c5a3f829a` | `app/page.tsx` | Latest weekly pulse |
| Run history | `screens/08cd0bc5260a44d0879ea6c766c2fd1d` | `app/runs/page.tsx` | Pipeline run timeline |

Stitch project: `web application/stitch/projects/6374599666648079093` · Prompt source: `docs/google-stitch-frontend-prompts.md`

**Approved colour scheme & design tokens**

| Token | Hex | Usage |
|-------|-----|--------|
| Background | `#F8FAFC` | Page canvas (off-white) |
| Surface / card | `#FFFFFF` | Theme cards, quote blocks, note preview |
| Border | `#E2E8F0` | Card borders, dividers |
| Primary accent | `#00B386` | CTAs, active nav, success status, primary buttons |
| Heading / nav | `#0F172A` | Titles, wordmark, primary text |
| Text secondary | `#64748B` | Labels, metadata, captions |
| Text muted | `#94A3B8` | Timestamps, helper text |
| Negative sentiment | `#EF4444` | Low-star %, severity bars, failed runs |
| Mixed sentiment | `#F59E0B` | Mixed-sentiment badges |
| Positive sentiment | `#10B981` | Success badges, positive signals |

- **Typography:** Inter (or equivalent geometric sans) — 32px bold hero, 20px semibold section titles, 14px body, 12px captions.
- **Cards:** 12px radius, 1px `#E2E8F0` border, shadow `0 1px 3px rgba(15,23,42,0.08)`.
- **Buttons:** 8px radius; primary filled `#00B386`; secondary outline slate.
- **Badges:** Pill shape — volume `HIGH` / `MEDIUM` / `LOW`; sentiment `NEGATIVE` / `MIXED` / `POSITIVE`.

**What we are doing**
- Scaffold a **Next.js** app (App Router, TypeScript) under `dashboard/` that **pixel-matches the approved Stitch screens** and consumes the Phase 9 Render API.
- **Main dashboard screen** (`490cfa08…`): top nav (logo + week selector + Doc/Gmail links + success pill), hero with review metadata, **bento grid of 3 theme cards** (rank, volume/sentiment badges, stats), two-column **User Quotes** + **Action Ideas**, collapsible **weekly note preview** (≤250 words).
- **Run history screen** (`08cd0bc5…`): breadcrumb, filter chips (All / Success / Failed / Skipped delivery), vertical **timeline cards** per run (run ID, week range, status badge, timestamps, delivery links, mini stats).
- Use **Server Components** for initial data fetch; **Client Components** for week selector, filters, and loading states.
- Add **loading / error / empty** states consistent with the same Stitch palette (see `google-stitch-frontend-prompts.md` Prompt 4).
- Configure **Vercel environment variables** (`NEXT_PUBLIC_API_URL` → Render backend, optional auth token).
- Enable **preview deployments** per PR and **production** on merge to main.
- Keep the dashboard **read-only** — no pipeline triggers from the UI in v1.

**Why it matters:** Docs and Gmail drafts reach operators in their tools; the Stitch-approved Next.js dashboard gives product and leadership a scannable, on-brand weekly pulse in the browser.

**Produces:** a live Vercel URL (e.g. `https://groww-pulse.vercel.app`) — Next.js app matching Stitch mocks, connected to the Render API.

**Depends on:** Phase 9 (backend API live and CORS-enabled).

**Risks / watch-outs:** deviating from approved Stitch colour scheme; API URL misconfigured across environments; rendering PII if API contract drifts; backend cold-start on Render free tier; preview vs production pointing at different APIs.

---

## Phase Summary
| Phase | Name                          | Key Output                                  |
|-------|-------------------------------|---------------------------------------------|
| 0     | Foundations & Environment     | Skeleton + proven MCP connectivity          |
| 1     | Ingestion & Normalization     | Normalized Groww reviews                     |
| 2     | PII Scrubbing                 | PII-safe dataset                            |
| 3     | Theme Analysis (Groq)         | ≤5 themes in `data/analysis/themes.json`    |
| 4     | Insight Selection (Groq)      | Top 3 + quotes + actions in `insights.json` |
| 5     | Weekly Note Generation (Groq)| ≤250-word note in `weekly_note.md`          |
| 6     | Google Docs Delivery (MCP)    | Google Doc + link                            |
| 7     | Gmail Draft Delivery (MCP)    | Gmail draft (to self/alias)                  |
| 8     | Orchestration & End-to-End    | Repeatable weekly workflow + GitHub Actions (Mon 9:00 AM IST) |
| 9     | Backend API (Render)          | HTTPS API for PII-safe insights + run metadata |
| 10    | Insights Dashboard (Next.js / Vercel) | Stitch-approved UI + Next.js dashboard on Render API |

> Note: note-generation is now its own phase (Phase 5) and Docs/Gmail are split into Phases 6 and 7 for clearer ownership and testing. Phases 9–10 add production **deployment** (Render backend + **Next.js** frontend on Vercel). Exit criteria per phase are in `eval.md`; rationale for key choices is in `decision.md`.
