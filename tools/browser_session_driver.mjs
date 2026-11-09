import { chromium } from "playwright";
import { createHash } from "node:crypto";
import { createInterface } from "node:readline";
import {
  documentHeaders,
  fetchDocument,
  validateUrl,
} from "./browser_transport.mjs";

let browser,
  context,
  page,
  owner,
  sessionId,
  origins,
  snapshot,
  pendingDocument;
let sequence = 0;
let lifetime;
const digest = (value) => createHash("sha256").update(value).digest("hex");
const canonical = (value) =>
  JSON.stringify(
    Object.fromEntries(
      Object.entries(value).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)),
    ),
  );
async function close() {
  clearTimeout(lifetime);
  await context?.close().catch(() => {});
  await browser?.close().catch(() => {});
}
process.on("SIGTERM", () => void close().finally(() => process.exit(1)));
process.on("SIGINT", () => void close().finally(() => process.exit(1)));

async function state() {
  // Only fixed DOM inspection code executes, never page/model-provided scripts.
  const data = await page.evaluate(() => {
    document
      .querySelectorAll("[data-mitra-ref]")
      .forEach((node) => node.removeAttribute("data-mitra-ref"));
    const controls = [];
    for (const node of document.querySelectorAll("a[href],input,textarea")) {
      if (controls.length === 40) break;
      if (!node.getClientRects().length || node.disabled || node.readOnly)
        continue;
      const link = node.tagName === "A";
      const type = (node.getAttribute("type") || "text").toLowerCase();
      const label = (
        node.getAttribute("aria-label") ||
        node.labels?.[0]?.textContent ||
        node.textContent ||
        node.getAttribute("placeholder") ||
        node.getAttribute("name") ||
        "Unnamed field"
      )
        .trim()
        .slice(0, 160);
      if (
        link &&
        (node.hasAttribute("download") ||
          !["", "_self"].includes(node.getAttribute("target") || ""))
      )
        continue;
      if (
        !link &&
        ((node.tagName !== "TEXTAREA" && !["text", "search"].includes(type)) ||
          /password|secret|token/i.test(
            label + (node.name || "") + (node.autocomplete || ""),
          ))
      )
        continue;
      const ref = `e${controls.length}`;
      node.setAttribute("data-mitra-ref", ref);
      controls.push({
        ref,
        kind: link ? "link" : "text",
        label,
        href: link ? node.getAttribute("href") : "",
        value: link ? "" : node.value.slice(0, 2000),
      });
    }
    return {
      title: document.title.slice(0, 300),
      text: document.body.innerText.slice(0, 16000),
      controls,
      html: document.documentElement.outerHTML,
    };
  });
  const controls = data.controls.flatMap((control) => {
    try {
      return [
        {
          ...control,
          href:
            control.kind === "link"
              ? validateUrl(new URL(control.href, page.url()).href, origins)
              : "",
        },
      ];
    } catch {
      return [];
    }
  });
  return {
    sessionId,
    url: page.url(),
    title: data.title,
    text: data.text,
    controls,
    fingerprint: digest(data.html + JSON.stringify(controls) + page.url()),
    verified: true,
  };
}
async function observe() {
  const current = await state();
  snapshot = {
    ...current,
    snapshotId: digest(current.fingerprint + ++sequence),
  };
  return snapshot;
}
async function command(message) {
  if (message.command === "open") {
    if (browser) throw new Error("Session already open");
    ({ owner, sessionId, origins } = message);
    const doc = await fetchDocument(
      message.url,
      origins,
      AbortSignal.timeout(20000),
    );
    browser = await chromium.launch({
      headless: true,
      timeout: 10000,
      ...(process.platform === "win32" ? { channel: "msedge" } : {}),
    });
    context = await browser.newContext({
      javaScriptEnabled: false,
      acceptDownloads: false,
      serviceWorkers: "block",
      permissions: [],
    });
    page = await context.newPage();
    page.setDefaultTimeout(5000);
    await context.route("**/*", async (route) => {
      const request = route.request();
      if (
        pendingDocument &&
        request.method() === "GET" &&
        request.url() === pendingDocument.url &&
        request.frame() === page.mainFrame() &&
        request.isNavigationRequest()
      ) {
        const document = pendingDocument;
        pendingDocument = null;
        await route.fulfill({
          status: 200,
          body: document.body,
          headers: documentHeaders(document.mime),
        });
      } else await route.abort("blockedbyclient");
    });
    page.on("dialog", (dialog) => void dialog.dismiss());
    pendingDocument = doc;
    await page.goto(doc.url, { waitUntil: "domcontentloaded", timeout: 10000 });
    lifetime = setTimeout(
      () => void close().finally(() => process.exit(0)),
      600000,
    );
    return observe();
  }
  if (!browser || message.owner !== owner || message.sessionId !== sessionId)
    throw new Error("Session owner mismatch");
  if (message.command === "snapshot") return observe();
  if (message.command !== "action") throw new Error("Unknown session command");
  const { args, approval, stepId } = message;
  if (
    !approval ||
    approval.status !== "approved" ||
    approval.taskId !== owner ||
    approval.stepId !== stepId ||
    Date.parse(approval.expiresAt) <= Date.now() ||
    !Number.isFinite(Date.parse(approval.expiresAt)) ||
    approval.digest !== digest("browser_action" + canonical(args))
  )
    throw new Error("Exact approval required");
  if (args.sessionId !== sessionId || args.snapshotId !== snapshot.snapshotId)
    throw new Error("Stale snapshot");
  const current = await state();
  if (current.fingerprint !== snapshot.fingerprint)
    throw new Error("Page changed after observation");
  const control = current.controls.find((item) => item.ref === args.elementId);
  if (!control) throw new Error("Unknown control");
  const locator = page.locator(`[data-mitra-ref="${control.ref}"]`);
  if (
    args.action === "fill" &&
    control.kind === "text" &&
    typeof args.value === "string" &&
    args.value.length <= 2000
  ) {
    await locator.fill(args.value);
    if ((await locator.inputValue()) !== args.value)
      throw new Error("Field verification failed");
  } else if (
    args.action === "click" &&
    control.kind === "link" &&
    args.value === ""
  ) {
    const doc = await fetchDocument(
      control.href,
      origins,
      AbortSignal.timeout(20000),
    );
    // No new document is fetched on the browser's authority: only the approved link.
    // Fulfill at the link URL, then load the validated final URL if it redirected.
    pendingDocument = { ...doc, url: control.href };
    await locator.click({ noWaitAfter: true });
    await page.waitForURL(control.href, {
      waitUntil: "domcontentloaded",
      timeout: 10000,
    });
    if (doc.url !== control.href) {
      pendingDocument = doc;
      await page.goto(doc.url, {
        waitUntil: "domcontentloaded",
        timeout: 10000,
      });
    }
    if (page.url() !== doc.url)
      throw new Error("Navigation verification failed");
  } else
    throw new Error(
      "Only allowlisted links and ordinary text fields are supported",
    );
  return observe();
}

try {
  const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of lines) {
    try {
      if (line.length > 32000) throw new Error("Command too large");
      const message = JSON.parse(line);
      if (message.command === "close") break;
      const result = await command(message);
      process.stdout.write(JSON.stringify({ result }) + "\n");
    } catch {
      process.stdout.write(
        JSON.stringify({
          error:
            "Browser session action refused or failed; open a new session if expired or changed",
        }) + "\n",
      );
      break; // A failure invalidates the session; never retry an uncertain action.
    }
  }
} finally {
  await close();
  process.stdin.destroy();
}
