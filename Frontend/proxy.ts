import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { NextResponse, type NextRequest } from "next/server";

/*
 * Local security boundary for the MITRA interface.
 *
 * - Refuses non-loopback Host headers (DNS-rebinding protection).
 * - Forwards /api/v1 to the backend with a derived web key; the raw local key
 *   never leaves this server and is never forwarded.
 * - Rejects cross-site and cross-origin state-changing API requests.
 * - Turns one-time launch links into an HttpOnly, SameSite=Strict session cookie.
 * - Shows the locked screen to visitors without a valid session.
 *
 * The backend independently enforces every check that matters; if this file
 * is bypassed, requests reach the API without credentials and are refused.
 */

const API = process.env.MITRA_API_URL || "http://127.0.0.1:8000";
const COOKIE = "mitra_session";
const KEY_FORMAT = /^[A-Za-z0-9_-]{43,128}$/;
const CODE_FORMAT = /^[A-Za-z0-9_-]{20,100}$/;
const LOOPBACK = new Set(["127.0.0.1", "localhost", "[::1]"]);
const PUBLIC_FILES = new Set([
  "/icon.svg",
  "/favicon.ico",
  "/mitra-waves.svg",
  "/locked",
]);
const CONTROL_ROUTES = new Set(["/api/v1/auth/launch", "/api/v1/auth/redeem"]);

function secretDir(): string {
  if (process.env.MITRA_SECRET_DIR) return process.env.MITRA_SECRET_DIR;
  if (process.platform === "win32")
    return path.join(
      process.env.LOCALAPPDATA || path.join(os.homedir(), "AppData", "Local"),
      "MITRA",
    );
  return path.join(
    process.env.XDG_STATE_HOME || path.join(os.homedir(), ".local", "state"),
    "mitra",
  );
}

function readKey(): string | null {
  try {
    const value = readFileSync(
      path.join(secretDir(), "local-api.key"),
      "ascii",
    ).trim();
    return KEY_FORMAT.test(value) ? value : null;
  } catch {
    return null;
  }
}

function webKey(key: string): string {
  return createHmac("sha256", key).update("mitra-web-v1").digest("hex");
}

function loopbackHost(host: string | null): boolean {
  if (!host || /[@/\\?#]/.test(host)) return false;
  try {
    return LOOPBACK.has(new URL(`http://${host}`).hostname);
  } catch {
    return false;
  }
}

function deny(status: number, detail: string) {
  return NextResponse.json(
    { detail },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

function crossSite(request: NextRequest): boolean {
  const site = request.headers.get("sec-fetch-site");
  return site !== null && site !== "same-origin" && site !== "none";
}

function sameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return false;
  try {
    const parsed = new URL(origin);
    return (
      parsed.protocol === "http:" &&
      parsed.host === request.headers.get("host")
    );
  } catch {
    return false;
  }
}

function locked(request: NextRequest, reason?: string, clear = false) {
  const target = new URL("/locked", request.url);
  if (reason) target.searchParams.set("reason", reason);
  const response = NextResponse.rewrite(target);
  if (clear) response.cookies.delete(COOKIE);
  response.headers.set("Cache-Control", "no-store");
  return response;
}

function forward(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (CONTROL_ROUTES.has(pathname.replace(/\/+$/, "")))
    return deny(404, "Not found");
  if (crossSite(request)) return deny(403, "Cross-site requests are refused");
  if (!["GET", "HEAD"].includes(request.method) && !sameOrigin(request))
    return deny(403, "Origin not allowed");
  const key = readKey();
  if (!key)
    return deny(
      503,
      "MITRA's local key is not ready. Start the API, then reload.",
    );
  const headers = new Headers(request.headers);
  headers.delete("x-mitra-local-key");
  headers.set("x-mitra-web-key", webKey(key));
  return NextResponse.rewrite(new URL(pathname + search, API), {
    request: { headers },
  });
}

async function unlock(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code") ?? "";
  if (crossSite(request) || !CODE_FORMAT.test(code))
    return locked(request, "invalid");
  const key = readKey();
  if (!key) return locked(request, "offline");
  let grant: { token: string; expiresAt: string };
  try {
    const response = await fetch(new URL("/api/v1/auth/redeem", API), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-mitra-local-key": key,
      },
      body: JSON.stringify({ code }),
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return locked(request, "expired");
    grant = (await response.json()) as typeof grant;
  } catch {
    return locked(request, "offline");
  }
  const response = NextResponse.redirect(new URL("/", request.url), 303);
  response.cookies.set(COOKIE, grant.token, {
    httpOnly: true,
    sameSite: "strict",
    path: "/",
    expires: new Date(grant.expiresAt),
  });
  response.headers.set("Cache-Control", "no-store");
  return response;
}

async function gatePage(request: NextRequest) {
  const token = request.cookies.get(COOKIE)?.value;
  if (!token) return locked(request);
  const key = readKey();
  // Without a key the API has never started; the interface reports offline.
  if (!key) return NextResponse.next();
  try {
    const response = await fetch(new URL("/api/v1/auth/session", API), {
      headers: {
        "x-mitra-web-key": webKey(key),
        cookie: `${COOKIE}=${token}`,
      },
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(3000),
    });
    if (response.status === 401) return locked(request, "expired", true);
  } catch {
    // API offline: the shell holds no data and reports the disconnection itself.
  }
  return NextResponse.next();
}

export async function proxy(request: NextRequest) {
  if (!loopbackHost(request.headers.get("host")))
    return new NextResponse("MITRA only accepts loopback hosts", {
      status: 421,
    });
  const { pathname } = request.nextUrl;
  if (
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/__nextjs") ||
    PUBLIC_FILES.has(pathname)
  )
    return NextResponse.next();
  if (pathname.startsWith("/api/")) return forward(request);
  if (pathname === "/unlock") return unlock(request);
  return gatePage(request);
}
