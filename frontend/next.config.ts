import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  devIndicators: false,
  // Longer than the backend's 120-second request budget.
  experimental: { proxyTimeout: 150_000 },
  async rewrites() {
    // Vercel Services routes /backend directly to the backend container.
    if (process.env.VERCEL && !process.env.API_PROXY_URL) return [];
    const backend = (process.env.API_PROXY_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    return [{ source: "/backend/:path*", destination: `${backend}/:path*` }];
  },
};

export default nextConfig;
