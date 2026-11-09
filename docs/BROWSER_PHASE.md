# Browser phases: inspection and controlled interaction

`inspect_page({"url":"https://example.com/notes"})` is an optional tool in the existing bounded agent loop. It produces a page title, up to 16,000 text characters, up to 50 allowlisted links, final URL, truncation flag, and a verified observation. Verification confirms retrieval/inspection, not the truth of a page's claims.

## Enable later

Install Node dependencies with `npm ci`. Windows uses installed Microsoft Edge; other platforms use Playwright Chromium (`npx playwright install chromium`). No browser or model downloads happen automatically.

Set exact trusted origins in root `.env`, then restart the API:

```dotenv
MITRA_BROWSER_ORIGINS=https://example.com,https://docs.example.com
```

An empty value (the default) omits the tool from the model's schemas and rejects dispatch. Settings shows configured origins. “Configured” is not a claim that a browser is running or ready. The adapter starts on demand and closes after each inspection. Normal browsing through the agent requires the user to start their model; automated tests use scripted responses.

## Boundaries

- Each inspection has a fresh nonpersistent context with no imported login, cookies, permissions or history.
- Requests use GET only. Every redirect is checked against the exact origin allowlist; at most three redirects are followed. No wildcard or implicit subdomain access.
- The fixed adapter fetches at most 1 MB of HTML/plain text, then provides that document to an isolated browser. Page JavaScript, service workers, forms, frames, downloads, and all additional browser resource requests are blocked. Dynamic app content requiring scripts will not be available.
- The read-only adapter exposes no interaction. The separately enabled phase 4B tools below add approved link clicks and ordinary text entry; submission, uploads and generic evaluation stay blocked.
- Only one inspection executes at a time per API worker. HTTP fetch has a 25-second abort deadline; browser operations have bounded timeouts and dispatch has a 40-second limit. Cancellation terminates the owned process tree on Windows. Normal completion closes the context and browser.
- Output enters the existing redacted trace and untrusted-context pipeline. Page text cannot change registry, origin configuration, or file-write approval policy.
- This is a trusted-origin allowlist, not a hardened network sandbox. Operators must trust the origin, its DNS ownership, and its GET endpoints. Explicitly allowlisting a local origin grants access to that local service. Do not allowlist sensitive/admin endpoints; even GET requests can have server-side effects. No cookie jar or authentication is used.
- Browser child-process diagnostics are intentionally summarized on failure; secret-bearing URLs are not echoed in error messages. URLs/page content can still contain personal data in redacted traces, subject to the existing redactor limitations.

## Checks

`python -m pytest tests/test_browser.py -q` exercises real headless browser inspection against a local fixture, exact-origin enforcement, disabled-by-default behavior, redirect denial, size bounds, script/resource blocking, fresh-session cookies, and a full scripted-agent task with persisted traces. It does not assess live-model reasoning or injection resistance.

## Phase 4B: approved browser controls

Enable separately in root `.env`, alongside `MITRA_BROWSER_ORIGINS`:

```dotenv
MITRA_BROWSER_INTERACTION=true
```

This does not start a browser or model. Tools become available on the next API start:

| Tool | Behavior |
| --- | --- |
| `browser_open(url)` | Open one task-owned static page session; return sessionId, snapshotId and numbered controls. |
| `browser_snapshot(sessionId)` | Read the current session, issuing a fresh snapshot ID. |
| `browser_action(sessionId, snapshotId, elementId, action, value)` | After exact human approval, `click` a safe link or `fill` a text field. A click uses an empty value. |
| `browser_close(sessionId)` | Close the owned session and release the browser. |

Sessions are isolated between tasks, never use an existing profile, and are limited to one per API worker with a ten-minute absolute lifetime. Completion, failure, cancellation, rejection and API shutdown close the session. A process restart invalidates browser approvals and never restores a logged-in profile or replays actions. Expired sessions require a new task/session and new approval. Pausing does not extend the lifetime.

The approval card shows source page, target label (including destination for a link), action, exact fill value, element ref, session ID and snapshot ID. The server gates every interaction, including fills. The worker independently rechecks approval digest, expiry, task/step binding and page fingerprint. One accepted action consumes the old snapshot. The UI continues to wait for the authoritative approval event.

Only visible enabled text/search inputs, textareas and allowlisted links are enumerated. Password/secret-labelled fields, file inputs, forms, submit buttons, downloads and new-tab links are excluded. Page JavaScript and all browser-initiated network requests remain blocked. A clicked link's document is fetched by the fixed adapter under the same GET-only origin/redirect rules, then delivered into the isolated page. Entering a value never submits it. Some ordinary sites will not work with these restrictions; this is not general web automation.

Filled values exist in the task/session and exact consent view. Traces/context use the existing redactor; do not enter secrets or sensitive account data. No claim is made that pattern-based redaction recognizes every secret.

Tests cover real fill/navigation, denial, expiry, tampering, ownership, stale snapshots, worker-side rechecks, double-use prevention, terminal cleanup and restart invalidation. Tests use local fixtures and scripted providers only. The next roadmap phase is the paired Windows runtime; broader browser capabilities remain explicit future work.

Adapter lifecycle follows the [Playwright BrowserContext documentation](https://playwright.dev/docs/api/class-browsercontext) and [Browser close documentation](https://playwright.dev/docs/api/class-browser#browser-close).
