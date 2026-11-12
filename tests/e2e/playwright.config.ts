import os from "node:os";
import path from "node:path";
import { defineConfig } from "@playwright/test";

const secretDir =
  process.env.MITRA_SECRET_DIR || path.join(os.tmpdir(), "mitra-e2e-secrets");
process.env.MITRA_SECRET_DIR = secretDir;

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
      env: {
        MITRA_WEB_ORIGIN: "http://127.0.0.1:3007",
        MITRA_SECRET_DIR: secretDir,
      },
      url: "http://127.0.0.1:8007/browser-fixture",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: "npm run dev -- --port 3007",
      env: {
        MITRA_API_URL: "http://127.0.0.1:8007",
        MITRA_BUILD_DIR: ".next-e2e",
        MITRA_SECRET_DIR: secretDir,
      },
      cwd: process.cwd(),
      url: "http://127.0.0.1:3007/locked",
      reuseExistingServer: false,
      timeout: 60000,
    },
  ],
});
