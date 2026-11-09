# User-managed memory and opt-in voice

## Milestone 6: memory

Open **Memory** to add a key and a fact/preference. Choose all conversations or the current conversation, and whether the fact is confirmed. Drafts are visible and editable but never retrieved for model input. The source is explicitly `user`; MITRA does not automatically extract facts from conversations or infer permanent preferences.

Records live in SQLite through Alembic migration `0003_memory`. Editing preserves creation time and increments a revision. Stale edits are refused instead of overwriting someone else's newer edit. Duplicate keys in the same scope are refused; edit the existing record. A confirmed conversation-scoped record overrides a global record with the same key in that conversation.

At each agent decision, bounded lexical matching retrieves at most three confirmed records relevant to the current request. It excludes other conversations' private records and unrelated terms. Retrieved facts carry ID, key, source and update time in a quoted, explicitly untrusted context block. They cannot change tool permissions. This is lightweight keyword retrieval, not semantic/vector search; no embedding model or external database is used. Maximum storage is 200 records, 1,000 characters per fact; model excerpts are limited to 500 characters each.

Deletion prevents subsequent retrieval. It cannot retract an already-issued model request or remove facts copied into past conversation messages or private traces. An edited/deleted fact is not a retroactive history erasure. The deployment is single-user; global scope means all conversations in this local database, not cross-account isolation.

## Milestone 7: voice

Open the microphone control in the prompt or Voice controls in Settings. Recording requires an explicit click and the browser's microphone permission. Stop recording to request transcription. The transcript remains editable and must be reviewed; **Use reviewed transcript** only fills the main prompt. The normal **Send** action then creates a task through the existing conversation, tool policy and approval pipeline. Speech cannot bypass write or desktop approval.

The panel also reads the reviewed text aloud on request (up to 2,000 characters). Recording stops after thirty seconds or the two-MB payload limit. Cancellation or closing the panel stops microphone tracks and playback, aborts pending HTTP requests, and discards late results. There is no wake-word listening, background recording, automatic speech playback or automatic task submission. Browser support and microphone availability are checked; provider errors are surfaced instead of fabricating transcripts.

### Configuration, when you choose to use voice

Voice is disabled by default. In `.env`, configure explicitly:

```dotenv
MITRA_VOICE_ENABLED=true
LLM_STT_PROVIDER=local
LLM_STT_BASE_URL=http://127.0.0.1:8090/v1
LLM_STT_MODEL=your-transcription-model
LLM_STT_API_KEY=
LLM_TTS_PROVIDER=local
LLM_TTS_BASE_URL=http://127.0.0.1:8090/v1
LLM_TTS_MODEL=your-speech-model
LLM_TTS_API_KEY=
MITRA_TTS_VOICE=your-provider-voice
```

The addresses/model names are examples, not supplied servers. No model is started, installed, downloaded, unloaded or switched by MITRA. Both speech roles require their own explicit URL and model even though general role configuration supports fallback. Set `PROVIDER=hosted` explicitly and HTTPS when using a remote provider; audio/text will leave the computer only after the respective user action. Provider retention is outside MITRA's control.

The speech adapter contract is:

- `POST {STT_BASE_URL}/audio/transcriptions`: multipart `file` (WebM, Ogg, WAV or MP4) and `model`; JSON result with nonblank `text`.
- `POST {TTS_BASE_URL}/audio/speech`: JSON `model`, `input`, `voice`, `response_format: mp3`; MP3 bytes in response.
- Optional Bearer API keys stay in the backend. Redirects and environment proxies are disabled. Provider response size and request time are bounded; raw errors, audio and keys are not logged or persisted.

Speech and agent inference use the same single semaphore. Voice refuses a busy slot rather than accumulating work. HTTP cancellation releases the slot. This serializes requests; it does not manage the RAM consumed by independently launched servers. On this machine, run only the model/server you intend to use, or a provider that manages its own resource switching. There is no automatic second model startup.

The live microphone, acoustic accuracy, actual model speech quality and hosted-provider behavior remain user-run acceptance checks. Tests use synthetic recordings, mocked provider transports and browser media fixtures. Scripted checks are not a speech-quality benchmark.
