# MITRA

**A supervised personal AI agent that keeps you in control.** MITRA combines a conversational workspace with bounded file tools, explicit approvals, persistent user-managed memory, and optional browser, Windows desktop, and voice features.

The default provider is an explicitly configured OpenAI-compatible model endpoint. MITRA does not start or download models automatically, and it has no production fake-provider fallback.

## Frontend screenshots

<p align="center">
  <img src="docs/screenshots/mitra-desktop.png" alt="MITRA desktop workspace" width="720">
  <img src="docs/screenshots/mitra-mobile.png" alt="MITRA mobile workspace" width="220">
</p>

<p align="center"><em>Desktop and mobile workspace. Screenshots use the deterministic test API; they do not represent live model output.</em></p>

## Highlights

- Review and approve exact proposed file writes before they run.
- Keep file access inside the configured workspace; there is no generic shell tool.
- Opt in to trusted browser origins and separately approved link/text interactions.
- Pair the Windows runtime for heartbeat; explicitly enable exact-approved window inspection, capture, or focus.
- Manage explicit memory records and revisions; voice is opt-in and never submits a transcript automatically.

Browser interaction is disabled by default. Browser forms, authentication, uploads, page scripts, unrestricted desktop input, and scheduled workers are not implemented. See [browser setup and boundaries](docs/BROWSER_PHASE.md), [Windows runtime setup](docs/WINDOWS_RUNTIME.md), and [memory and voice](docs/MEMORY_AND_VOICE.md).

## Repository

```text
Frontend/             Next.js command interface with cyan accents and live task indicators
apps/api/             FastAPI, Pydantic contracts, configuration, Alembic migrations
apps/runtime/         Windows helper: encrypted pairing, opt-in observation/capture/focus
packages/contracts/   Generated TypeScript API types (do not edit)
agent/                State machine, bounded context, step-at-a-time orchestrator
models/               OpenAI-compatible streaming adapter for llama.cpp or hosted API
security/             Central approval policy and trace redaction
tools/                Fixed file-tool registry, path sandbox, subprocess dispatcher
memory/               SQLAlchemy SQLite storage
observability/        Structured logs and redacted JSONL trace export
tests/                API/policy/adapter tests and browser E2E
Frontend/tests/       Approval-state and event-de-duplication tests
evals/                20 scripted/live cases, runner, saved results
```

The API uses SQLite through SQLAlchemy/Alembic. Entity IDs are UUIDs; SSE uses a monotonically increasing event cursor for replay. Current work and checks are tracked in [PROJECT_PROGRESS.md](PROJECT_PROGRESS.md).

## Windows setup

Clone the repository and run commands from its root. Requires Python 3.11+, Node.js 20.9+, and, if using a local model, a separately installed llama.cpp build and model. No model is downloaded automatically.

```powershell
git clone https://github.com/Amit20111/MITRA.git
Set-Location MITRA
python -m venv .venv
.venv\Scripts\python -m pip install -c requirements.lock -e '.[dev]'
npm ci
Copy-Item .env.example .env
```

### 1. Start the local model (optional, user-controlled)

Model startup is deferred to you. Frontend development, API startup, and scripted tests do not require a running model. Skip this step to preview the interface without inference. Development tools must not launch or download a model automatically, and live evaluations should only run when you explicitly choose to run them.

In the directory containing `llama-server.exe`, use your actual GGUF path:

```powershell
.\llama-server.exe -m "C:\Models\Qwen3.5-9B-Q4_K_M.gguf" --alias mitra-local --host 127.0.0.1 --port 8080 -ngl 0 -c 4096 --parallel 1 --jinja
```

The path is an example, not an included model. Use a llama.cpp build that supports your model. Keep one local model running. The backend sends `chat_template_kwargs.enable_thinking=false` by default, serializes model calls, bounds context/tool output, and limits output to 1,024 tokens. CPU latency depends on your machine; a live Qwen run has not been verified here.

Set these in root `.env`:

```dotenv
LLM_BASE_URL=http://127.0.0.1:8080/v1
LLM_MODEL=mitra-local
LLM_API_KEY=
# Optional; defaults to the repository's workspace directory:
# MITRA_WORKSPACE=C:/path/to/your/workspace
```

The API can start without a model, but requests fail honestly with a configuration/connection error. It never switches providers automatically.

### 2. Start the API

```powershell
.venv\Scripts\python -m apps.api.migrate
.venv\Scripts\python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Startup also applies Alembic migrations. SQLite uses `.data/mitra-slice1.db`. Previous milestone databases (`mitra.db`, test databases) are preserved and not automatically imported. Run one API worker; this is a local, single-user service, not an authenticated public deployment.

### 3. Start the frontend

In another terminal:

```powershell
npm run dev
```

Open **http://127.0.0.1:3000**. API docs: **http://127.0.0.1:8000/docs**. Frontend requests proxy `/api/v1/*` to the API. A custom `MITRA_API_URL` belongs in the frontend shell or `Frontend/.env.local`, not root `.env`.

Try: `Read notes.txt in the workspace and summarize it.` Then ask to create a file. A write creates a pending approval containing the exact target/content. Approving permits execution; rejection never dispatches that write. Successful writes show `verified` after hash read-back. Earlier completed steps are not undone by cancelling a task.

## Optional Windows runtime

Settings can pair and revoke the separate Windows helper. See [runtime setup and boundaries](docs/WINDOWS_RUNTIME.md). Pairing alone supports heartbeat; `run --desktop` opts into exact-approved window inspection, capture and focus. No model is required, and nothing starts automatically.

## Memory and voice

The Memory screen saves explicit confirmed facts, supports editing/deletion, and retrieves bounded relevant records per task. The microphone control supports opt-in recording, transcript review and playback through explicitly configured speech providers. Voice is disabled by default and never starts a model. See [memory/voice setup and limits](docs/MEMORY_AND_VOICE.md).

## Provider roles and hosted comparison

`agent`, `summarizer`, `embedder`, `stt`, and `tts` accept `LLM_<ROLE>_PROVIDER`, `BASE_URL`, `MODEL`, and `API_KEY`. General roles inherit agent configuration, but speech additionally requires explicit STT/TTS URLs, model names and MITRA_VOICE_ENABLED=true. Summarizer/embedder remain configuration-only. Settings displays public configuration, never keys.

For a compatible hosted endpoint, explicitly set `LLM_AGENT_PROVIDER=hosted`, its HTTPS `LLM_AGENT_BASE_URL`, model, and key in root `.env`. Restart the API. Hosted operation and local inference have not been live-tested; HTTP adapter behavior is tested with mocked transport.

## Contracts and checks

```powershell
npm run gen:types              # Generate from app.openapi(), no server needed
npm run gen:types:live         # Generate from running API /openapi.json
npm run check:types            # Fails on stale generated types
npm run lint
npm run typecheck
npm test
npm run build
.venv\Scripts\python -m ruff check apps/api apps/runtime agent models tools memory security observability tests evals
.venv\Scripts\python -m mypy
.venv\Scripts\python -m pytest -q
npm run test:e2e
```

Browser tests use the installed Edge browser on Windows; on Linux run `npx playwright install chromium` first. They launch test-only servers on **3007/8007**, a separate `.next-e2e` build directory, and a temporary workspace. Your normal servers and files are not reused. No test provider can be selected through production environment configuration.

`.github/workflows/ci.yml` checks generated types, lint, types, backend tests, frontend tests, build, browser E2E, and scripted evals. `requirements.lock` pins the verified Python environment. Root npm commands continue to work.

## Evaluations and traces

```powershell
.venv\Scripts\python -m evals.run --provider fake
.venv\Scripts\python -m evals.run --provider local --timeout 300
.venv\Scripts\python -m observability.export --output .data/traces-export.jsonl
```

The exporter refuses to overwrite an existing file and re-applies redaction. Traces include model request messages, schemas, raw responses, normalized proposals, validation errors, approval state, latency, usage, outcome, and verification. Interrupted generations are recorded as incomplete. Exports can contain personal content even after credential redaction; keep them local unless you intend to share them.

The runner creates temporary workspaces and executes the real orchestration/API/tool stack. It auto-approves **only the exact write expected by the fixture**, and denies unexpected proposals. Saved results are in `evals/results/`. Scripted scores verify infrastructure, not real-model reasoning or injection resistance. Missing model configuration is recorded as `not_run`, not a passing score.

See [architecture and limitations](docs/ARCHITECTURE.md), [API/event contract](docs/API_CONTRACT.md), and [implementation report](docs/SLICE1_REPORT.md).


The responsive frontend uses a navy-and-cyan command workspace with live application state; it does not fabricate uptime, connection status, or latency. On small screens, task overview is available from the header.
