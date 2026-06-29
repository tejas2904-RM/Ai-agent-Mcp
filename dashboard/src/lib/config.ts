/** Production Render API — matches `render.yaml` service `groww-pulse-api`. */
export const PRODUCTION_API_URL = "https://groww-pulse-api-uss6.onrender.com";

const LOCAL_API_URL = "http://localhost:8000";

function isLocalhostUrl(url: string): boolean {
  try {
    const hostname = new URL(url).hostname;
    return hostname === "localhost" || hostname === "127.0.0.1";
  } catch {
    return false;
  }
}

/**
 * Resolve the Phase 9 API base URL at request time (server components only).
 *
 * Prefer PULSE_API_URL (server-only, runtime on Vercel). NEXT_PUBLIC_* is inlined
 * at build time and may be stuck on localhost if misconfigured — we ignore localhost
 * outside development.
 */
export function resolveApiBaseUrl(): string {
  const pulseApiUrl = process.env.PULSE_API_URL?.trim();
  if (pulseApiUrl && !isLocalhostUrl(pulseApiUrl)) {
    return pulseApiUrl.replace(/\/$/, "");
  }

  const publicUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (publicUrl && !isLocalhostUrl(publicUrl)) {
    return publicUrl.replace(/\/$/, "");
  }

  if (process.env.NODE_ENV === "development") {
    return LOCAL_API_URL;
  }

  return PRODUCTION_API_URL;
}
