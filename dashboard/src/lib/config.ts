/** Production Render API — matches `render.yaml` service name `groww-pulse-api`. */
export const PRODUCTION_API_URL = "https://groww-pulse-api.onrender.com";

export function resolveApiBaseUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (fromEnv) {
    return fromEnv.replace(/\/$/, "");
  }

  // Vercel / production builds must not fall back to localhost
  if (process.env.NODE_ENV === "production" || process.env.VERCEL) {
    return PRODUCTION_API_URL;
  }

  return "http://localhost:8000";
}
