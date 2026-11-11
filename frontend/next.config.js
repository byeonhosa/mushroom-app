/** @type {import('next').NextConfig} */
const nextConfig = {
  // A self-contained server in .next/standalone: a smaller image and less
  // memory on the 2 GB droplet. `npm run start` runs the same server.
  output: "standalone",
};
module.exports = nextConfig;
