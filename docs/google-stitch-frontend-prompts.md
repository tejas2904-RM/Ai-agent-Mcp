# Google Stitch UI Prompts — Groww Review Pulse Dashboard

Use these prompts in **[Google Stitch](https://stitch.withgoogle.com)** to generate high-fidelity UI mockups for **Phase 10** (Next.js dashboard on Vercel).

**Product context** (from `Problemstatment.md`):
- **Product analyzed:** Groww — Stocks, Mutual Funds & Gold
- **Audience:** Product / Growth teams, Support teams, Leadership
- **Weekly pulse contains:** Top 3 themes, 3 real user quotes (PII-free), 3 action ideas
- **Dashboard is read-only** — no login, no pipeline triggers in v1
- **Constraints:** Scannable layout, professional fintech analytics feel, no PII (no emails, usernames, phone numbers)

Paste **one prompt per screen**. Start with the **Shared Design System** block on the first screen; reuse it on follow-up screens for consistency.

---

## Approved Stitch screens (Phase 10 reference)

These screens are the **visual source of truth** for the Next.js dashboard. Project ID: `6374599666648079093`.

| Screen | Stitch screen ID | Next.js route |
|--------|------------------|---------------|
| Main dashboard (latest weekly pulse) | `490cfa088c134c2abffc140c5a3f829a` | `/` |
| Run history & timeline | `08cd0bc5260a44d0879ea6c766c2fd1d` | `/runs` |

Documented in `docs/implementationplan.md` (Phase 10) and `docs/architecture.md` (§5.14).

---

## Shared Design System (copy into every prompt)

```text
DESIGN SYSTEM (REQUIRED):
- Platform: Web, Desktop-first (1440px), responsive down to mobile
- Theme: Light, clean, trustworthy fintech analytics dashboard
- Background: Off-white (#F8FAFC)
- Surface / Cards: White (#FFFFFF) with soft elevation
- Primary Accent: Groww-inspired teal-green (#00B386) for CTAs, active nav, positive badges
- Secondary Accent: Deep navy (#0F172A) for headings and nav text
- Warning / Negative sentiment: Coral red (#EF4444) for low-star signals
- Mixed sentiment: Amber (#F59E0B)
- Positive sentiment: Emerald (#10B981)
- Text Primary: Slate 900 (#0F172A)
- Text Secondary: Slate 500 (#64748B)
- Text Muted: Slate 400 (#94A3B8)
- Typography: Inter or similar geometric sans — bold 32px hero, semibold 20px section titles, regular 14px body, 12px captions
- Cards: 12px border radius, 1px border #E2E8F0, subtle shadow (0 1px 3px rgba(15,23,42,0.08))
- Buttons: 8px radius; primary filled teal-green; secondary outline slate
- Badges: Pill shape, small caps labels for volume (HIGH / MEDIUM / LOW) and sentiment (NEGATIVE / MIXED / POSITIVE)
- Spacing: 8px grid; generous whitespace; bento-style card grid for themes
- Icons: Simple line icons (calendar, document, mail, chart, quote)
- Accessibility: High contrast text, clear hierarchy, no decorative clutter
```

---

## Prompt 1 — Main Dashboard (Latest Weekly Pulse)

```text
A professional fintech analytics dashboard called "Groww Review Pulse" — weekly App Store and Play Store review insights for the Groww investing app. Clean SaaS vibe, trustworthy, executive-ready.

DESIGN SYSTEM (REQUIRED):
- Platform: Web, Desktop-first (1440px), responsive down to mobile
- Theme: Light, clean, trustworthy fintech analytics dashboard
- Background: Off-white (#F8FAFC)
- Surface / Cards: White (#FFFFFF) with soft elevation
- Primary Accent: Groww-inspired teal-green (#00B386) for CTAs and active states
- Secondary Accent: Deep navy (#0F172A) for headings
- Warning / Negative: Coral red (#EF4444); Mixed: Amber (#F59E0B); Positive: Emerald (#10B981)
- Typography: Inter — bold hero, semibold section titles, regular body
- Cards: 12px radius, subtle border and shadow

PAGE STRUCTURE:
1. **Top navigation bar:** Left — logo mark + "Groww Review Pulse" wordmark. Center — week selector dropdown showing "Jun 08 - 26, 2026". Right — status pill "Last run: Success" in green, link buttons "Open Google Doc" and "Gmail Draft" with document/mail icons.
2. **Hero section:** Headline "Weekly Review Pulse" with subtext "Groww — Stocks, Mutual Funds & Gold · 600 reviews analyzed". Small metadata row: App Store + Play Store icons, star rating mix, date range badge.
3. **Top 3 Themes — bento card grid (3 equal cards):**
   - Card 1 (rank #1): "Trading Experience" — HIGH volume, NEGATIVE sentiment badges. One-line summary. Stats: 413 reviews, avg 3.75★, 30% low-star. Severity bar in red.
   - Card 2 (rank #2): "Payment and Withdrawal Issues" — LOW volume, NEGATIVE. 25 reviews, 1.92★, 76% low-star.
   - Card 3 (rank #3): "App UX and Support" — MEDIUM volume, MIXED. 126 reviews, 3.61★, 29% low-star.
4. **Two-column section below themes:**
   - Left column "User Quotes" — 3 quote cards with left border accent, star rating, source badge (App Store / Play Store), theme tag. Use placeholder quote text only (no names or emails).
   - Right column "Action Ideas" — numbered list 1–3 with checkmark icons, each tied to a theme name.
5. **Weekly Note preview card:** Collapsible markdown-style preview, max ~250 words, sections "Top 3 Themes", "User Quotes", "Action Ideas". Word count badge "199 words".
6. **Footer:** Subtle gray bar — "Read-only dashboard · Data refreshed weekly · No PII displayed"

CONTENT TONE: Analytical, calm, no alarmist colors except on severity badges. No user avatars or personal identifiers.
```

---

## Prompt 2 — Run History & Timeline

```text
A run history and audit timeline page for "Groww Review Pulse" — same fintech analytics dashboard family. Minimal, data-dense but readable.

DESIGN SYSTEM (REQUIRED):
[Use Shared Design System block from above]

PAGE STRUCTURE:
1. **Header:** Breadcrumb "Dashboard / Run History". Page title "Pipeline Runs". Filter chips: All, Success, Failed, Skipped delivery.
2. **Timeline list (vertical):** Each run as a card row with:
   - Run ID (truncated hash), week range "Jun 08 - 26, 2026"
   - Status badge (Success green / Failed red)
   - Timestamps: started, completed
   - Chips: "Re-run", "Delivery skipped" when applicable
   - Mini stats: normalized count, scrubbed count, Groq calls, note word count
   - Links: Google Doc URL, Gmail draft ID
3. **Empty state variant (show in separate frame):** Illustration of empty inbox/calendar, text "No runs yet — weekly pulse runs every Monday 9:00 AM IST", secondary button "View documentation".
4. **Sidebar (optional):** Quick stats — total runs, success rate, latest week.

VIBE: Operations console meets executive summary. Monospace for run IDs only.
```

---

## Prompt 3 — Mobile Dashboard (Responsive)

```text
Mobile-first responsive version of the Groww Review Pulse weekly dashboard (375px width). Same brand as desktop but stacked single-column layout.

DESIGN SYSTEM (REQUIRED):
[Use Shared Design System block from above — mobile adjustments: 16px side padding, full-width cards, sticky top bar]

PAGE STRUCTURE:
1. **Sticky header:** Hamburger hidden (single page), title "Review Pulse", week dropdown, green status dot.
2. **Hero:** Compact — week range, review count, two icon buttons for Doc and Gmail.
3. **Theme cards:** Stacked vertically, swipeable horizontal scroll OR full-width stacked cards with rank number large on left.
4. **Quotes:** Single quote per card, carousel dots below for 3 quotes.
5. **Action ideas:** Accordion list, expand each item.
6. **Bottom sheet style CTA:** "View full weekly note" button fixed above safe area.

Touch targets minimum 44px. No tiny text.
```

---

## Prompt 4 — Loading & Error States

```text
Three UI states for Groww Review Pulse dashboard — loading skeleton, API cold-start error, and no-data empty state. Same design system.

DESIGN SYSTEM (REQUIRED):
[Use Shared Design System block from above]

PAGE STRUCTURE — show 3 panels side by side (or 3 separate mobile screens):

**Panel A — Loading:**
- Skeleton shimmer on hero, 3 theme card placeholders, quote blocks, action list
- Text "Fetching latest pulse…"

**Panel B — API unavailable (Render cold start):**
- Friendly illustration, headline "Dashboard temporarily unavailable"
- Body "The insights API is waking up. This can take up to 60 seconds on free tier."
- Primary button "Retry" in teal-green

**Panel C — No data yet:**
- Illustration of empty chart
- Headline "No weekly pulse yet"
- Body "The first automated run happens Monday 9:00 AM IST. You can also trigger a manual run from GitHub Actions."
- Secondary link "How it works"

Keep tone helpful, not technical jargon-heavy.
```

---

## Prompt 5 — Theme Detail Drill-Down (Optional)

```text
A theme detail drill-down screen for Groww Review Pulse when user clicks a theme card. Desktop 1440px.

DESIGN SYSTEM (REQUIRED):
[Use Shared Design System block from above]

PAGE STRUCTURE:
1. **Back link:** "← Back to weekly pulse"
2. **Theme header:** "Trading Experience" with HIGH volume + NEGATIVE sentiment badges. Large severity score "152.8". Summary paragraph.
3. **Stats row:** 4 metric tiles — review count, avg rating, low-star %, source split (App Store vs Play Store horizontal bar).
4. **Related quote:** Highlighted quote card from this theme.
5. **Related action:** Single action idea card with theme mapping.
6. **Chart placeholder:** Simple bar chart "Rating distribution" (1–5 stars) — decorative, muted colors.

Analytical, not marketing. No stock photos.
```

---

## Stitch workflow tips

1. **Generate Screen 1 first** — it establishes the visual language for the project.
2. In Stitch, save a **DESIGN.md** (or `.stitch/DESIGN.md`) from the approved screen and reference it on later prompts.
3. **Iterate with edit prompts** — e.g. "Make theme cards equal height" or "Increase quote card left border to 4px teal".
4. **Export** approved screens to Figma or HTML/CSS for the Next.js `dashboard/` implementation.
5. **Do not include** real user emails, phone numbers, or names in generated content — use anonymous quotes only.

---

## Mapping to Next.js implementation (Phase 10)

| Stitch screen | Next.js route / component |
|---------------|---------------------------|
| Main Dashboard | `app/page.tsx` — latest pulse from `GET /api/v1/pulse/latest` |
| Run History | `app/runs/page.tsx` — `GET /api/v1/runs` |
| Week selector | Client component — `GET /api/v1/pulse/weeks` |
| Loading / Error | `loading.tsx`, `error.tsx`, empty state component |
| Theme drill-down | `app/themes/[slug]/page.tsx` (optional v1.1) |

---

## Reference links

- [Google Stitch](https://stitch.withgoogle.com)
- [Stitch Prompt Guide](https://discuss.ai.google.dev/t/stitch-prompt-guide/83844)
- Project problem statement: `Problemstatment.md`
- Phase 10 plan: `docs/implementationplan.md`
- API shapes: Phase 9 `GET /api/v1/pulse/latest` response
