import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import openapiTS, { astToString } from "openapi-typescript";

function readLocalKey() {
  const dir =
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
  try {
    return readFileSync(path.join(dir, "local-api.key"), "ascii").trim();
  } catch {
    return "";
  }
}

const live = process.argv.includes("--live");
const check = process.argv.includes("--check");
let schema;
if (live) {
  const key = readLocalKey();
  const response = await fetch(
    process.env.MITRA_OPENAPI_URL || "http://127.0.0.1:8000/openapi.json",
    key ? { headers: { "x-mitra-local-key": key } } : undefined,
  );
  if (!response.ok)
    throw new Error(`OpenAPI request failed: ${response.status}`);
  schema = await response.json();
} else {
  const python =
    process.env.MITRA_PYTHON ||
    (process.platform === "win32"
      ? ".venv/Scripts/python.exe"
      : ".venv/bin/python");
  const result = spawnSync(
    python,
    [
      "-c",
      "import json; from apps.api.main import app; print(json.dumps(app.openapi()))",
    ],
    { encoding: "utf8" },
  );
  if (result.status !== 0) throw new Error(result.stderr);
  schema = JSON.parse(result.stdout);
}
const output =
  "// Generated from apps/api Pydantic contracts. Do not edit.\n" +
  astToString(await openapiTS(schema));
const target = "packages/contracts/api.d.ts";
if (check) {
  if (readFileSync(target, "utf8") !== output)
    throw new Error("Generated contracts are stale. Run npm run gen:types.");
  console.log("Generated contracts are current.");
} else {
  mkdirSync("packages/contracts", { recursive: true });
  writeFileSync(target, output);
  console.log(`Generated ${target}`);
}
