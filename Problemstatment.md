# Problem Statement

## Selected Product
**Groww — Stocks, Mutual Funds & Gold** (the same product selected in Milestone 1).

All reviews, themes, quotes, and action ideas in this project are based on the **Groww** app on the App Store and Play Store.

## Overview
Build an AI-agent-driven workflow that turns recent **App Store + Play Store reviews of Groww** into a **one-page weekly pulse** and delivers it to your inbox as a draft email.

The weekly pulse must contain:
- **Top themes** — the most important issues/topics users are talking about
- **Real user quotes** — actual snippets from reviews (with PII removed)
- **Three action ideas** — concrete next steps the team can take

Finally, send yourself a draft email containing this weekly note.

## Integration Approach (Important)
This project must integrate with Google services through **MCP (Model Context Protocol) servers — NOT raw Google REST APIs**.

- **Google Docs** → use a Google Docs MCP server to create/write the one-page weekly note as a document.
- **Gmail** → use a Gmail MCP server to create the draft email (sent to yourself/an alias) containing the weekly note.

The agent should call these MCP tools to perform document creation and email drafting, rather than directly calling Google APIs or SDKs. This keeps the workflow tool-driven, portable, and consistent with the MCP architecture used throughout the milestone.

## Who This Helps
- **Product / Growth Teams** → understand what to fix next
- **Support Teams** → know what users are saying and acknowledge it
- **Leadership** → get a quick weekly health pulse

## What You Must Build
1. **Import reviews** from the last 8–12 weeks (capture: rating, title, text, date).
2. **Group reviews into a maximum of 5 themes** (e.g., onboarding/KYC, order execution & trading, mutual fund/SIP investments, payments & withdrawals, app performance/support).
3. **Generate a weekly one-page note** containing:
   - Top 3 themes
   - 3 user quotes
   - 3 action ideas
4. **Write the note to Google Docs** via the Google Docs MCP server.
5. **Draft an email with the note** via the Gmail MCP server (send to yourself/an alias).
6. **Do NOT include any PII.**

## Key Constraints
- Use **public review exports only** — no scraping behind logins.
- **Maximum 5 themes.**
- Keep notes **scannable and ≤ 250 words**.
- **No usernames, emails, or IDs** in any artifacts.
- All Google Docs and Gmail interactions must go through **MCP servers**, not direct API calls.
