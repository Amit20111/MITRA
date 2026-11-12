import { readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const api = process.env.MITRA_API_URL || "http://127.0.0.1:8000";
const web = process.env.MITRA_WEB_ORIGIN || "http://127.0.0.1:3000";
const secretDir =
  process.env.MITRA_SECRET_DIR ||
  (process.platform === "win32"
    ? path.join(
        process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local"),
        "MITRA",
      )
    : path.join(
        process.env.XDG_STATE_HOME || path.join(os.homedir(), ".local", "state"),
        "mitra",
      ));

const keyPath = path.join(secretDir, "local-api.key");
let key;
try {
  key = readFileSync(keyPath, "ascii").trim();
} catch {
  console.error(
    `Could not read ${keyPath}. Start the MITRA API first so it creates the local key.`,
  );
  process.exit(1);
}

const response = await fetch(`${api}/api/v1/auth/launch`, {
  method: "POST",
  headers: { "x-mitra-local-key": key },
});
if (!response.ok) {
  const detail = await response.text().catch(() => "");
  console.error(`Failed to issue launch link (${response.status}): ${detail}`);
  process.exit(1);
}
const { code, expiresAt } = await response.json();
const url = `${web.replace(/\/+$/, "")}/unlock?code=${encodeURIComponent(code)}`;
if (process.argv.includes("--url-only")) {
  console.log(url);
} else {
  console.log(`One-time MITRA launch link (expires ${expiresAt}):`);
  console.log(url);
}
