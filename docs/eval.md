# Evaluation, Testing & Exit Criteria — Per Phase

This file defines how each phase is tested and the **exit criteria** that must be met before moving on. A phase is "done" only when all its exit criteria pass. Phases match `implementationplan.md`. Product under analysis: **Groww — Stocks, Mutual Funds & Gold**.

---

## Phase 0 — Foundations & Environment
**What to test**
- Project skeleton runs cleanly.
- Both MCP servers (Google Docs, Gmail) are reachable.
- MCP tool discovery returns the tools we need (create doc, write content, create draft).

**Exit Criteria**
- [ ] Project builds/runs with no errors.
- [ ] Google Docs MCP server connects and lists tools.
- [ ] Gmail MCP server connects and lists tools.
- [ ] Required tools confirmed present on each server.
- [ ] Sample Groww review export loads without error.

---

## Phase 1 — Review Ingestion & Normalization
**What to test**
- Parser handles both App Store and Play Store exports.
- Correct extraction of `rating`, `title`, `text`, `date`, `source`.
- Date filter keeps only the last 8–12 weeks.

**Exit Criteria**
- [ ] All required fields populated for every record.
- [ ] Only reviews within the 8–12 week window remain.
- [ ] Malformed rows are skipped/logged, not crashing the run.
- [ ] Source is correctly tagged (`app_store` / `play_store`).
- [ ] Obvious duplicates removed; dates/ratings standardized.
- [ ] Reviews kept only if **English**, **more than 6 words**, and **no emojis** in stored text.

---

## Phase 2 — PII Scrubbing
**What to test**
- Emails, phone numbers, usernames, and IDs are removed/masked.
- Scrubbing runs before any LLM call.

**Exit Criteria**
- [ ] Zero emails/phones/usernames/IDs detected in scrubbed dataset.
- [ ] Verification log confirms scrubbed categories.
- [ ] No PII present in any data passed downstream.
- [ ] Review meaning preserved (not over-scrubbed).

---

## Phase 3 — Theme Analysis (LLM)
**What to test**
- Number of themes never exceeds 5.
- Themes are relevant to Groww and reviews are assigned to them.
- Each theme has a prominence/sentiment signal.

**Exit Criteria**
- [ ] ≤ 5 themes produced.
- [ ] Every analyzed review is assigned to a theme.
- [ ] Each theme has a volume/sentiment indicator.
- [ ] No single theme trivially absorbs everything.

---

## Phase 4 — Insight Selection
**What to test**
- Top 3 themes selected with a clear ranking basis.
- Quotes map back to real (scrubbed) reviews.
- Action ideas are specific and tied to themes.

**Exit Criteria**
- [ ] Exactly 3 top themes selected.
- [ ] Exactly 3 PII-free quotes, each traceable to a source review.
- [ ] Exactly 3 actionable, theme-linked action ideas.

---

## Phase 5 — Weekly Note Generation
**What to test**
- Note contains header + Top 3 themes, 3 quotes, 3 action ideas.
- Word count ≤ 250.
- Output is scannable and contains no PII.

**Exit Criteria**
- [ ] Word count ≤ 250 (automated check).
- [ ] All required sections present with 3 items each.
- [ ] No PII in final note (automated re-scan).
- [ ] Layout is scannable (headings/bullets).

---

## Phase 6 — Google Docs Delivery (via MCP)
**What to test**
- Doc creation via the Google Docs MCP tool.
- Note content written correctly and completely.

**Exit Criteria**
- [ ] Google Doc is created via MCP (not direct API).
- [ ] Doc contains the full, correctly formatted note.
- [ ] Doc has a clear, consistent title (product + week range).
- [ ] A valid document link is returned/stored.

---

## Phase 7 — Gmail Draft Delivery (via MCP)
**What to test**
- Draft creation via the Gmail MCP tool.
- Draft is addressed to self/alias and is NOT auto-sent.

**Exit Criteria**
- [ ] Gmail draft is created via MCP (not direct API).
- [ ] Draft contains the note and/or Doc link.
- [ ] Subject is clear and consistent.
- [ ] Recipient is self/alias; nothing is auto-sent.

---

## Phase 8 — Orchestration & End-to-End
**What to test**
- Full pipeline runs from a single entry point.
- Failure handling, retries, and logging behave correctly.

**Exit Criteria**
- [ ] One command/trigger runs ingestion → note → Doc → Gmail draft.
- [ ] Run completes without manual intervention.
- [ ] Errors are handled gracefully and logged.
- [ ] Re-running for the same week does not create confusing duplicates.
- [ ] Final artifacts (Doc + draft) are PII-free and within constraints.

---

## Global Acceptance (Project Done)
- [ ] Weekly note ≤ 250 words, no PII, top 3 themes + 3 quotes + 3 actions.
- [ ] Analysis based on Groww App Store + Play Store reviews (last 8–12 weeks).
- [ ] Google Doc produced via MCP.
- [ ] Gmail draft produced via MCP (to self/alias).
- [ ] Only public review exports used (no scraping behind logins).
