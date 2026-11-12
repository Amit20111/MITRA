import { test, expect, type Page } from "@playwright/test";
import { readFileSync, existsSync } from "node:fs";
import os from "node:os";
import path from "node:path";

const secretDir =
  process.env.MITRA_SECRET_DIR || path.join(os.tmpdir(), "mitra-e2e-secrets");
const apiOrigin = process.env.MITRA_API_URL || "http://127.0.0.1:8007";

function localKey(): string {
  return readFileSync(path.join(secretDir, "local-api.key"), "ascii").trim();
}

async function issueLaunchCode(): Promise<string> {
  const response = await fetch(`${apiOrigin}/api/v1/auth/launch`, {
    method: "POST",
    headers: { "x-mitra-local-key": localKey() },
  });
  expect(response.status).toBe(200);
  const data = (await response.json()) as { code: string };
  return data.code;
}

async function unlockPage(page: Page): Promise<void> {
  const code = await issueLaunchCode();
  await page.goto(`/unlock?code=${encodeURIComponent(code)}`);
  await expect(page).toHaveURL(/\/$/);
}

test.beforeEach(async ({ page }) => {
  await unlockPage(page);
});

function sameOriginHeader(headers?: Record<string, string>) {
  return { Origin: "http://127.0.0.1:3007", ...headers };
}

test("send -> proposed write -> approval -> verified file -> persisted reload", async ({
  page,
}) => {
  const settings = await (await page.request.get("/api/v1/settings")).json();
  const target = path.join(settings.workspace, "approved.txt");
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await expect(page.locator(".mechanical-collar")).toHaveCSS(
    "animation-name",
    "signal-orbit",
  );
  await page.emulateMedia({ reducedMotion: "reduce" });
  await expect(page.locator(".mechanical-collar")).toHaveCSS(
    "animation-name",
    "none",
  );
  await expect(
    page.getByRole("region", { name: "System overview" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 1440, height: 1000 });
  for (const viewport of [
    { width: 1366, height: 768 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await expect(page.getByLabel("Message MITRA")).toBeInViewport({ ratio: 1 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollHeight <= window.innerHeight,
      ),
    ).toBe(true);
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "test-results/command-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/command-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page
    .getByLabel("Message MITRA")
    .fill("Create approved.txt with a short note");
  await page.getByRole("button", { name: "Send message", exact: true }).click();
  await expect(page.getByText("A quick check before I continue")).toBeVisible({
    timeout: 15000,
  });
  expect(existsSync(target)).toBe(false);
  await page.getByText("Review exact write content").click();
  await expect(
    page.getByText("Verified by the browser test", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByText("Approved by you")).toBeVisible();
  await expect(
    page.locator(".status-pill").filter({ hasText: "Completed" }),
  ).toBeVisible();
  expect(readFileSync(target, "utf8")).toBe("Verified by the browser test");
  await page.reload();
  await expect(page.getByText("Approved by you")).toBeVisible();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(page.getByText("Allowed workspace")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});

test("browser field waits for exact approval and then verifies", async ({
  page,
}) => {
  await page.goto("/");
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes("/api/v1/conversations") && r.ok(),
    ),
    page.getByRole("button", { name: /New conversation/ }).click(),
  ]);
  await page
    .getByLabel("Message MITRA")
    .fill("Fill browser note with the verified value");
  const sendButton = page.getByRole("button", {
    name: "Send message",
    exact: true,
  });
  await expect(sendButton).toBeEnabled({ timeout: 15000 });
  await sendButton.click();
  await expect(page.getByText("Review exact browser action")).toBeVisible({
    timeout: 20000,
  });
  const pendingTasks = await (await page.request.get("/api/v1/tasks")).json();
  const pending = pendingTasks.find(
    (task: { status: string; steps: { tool: string }[] }) =>
      task.status === "awaiting_approval" &&
      task.steps.at(-1)?.tool === "browser_action",
  );
  expect(pending).toBeTruthy();
  expect(pending.steps[0].result.controls[0].value).toBe("");
  await page.getByText("Review exact browser action").click();
  await expect(page.locator(".approval-card pre")).toContainText(
    "Verified browser value",
  );
  await expect(page.locator(".approval-card pre")).toContainText(
    pending.steps.at(-1).arguments.snapshotId,
  );
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByText("Approved by you")).toBeVisible();
  await expect(
    page.locator(".status-pill").filter({ hasText: "Completed" }),
  ).toBeVisible({ timeout: 15000 });
  const finished = await (
    await page.request.get(`/api/v1/tasks/${pending.id}`)
  ).json();
  expect(finished.steps.at(-1).result.controls[0].value).toBe(
    "Verified browser value",
  );
  expect(finished.steps.at(-1).status).toBe("verified");
});

test("runtime pairing reports heartbeat and revokes access", async ({
  page,
  request,
}) => {
  await page.goto("/settings");
  await page
    .getByRole("button", { name: "Generate runtime pairing code" })
    .click();
  const code = await page.getByLabel("Runtime pairing code").innerText();
  const [pairingId, secret] = code.split(".");
  const claim = await request.post(`${apiOrigin}/api/v1/runtime/pairing/claim`, {
    data: {
      pairingId,
      code: secret,
      name: "E2E runtime",
      platform: "windows",
      protocolVersion: 1,
    },
  });
  expect(claim.status()).toBe(200);
  const credential = await claim.json();
  const heartbeat = () =>
    request.post(
      `${apiOrigin}/api/v1/runtime/${credential.runtimeId}/heartbeat`,
      {
        headers: { Authorization: `Bearer ${credential.token}` },
        data: { protocolVersion: 1, runtimeVersion: "0.1.0" },
      },
    );
  expect((await heartbeat()).status()).toBe(200);
  await expect(
    page.locator(".runtime-settings .outline-badge").first(),
  ).toHaveText("Connected", { timeout: 10000 });
  await expect(page.locator(".runtime-settings")).toContainText(
    "Pairing alone grants heartbeat only",
  );
  await page.getByRole("button", { name: "Revoke runtime access" }).click();
  await expect(
    page.locator(".runtime-settings .outline-badge").first(),
  ).toHaveText("Not paired");
  expect((await heartbeat()).status()).toBe(401);
});

test("memory records persist, edit and delete", async ({ page }) => {
  await page.goto("/memory");
  await page
    .getByLabel("Memory key", { exact: true })
    .fill("editor preference");
  await page
    .getByLabel("Fact or preference")
    .fill("Use the compact editor layout");
  await page.getByRole("button", { name: "Add memory", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Edit editor preference" }),
  ).toBeVisible();
  await page.reload();
  await page.getByRole("button", { name: "Edit editor preference" }).click();
  await page
    .getByLabel("Fact or preference")
    .fill("Use a spacious editor layout");
  await page.getByRole("button", { name: "Save memory changes" }).click();
  await expect(page.locator(".memory-grid")).toContainText(
    "Use a spacious editor layout",
  );
  await page.getByRole("button", { name: "Delete editor preference" }).click();
  await expect(
    page.getByText("No memories saved.", { exact: false }),
  ).toBeVisible();
});

test("desktop operation waits for consent and stop prevents dispatch", async ({
  page,
  request,
}) => {
  const code = await (
    await page.request.post("/api/v1/runtime/pairing", {
      headers: sameOriginHeader(),
    })
  ).json();
  const [pairingId, secret] = code.pairingCode.split(".");
  const credential = await (
    await request.post(`${apiOrigin}/api/v1/runtime/pairing/claim`, {
      data: { pairingId, code: secret, name: "Desktop fixture" },
    })
  ).json();
  const headers = { Authorization: `Bearer ${credential.token}` };
  await request.post(
    `${apiOrigin}/api/v1/runtime/${credential.runtimeId}/heartbeat`,
    {
      headers,
      data: { desktopEnabled: true },
    },
  );
  await page.goto("/settings");
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes("/api/v1/runtime/desktop/jobs") && r.ok(),
    ),
    page.getByRole("button", { name: "Inspect windows", exact: true }).click(),
  ]);
  expect(
    await (
      await request.post(
        `${apiOrigin}/api/v1/runtime/${credential.runtimeId}/poll`,
        {
          headers,
        },
      )
    ).json(),
  ).toBeNull();
  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/decision") && r.ok()),
    page.getByRole("button", { name: "Approve desktop operation" }).click(),
  ]);
  const job = await (
    await request.post(
      `${apiOrigin}/api/v1/runtime/${credential.runtimeId}/poll`,
      {
        headers,
      },
    )
  ).json();
  expect(job.state).toBe("dispatched");
  await request.post(
    `${apiOrigin}/api/v1/runtime/${credential.runtimeId}/${job.id}/result`,
    {
      headers,
      data: {
        success: true,
        message: "Inspected",
        targets: [
          { id: "test-target", title: "Synthetic window", processId: 1 },
        ],
      },
    },
  );
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes("/api/v1/runtime/desktop/jobs") && r.ok(),
    ),
    page
      .getByRole("button", { name: "Focus Synthetic window", exact: true })
      .click(),
  ]);
  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/decision") && r.ok()),
    page.getByRole("button", { name: "Approve desktop operation" }).click(),
  ]);
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes("/api/v1/runtime/desktop/stop") && r.ok(),
    ),
    page
      .getByRole("button", { name: "Stop desktop & clear captures" })
      .click(),
  ]);
  expect(
    await (
      await request.post(
        `${apiOrigin}/api/v1/runtime/${credential.runtimeId}/poll`,
        {
          headers,
        },
      )
    ).json(),
  ).toBeNull();
  await page.request.post("/api/v1/runtime/revoke", {
    headers: sameOriginHeader(),
    data: { runtimeId: credential.runtimeId },
  });
});

test("voice disabled state and reviewed text never auto-sends", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Voice input information" }).click();
  const dialog = page.getByRole("dialog", {
    name: "Voice, with you in control",
  });
  await expect(
    dialog.getByRole("button", { name: "Start recording", exact: true }),
  ).toBeDisabled();
  await dialog
    .getByLabel("Voice transcript", { exact: true })
    .fill("A reviewed speech request");
  const before = await (await page.request.get("/api/v1/tasks")).json();
  await dialog
    .getByRole("button", { name: "Use reviewed transcript", exact: true })
    .click();
  await expect(page.getByLabel("Message MITRA")).toHaveValue(
    "A reviewed speech request",
  );
  const after = await (await page.request.get("/api/v1/tasks")).json();
  expect(after.length).toBe(before.length);
});

test("voice recording review, cancellation and playback use explicit controls", async ({
  page,
}) => {
  let transcriptions = 0;
  await page.route("**/api/v1/voice/status", (route) =>
    route.fulfill({
      json: {
        enabled: true,
        transcription: true,
        speech: true,
        message: "Synthetic speech provider",
        maxRecordingSeconds: 30,
      },
    }),
  );
  await page.route("**/api/v1/voice/transcribe", (route) => {
    transcriptions++;
    return route.fulfill({
      json: { text: "Review this synthetic transcript", reviewRequired: true },
    });
  });
  await page.route("**/api/v1/voice/speak", (route) =>
    route.fulfill({ json: { audio: "SUQzdGVzdA==", mime: "audio/mpeg" } }),
  );
  await page.addInitScript(() => {
    const fixture = { tracksStopped: 0, paused: 0 };
    Object.defineProperty(window, "voiceFixture", { value: fixture });
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
      value: async () => ({
        getTracks: () => [
          {
            stop: () => {
              fixture.tracksStopped++;
            },
          },
        ],
      }),
    });
    class Recorder {
      state = "inactive";
      onstop: (() => void) | null = null;
      ondataavailable: ((event: { data: Blob }) => void) | null = null;
      onerror: (() => void) | null = null;
      static isTypeSupported() {
        return true;
      }
      start() {
        this.state = "recording";
      }
      stop() {
        this.state = "inactive";
        this.ondataavailable?.({ data: new Blob(["synthetic audio"]) });
        this.onstop?.();
      }
    }
    class Player {
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;
      async play() {}
      pause() {
        fixture.paused++;
      }
    }
    Object.defineProperty(window, "MediaRecorder", { value: Recorder });
    Object.defineProperty(window, "Audio", { value: Player });
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Voice input information" }).click();
  const dialog = page.getByRole("dialog", {
    name: "Voice, with you in control",
  });
  await dialog
    .getByRole("button", { name: "Start recording", exact: true })
    .click();
  await expect(dialog.getByRole("status")).toContainText("Recording");
  await dialog
    .getByRole("button", { name: "Stop & transcribe", exact: true })
    .click();
  await expect(
    dialog.getByLabel("Voice transcript", { exact: true }),
  ).toHaveValue("Review this synthetic transcript");
  expect(transcriptions).toBe(1);
  await dialog
    .getByRole("button", { name: "Start recording", exact: true })
    .click();
  await dialog
    .getByRole("button", { name: "Cancel recording / stop playback" })
    .click();
  await expect(dialog.getByRole("status")).toContainText("Idle");
  expect(transcriptions).toBe(1);
  await dialog.getByRole("button", { name: "Read text aloud" }).click();
  await expect(dialog.getByRole("status")).toContainText("Playing");
  await dialog
    .getByRole("button", { name: "Cancel recording / stop playback" })
    .click();
  await expect(dialog.getByRole("status")).toContainText("Idle");
  const counts = await page.evaluate(
    () =>
      (
        window as unknown as {
          voiceFixture: { tracksStopped: number; paused: number };
        }
      ).voiceFixture,
  );
  expect(counts.tracksStopped).toBeGreaterThanOrEqual(2);
  expect(counts.paused).toBeGreaterThanOrEqual(1);
});

test("unauthenticated visitors see locked screen, launch link unlocks once, and lock revokes session", async ({
  browser,
}) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  try {
    const first = await page.goto("/");
    expect(first?.headers()["content-security-policy"]).toContain(
      "default-src 'self'",
    );
    expect(first?.headers()["x-frame-options"]).toBe("DENY");
    await expect(
      page.getByRole("heading", { name: "MITRA is locked" }),
    ).toBeVisible();
    const denied = await page.request.get("/api/v1/settings");
    expect(denied.status()).toBe(401);

    const code = await issueLaunchCode();
    await page.goto(`/unlock?code=${encodeURIComponent(code)}`);
    await expect(page.getByLabel("Message MITRA")).toBeVisible();

    const freshContext = await browser.newContext();
    const freshPage = await freshContext.newPage();
    await freshPage.goto(`/unlock?code=${encodeURIComponent(code)}`);
    await expect(
      freshPage.getByRole("heading", { name: "MITRA is locked" }),
    ).toBeVisible();
    await freshContext.close();

    await page.goto("/settings");
    await page.getByRole("button", { name: "Lock session" }).click();
    await expect(
      page.getByRole("heading", { name: "MITRA is locked" }),
    ).toBeVisible();
    expect((await page.request.get("/api/v1/settings")).status()).toBe(401);
  } finally {
    await context.close();
  }
});
