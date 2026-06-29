import type { NextConfig } from "next";
import { PRODUCTION_API_URL } from "./src/lib/config";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  env: {
    // Baked at build — production fallback if Vercel env vars are missing/wrong.
    PULSE_API_URL: process.env.PULSE_API_URL ?? PRODUCTION_API_URL,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? PRODUCTION_API_URL,
  },
};

export default nextConfig;
