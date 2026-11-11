/** @type {import('next').NextConfig} */
const nextConfig = {
  // A self-contained server in .next/standalone: a smaller image and less
  // memory on the 2 GB droplet. `npm run start` runs the same server.
  output: "standalone",

  // CLAUDE.md is this repository's instruction file for coding agents; do not
  // let `next dev` add an AGENTS.md of its own beside it.
  agentRules: false,

  // The browser always calls the API on the page's own origin (lib/api.ts).
  // In production the Caddy proxy routes /api/* to the API before a request
  // ever reaches this server. In development and in the browser tests there
  // is no proxy, so this server forwards /api/* itself.
  async rewrites() {
    const target = process.env.API_PROXY_TARGET;
    if (!target) return [];
    return [{ source: "/api/:path*", destination: `${target.replace(/\/$/, "")}/api/:path*` }];
  },
};
module.exports = nextConfig;
