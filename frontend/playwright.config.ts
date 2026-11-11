import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const frontendDir = __dirname;
const repoRoot = path.resolve(frontendDir, "..");
const backendDir = path.join(repoRoot, "backend");
// E2E_PYTHON lets a developer point at a virtualenv interpreter.
const pythonCommand = process.env.E2E_PYTHON || (process.platform === "win32" ? "python" : "python3");
// PW_CHROMIUM_PATH lets an environment with a pre-installed Chromium use it
// instead of the browser that `npx playwright install` downloads in CI.
const chromiumPath = process.env.PW_CHROMIUM_PATH || undefined;

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"]],
  outputDir: "test-results",
  use: {
    baseURL: "http://localhost:3001",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    // Video needs Playwright's own ffmpeg, which a pre-installed browser may lack.
    video: chromiumPath ? "off" : "retain-on-failure",
    launchOptions: chromiumPath ? { executablePath: chromiumPath } : {},
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],
  webServer: [
    {
      command: `${pythonCommand} scripts/serve_e2e.py`,
      cwd: backendDir,
      url: "http://localhost:8001/api/health",
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        DATABASE_URL: "sqlite:///./e2e.sqlite3",
        // The origin the pages are served from: accepted on state-changing requests.
        CORS_ORIGINS: "http://localhost:3001",
        PORT: "8001",
      },
    },
    {
      command: "npx next dev -p 3001",
      cwd: frontendDir,
      url: "http://localhost:3001",
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        // The pages call /api on their own origin; next dev forwards it here.
        API_PROXY_TARGET: "http://localhost:8001",
      },
    },
  ],
});
