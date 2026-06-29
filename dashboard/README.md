# Groww Review Pulse Dashboard

Next.js (App Router) insights dashboard for the weekly Groww Review Pulse. Consumes the Phase 9 read-only API.

## Local development

```powershell
copy .env.example .env.local
npm install
npm run dev
```

Ensure the Phase 9 API is running (`groww-pulse-api` from the repo root). Local dev uses `PULSE_API_URL=http://localhost:8000` in `.env.local`.

**Vercel:** set `PULSE_API_URL` to your Render URL (or rely on the built-in default `https://groww-pulse-api.onrender.com`). Do **not** set `NEXT_PUBLIC_API_URL` to `localhost` on Vercel — it is baked in at build time.

## Vercel deployment

1. Set **Root Directory** to `dashboard` in the Vercel project settings.
2. Configure `NEXT_PUBLIC_API_URL` to your Render backend URL.
3. Add Vercel preview/production domains to `CORS_ORIGINS` on Render.

## Design reference

Approved Google Stitch project `6374599666648079093` — see `docs/google-stitch-frontend-prompts.md`.
