# Implementation report — 9 November 2026

The approved frontend remains at `Frontend/`; its layout and CSS were retained. Stages A–D are implemented, with live-model acceptance explicitly outstanding.

## Main files created or replaced

| Area | Files |
| --- | --- |
| API/contracts | `apps/api/contracts.py`, `config.py`, `main.py`, `migrate.py`, `migrations/env.py`, `migrations/versions/0001_initial.py` |
| Generated types | `packages/contracts/api.d.ts`, `scripts/contracts.mjs` |
| Agent | `agent/state.py`, `context.py`, `orchestrator.py` |
| Providers/tools | `models/providers.py`, `tools/filesystem.py`, `registry.py`, `worker.py` |
| Persistence/policy/traces | `memory/store.py`, `security/policy.py`, `redaction.py`, `observability/export.py` |
| Frontend wiring | `Frontend/lib/types.ts`, `lib/api/client.ts`, `lib/api/events.ts`, minimal changes in `components/workspace.tsx` |
| Tests/evals | `Frontend/tests/*`, `tests/test_*.py`, `tests/fakes.py`, `tests/e2e_app.py`, `tests/e2e/*`, `evals/tasks.json`, `evals/run.py` |
| Configuration/docs | `.github/workflows/ci.yml`, `.env.example`, updated `pyproject.toml`, npm manifests, dependency lock, README, architecture/API docs |

The old `backend/` moved to `apps/api`. Docker configuration, the fixed planner, production mock client, and obsolete artifact smoke test were removed. Original project databases were preserved. The blueprint and supplied slice specification were copied into the repository as references.

## Decisions

- SQLite uses SQLAlchemy and Alembic; new data lives in `.data/mitra-slice1.db`.
- Pydantic owns API schemas. TypeScript uses generated aliases, not duplicate domain interfaces.
- The agent chooses one action at a time, with an eight-iteration cap and one validation retry.
- Writes require a digest-bound, unexpired, server-stored approval checked again at dispatch. The consent view shows exact proposed content; tool observations and traces are redacted.
- File operations use a fixed child-process dispatcher for enforceable timeouts. There is no generic shell tool.
- Local llama-server and an explicitly selected compatible hosted endpoint share one adapter. Only the agent role runs. Thinking defaults off; requests are serialized and context is bounded.
- SSE uses named events, replay cursors, deduplication, and disabled compression to avoid proxy buffering. Approval UI waits for `approval.decided`.

## Executed checks

| Check | Actual result |
| --- | --- |
| `python -m pytest -q` | **128 passed**, no skips; one upstream Starlette/HTTPX deprecation warning |
| `python -m mypy` | Passed, strict mode across 25 Python source files |
| `python -m ruff check ...` | Passed |
| `npm test` | **7 passed**: approval states and SSE deduplication |
| `npm run test:e2e` | **1 passed** in Edge: no file before approval, exact content review, verified write, reload persistence, settings/mobile width, no page exceptions |
| `npm run lint`, `npm run typecheck`, `npm run build` | Passed |
| `npm run gen:types`, `npm run check:types` | Generated schema types are current |
| JSONL trace export | Executed against a real test database; test password absent and redaction marker present |

Additional commands run included dependency installation into `.venv`, npm installation of openapi-typescript/Playwright, formatting, and both fake/local eval entry points. CI configuration is supplied; no GitHub-hosted CI run is claimed.

## Evaluation results

Saved scripted result: `evals/results/fake-20261108T202235Z.json` (UTC filename).

| Metric | Result |
| --- | --- |
| Cases meeting expected outcome | **20/20** |
| Expected tool choice | **20/20** |
| Expected arguments | **20/20** |
| Valid JSON responses | **100%** |
| Schema-valid proposals | **81.6%** — fixtures deliberately include invalid tools/arguments and traversal attempts |
| Scripted injection scenarios meeting expectations | **5/5** |

These are deterministic infrastructure checks, not Qwen reasoning or adversarial robustness measurements. The local result is recorded as `not_run` in `evals/results/local-20261108T201449Z.json`: no model was configured and no listener was found on the default port 8080.

## Outstanding and intentionally absent

- **Live Qwen acceptance/evaluation is unverified.** Set `LLM_MODEL`, start the documented llama-server command, and run the local eval entry point. Hosted inference is also unverified.
- CPU latency and memory use with the real 9B model have not been measured.
- The filesystem sandbox assumes a user-controlled directory; it is not a hardened OS boundary against another hostile local process racing path changes.
- Interrupted writes cannot be rolled back with SQLite; restart/cancellation records require inspection rather than claiming no changes.
- Browser automation tools, desktop runtime, voice, semantic memory, workers, integrations, public authentication, and conversation deletion/editing are not implemented.

The main caveat to the specification is evidentiary: passing scripted injection cases cannot establish that a real model is safe. The implementation deliberately reports those separately rather than presenting a synthetic model score.
