# Windows runtime - milestone 5

The Windows helper supports explicit pairing, authenticated heartbeats, and opt-in desktop observation and window focus. Pairing alone grants heartbeat only. Desktop access requires `run --desktop` plus exact approval for each operation. No model is started or called; typing, clicks, shell execution and unrestricted filesystem access are not exposed.

## Optional setup

Start the local API and frontend as described in the root README, with one API worker. No model is needed. Open Settings and choose **Generate runtime pairing code**. From the repository root, run:

```powershell
.venv\Scripts\python -m apps.runtime pair
```

Paste the code into the hidden prompt. Then start the helper:

```powershell
.venv\Scripts\python -m apps.runtime run
```

The helper makes outbound requests to `http://127.0.0.1:8000`; it opens no listening port. Use `pair --api http://127.0.0.1:PORT` for another local port and `--name "My Windows PC"` for a display name. Remote origins, credentials in URLs, proxies and redirects are refused. There is no autostart service.

Use Ctrl+C to stop. `run --once` checks one heartbeat, explicitly disconnects, and exits. Settings distinguishes **Not paired**, **Paired / offline**, and **Connected**. Heartbeats run every five seconds; fifteen seconds without a heartbeat marks the runtime offline. Network failures use backoff up to thirty seconds. Restarting the API retains pairing but requires a fresh heartbeat before reporting connected.

Choose **Revoke runtime access** in Settings to invalidate access immediately. A running helper stops on its next rejected heartbeat. To replace a saved credential, first revoke its old pairing, generate a new code, then run:

```powershell
.venv\Scripts\python -m apps.runtime pair --replace
```

## Credentials and limits

- Pairing codes expire after 120 seconds, work once, and lock after five failed guesses. Generating a new code invalidates older codes. Only one active runtime may be paired.
- The runtime credential expires after thirty days; re-pairing is required. The API stores hashes of secrets, not recoverable tokens. Validation responses and audit events omit secrets.
- The helper encrypts the entire saved credential and API origin with Windows CurrentUser DPAPI at `%LOCALAPPDATA%\MITRA\runtime.dpapi`. There is no plaintext fallback. `--credential-file PATH` must precede `pair` or `run` if an alternate location is required.
- If saving fails after a successful claim, revoke the pairing in Settings before trying again. A consumed code cannot be recovered. Do not share pairing codes or credential files.
- Runtime lifecycle audit events are persisted; `GET /api/v1/runtime/audit` returns the latest thirty. Regular successful heartbeats do not create an event each time.

## Trust boundary

This remains a trusted local, single-user application. Runtime authentication is not web-account authentication. The local Settings control plane can issue/revoke pairing without a separate account login. Runtime routes validate loopback Host and request peer; native claim/heartbeat/disconnect reject browser Origin headers. These checks are not an OS sandbox or protection from hostile programs running under the same Windows user. DPAPI likewise does not isolate this helper from other programs running as that user. A heartbeat proves credential possession, not verified device identity or permission to control the desktop.

Do not expose the API through a public interface or untrusted reverse proxy. One API worker is required for truthful lease/restart tracking. Desktop operations use the narrow approval protocol described below. Further actions require a separate supported adapter and authorization design.

## Verification

Tests cover pairing expiry/replay/guess limits/concurrent claims, credential authentication and expiry, stale leases, restart behavior, revocation, Origin/Host/peer checks, encrypted storage and tamper rejection. A Windows-only integration test starts a fixture API and a separate helper process with synthetic credentials, verifies heartbeat/disconnect, then revokes it and checks that it exits. Browser E2E checks Settings against the real API with synthetic heartbeat requests; it does not claim desktop control.

DPAPI and helper-process tests require a normal Windows user profile and are skipped on other operating systems. No live model is needed for these checks.

Windows API reference: [CryptProtectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata) and [CryptUnprotectData](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata).


## Phases 5B and 5C: observation and controlled focus

After pairing, explicitly opt in:

```powershell
.venv\Scripts\python -m apps.runtime run --desktop
```

In Settings, choose **Inspect windows**, review the proposed operation, and approve or reject. The helper returns up to fifty visible, non-minimized windows with titles/process IDs and opaque target references. Titles may contain personal information; inspection itself requires consent. Choose a listed window to propose a client-area capture or focus operation, then approve that exact request. Targets last two minutes and cannot be supplied as arbitrary OS handles through the API.

The first controlled action is **focus selected window**. The helper calls the normal Windows foreground API and verifies the foreground window afterward. Windows can refuse activation; that is reported as failure, without bypassing OS restrictions. Typing, arbitrary clicks, window closing, application launching and elevated control are intentionally outside this milestone's bounded action set.

Captures use `PrintWindow` for the selected client area, not the full screen, with a fixed child process and three-second timeout. Maximum dimensions are 1920 x 1080 and maximum output nine MB. Some apps produce blank or protected content; a returned image is not a claim that every application rendered correctly. Only the latest capture is retained in API memory. It is served with no-store headers, never placed in SQLite/traces or sent to the model, and expires after two minutes. Clearing/stopping or losing the runtime connection removes it; an API cleanup task checks expiry every five seconds. The browser may still hold an already displayed image until its next status refresh. This is retention control, not guaranteed secure memory erasure.

Requests bind action and opaque target ID to an exact digest, the paired runtime, and an expiry. The helper rechecks digest, state, expiry, one-use job ID, and its own snapshot of handle, process ID, title, class and client dimensions. Changed or expired targets require fresh inspection and approval. No retry automatically repeats a desktop action. Network interruption, revocation, expiry, opting out or restart prevents subsequent dispatch; interrupted requests fail/cancel and are never restored from the database.

**Stop desktop & clear captures** cancels queued work and blocks new dispatch. **Enable new desktop requests** allows fresh requests; it does not resume or replay cancelled work. Ctrl+C stops the helper. Stop/revocation cannot undo a focus/capture already executed or eliminate the tiny race after the final authorization check; this is supervised local automation, not an atomic OS security boundary. Lifecycle audit events persist without screenshots or window titles.

Desktop operations currently run from Settings; they are not advertised as autonomous agent tools. Existing restricted file tools remain the only agent filesystem path. Keeping the desktop action surface narrow does not imply general computer autonomy.

Native tests use a synthetic owned window for actual inspection, image capture, foreground verification/refusal and stale-window rejection. Browser tests exercise approval/stop using synthetic helper messages, while pairing/process tests exercise the real standalone helper. No personal application is captured in tests.

Win32 references: [PrintWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-printwindow), [SetForegroundWindow](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow), [GetWindowThreadProcessId](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getwindowthreadprocessid).
