import { chromium } from "playwright";
import { fetchDocument, validateUrl } from "./browser_transport.mjs";

// Fixed adapter, never a generic evaluator. No page-provided script executes.
let browser;
let context;
const controller = new AbortController();
const deadline = setTimeout(() => controller.abort(), 25000);
async function close() {
  controller.abort();
  await context?.close().catch(() => {});
  await browser?.close().catch(() => {});
}
process.on("SIGTERM", () => void close().finally(() => process.exit(1)));
process.on("SIGINT", () => void close().finally(() => process.exit(1)));

try {
  let input = "";
  for await (const chunk of process.stdin) {
    input += chunk;
    if (input.length > 16000) throw new Error("Input exceeds limit");
  }
  const { url: requested, origins } = JSON.parse(input);
  const validate = (value) => validateUrl(value, origins);
  const { url, body, mime } = await fetchDocument(
    requested,
    origins,
    controller.signal,
  );
  if (controller.signal.aborted) throw new Error("Browser deadline exceeded");
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
    viewport: { width: 1024, height: 768 },
  });
  const page = await context.newPage();
  let served = false;
  await context.route("**/*", async (route) => {
    const request = route.request();
    if (
      !served &&
      request.method() === "GET" &&
      request.url() === url &&
      request.isNavigationRequest() &&
      request.frame() === page.mainFrame()
    ) {
      served = true;
      await route.fulfill({
        status: 200,
        body,
        headers: {
          "content-type": `${mime}; charset=utf-8`,
          "content-security-policy":
            "default-src 'none'; style-src 'unsafe-inline'; form-action 'none'; frame-src 'none'; sandbox",
        },
      });
    } else await route.abort("blockedbyclient");
  });
  page.on("dialog", (dialog) => void dialog.dismiss());
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 10000 });
  // These fixed DOM readers are adapter code, not model- or page-supplied code.
  const title = (await page.title()).slice(0, 300);
  const text = await page.locator("body").innerText({ timeout: 3000 });
  const links = await page.locator("a[href]").evaluateAll((nodes) =>
    nodes.slice(0, 50).map((node) => ({
      text: (node.textContent || "").trim().slice(0, 200),
      url: node.getAttribute("href") || "",
    })),
  );
  const safeLinks = links.flatMap((link) => {
    try {
      return [{ ...link, url: validate(new URL(link.url, url).href) }];
    } catch {
      return [];
    }
  });
  process.stdout.write(
    JSON.stringify({
      url,
      title,
      text: text.slice(0, 16000),
      links: safeLinks,
      truncated: text.length > 16000,
      verified: true,
    }),
  );
} catch {
  process.stderr.write("Read-only browser inspection failed\n");
  process.exitCode = 1;
} finally {
  clearTimeout(deadline);
  await close();
}
