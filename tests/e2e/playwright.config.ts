import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.ts",
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: "http://127.0.0.1:3007",
    ...(process.platform === "win32" ? { channel: "msedge" } : {}),
  },
  webServer: [
    {
      command:
        (process.platform === "win32"
          ? ".venv\\Scripts\\python.exe"
          : ".venv/bin/python") +
        " -m uvicorn tests.e2e_app:app --host 127.0.0.1 --port 8007 --no-access-log",
      cwd: process.cwd(),
      env: { MITRA_WEB_ORIGIN: "http://127.0.0.1:3007" },
      url: "http://127.0.0.1:8007/api/v1/health",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "npm run dev -- --port 3007",
      env: {
        MITRA_API_URL: "http://127.0.0.1:8007",
        MITRA_BUILD_DIR: ".next-e2e",
      },
      cwd: process.cwd(),
      url: "http://127.0.0.1:3007",
      reuseExistingServer: false,
      timeout: 60000,
    },
  ],
});
