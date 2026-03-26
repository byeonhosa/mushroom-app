import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

const frontendDir = __dirname;
const repoRoot = path.resolve(frontendDir, "..");
const backendDir = path.join(repoRoot, "backend");
const pythonCommand = process.platform === "win32" ? "python" : "python3";

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
    video: "retain-on-failure",
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
        NEXT_PUBLIC_API_BASE: "http://localhost:8001/api",
      },
    },
  ],
});
