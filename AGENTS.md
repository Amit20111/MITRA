<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## MITRA project conventions

- Leave model startup to the user. Do not launch/download models, run live inference/evaluations, or start background model services unless the user explicitly asks. Use deterministic fake providers for development checks; run checks sequentially to limit CPU load.
- Keep the approved frontend at `Frontend/`; do not redesign or relocate it unless requested.
- Pydantic contracts in `apps/api/contracts.py` own API schemas. Regenerate `packages/contracts/api.d.ts` with `npm run gen:types`; do not edit generated types.
- Use SQLite through SQLAlchemy/Alembic. Three workspace file tools, opt-in `inspect_page`, and separately enabled task-owned browser sessions are implemented. Every `browser_action` requires exact stored approval and a current snapshot. No generic shell tool or automatic approval bypass is permitted.
- Keep `PROJECT_PROGRESS.md` current after each phase: changes, actual checks, limitations, and next work. Browser forms, authentication, page scripts, uploads, and arbitrary evaluation are not implemented.
- The default provider is a configured OpenAI-compatible llama-server, not a fake. FakeProvider is test-only; report live-model verification separately.
- Read `docs/ARCHITECTURE.md` and `docs/SLICE1_SPEC.md` before changing orchestration or security behavior.
- Checks: `npm run check:types`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, `.venv\Scripts\python -m pytest -q`, `.venv\Scripts\python -m mypy`, and Ruff for Python changes.
- Browser integration tests use `npm run test:e2e` on ports 3007/8007, isolated from normal development servers. Run evals with `.venv\Scripts\python -m evals.run --provider fake`; do not describe scripted scores as real model quality.

- Milestone 5 runtime (`apps/runtime`) pairs under CurrentUser DPAPI, defaults to heartbeat only, and opts into exact-approved window inspection/capture/focus with `run --desktop`. Never add plaintext credentials, unrestricted input, or model startup. Read `docs/WINDOWS_RUNTIME.md` before changing this boundary. Native desktop tests must use synthetic owned windows, never personal applications. Include `apps/runtime` in Ruff checks.
- Memory is explicit user-authored data, with revisions/scope and bounded retrieval; never promote records to instructions or permissions. Voice requires explicit configuration and user recording/playback actions, shares the agent inference slot, and never automatically submits transcripts. Read `docs/MEMORY_AND_VOICE.md` before changes. No live microphone/provider/model tests unless requested.
- Milestone 8A local security boundary: every API route requires a loopback peer and Host. Browser routes need the proxy-derived web key plus a hashed session. Launch/redeem/OpenAPI need the raw per-user key and refuse proxy traffic. Read `docs/SECURITY_BOUNDARY.md` before touching `apps/api/security_guard.py`, `apps/api/auth_service.py`, `apps/api/local_key.py` or `Frontend/proxy.ts`. Never add unauthenticated routes, fallback rewrites, or a key in frontend code. Tests use `tests/client.py` (`ApiClient`) and an isolated `MITRA_SECRET_DIR`.
