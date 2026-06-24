# AI Career Helper - Full Local Demo App

AI Career Helper is a FastAPI backend plus a Vite/React frontend demo. The
backend implements the full API contract from
[`design-docs/api-design.md`](design-docs/api-design.md) (11 modules) against the
page use cases in [`design-docs/use-cases.md`](design-docs/use-cases.md).

The **interface contracts are real** (paths, methods, status codes, schemas,
validation rules, and error codes all follow the design docs), while the
**business logic is mocked** (local SQLite store, mock AI, mock matching). This
lets the frontend integrate immediately; later you replace the `services/` layer
with real implementations without changing the routers or frontend API client.

The frontend lives in [`frontend/`](frontend/) and is wired to the backend `/v1`
API. In production-style local runs, FastAPI serves the built Vite app from
`frontend/dist`, so the app can run as a single service.

The AI capabilities (CV extraction, conversational onboarding, tailored CV,
interview coaching with voice) can be switched from mock to **real large-model
calls** with a single flag - see [Real AI integration](#real-ai-integration).

## Quick start

Start the full local app with one command:

```powershell
.\scripts\start.ps1
```

The script runs inside the `career-helper-app` conda environment, syncs Python
and Node dependencies when the requirements or lockfile change, builds the
frontend when `frontend/dist` is missing, and then starts FastAPI.

- Full app: http://127.0.0.1:8000/
- Interactive docs (Swagger): http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json
- Health check: http://127.0.0.1:8000/health
- API base path: `/v1` (e.g. `POST /v1/auth/register`)

Development mode, with FastAPI and Vite running separately:

```powershell
.\scripts\dev.ps1
```

- Backend URL: http://127.0.0.1:8000
- Frontend dev URL: http://127.0.0.1:5173
- For frontend dev, copy `frontend/.env.example` to `frontend/.env.local` if you
  need to override the API URL. The default production build uses same-origin
  `/v1`.

Stop local app processes on the default ports:

```powershell
.\scripts\stop.ps1
```

Run the verification suite:

```powershell
.\scripts\test.ps1
```

Manual backend-only commands:

```bash
set CAREER_ENABLE_REAL_AI=false
conda run -n career-helper-app python -m pip install -r requirements-dev.txt
conda run -n career-helper-app python -m pytest tests/test_smoke.py
```

There is also a separate suite that exercises the **real** models - see
[Testing the real AI](#testing-the-real-ai).

## Design decisions (mock phase)

These are the defaults chosen for this mock backend. Each is intentionally easy
to swap for a real implementation later.

| Area | Decision |
| --- | --- |
| Storage | Local **normalized SQLite** store ([`app/services/store.py`](app/services/store.py)) at `CAREER_LOCAL_DATABASE_PATH` (`app/data/career_helper.sqlite3` by default). If the runtime DB is missing, it is copied from the committed initial DB at `app/data/career_helper_initial.sqlite3`. |
| Auth | **Real JWT** (access + refresh) with rotation and refresh-token revocation, via `PyJWT`; passwords hashed with `bcrypt`. |
| Async tasks | In mock mode CV extraction and interview-review analysis simulate progress by **advancing a stage on each poll** (`CAREER_ASYNC_PROCESSING_POLLS`). In real-AI mode they run in **FastAPI background tasks** and the poll just reports the live status. |
| Public catalogs | Goal catalog / jobs / alumni are stored in SQLite. `career_helper_initial.sqlite3` contains the seed catalog data for CI and fresh local setup; `career_helper.sqlite3` is ignored local runtime state. |
| matchScore / ranking | Simple **skill-overlap** rule ([`app/services/mock_match.py`](app/services/mock_match.py)). |
| Goal progress | `progress = 0.5 * normalized average confidence + 0.5 * average module step completion` ([`app/services/progress.py`](app/services/progress.py)). |
| File uploads | In mock mode CV and audio files are **validated (type/size) then discarded**. In real-AI mode CVs are parsed (PDF/DOCX/TXT) and audio is transcribed before being scored. |
| Notifications | Server-side event generation on milestones, partner pipeline advances, and meeting updates; de-duplicated by `dedupKey`. |
| Partner pipeline | Status advances automatically by elapsed time since `submittedAt`: 8h, 24h, 48h, 120h (use-case APP-05). |
| Mock interview | Up to **4 rounds** (`CAREER_MOCK_QUESTION_COUNT`). Mock mode returns fixed dimension scores; real mode generates questions from the profile/job and scores the transcript. Voice answers + TTS playback available in real mode. |
| Dev reset | `POST /__dev/reset` clears the current user's demo data (use-case SET-07). Toggle with `CAREER_ENABLE_DEV_RESET`. |
| Authoritative spec | `design-docs/` (the `docs/` copy is treated as a duplicate). |

### Notable spec choice

For repeated meeting requests to the same alumni, this backend follows
`api-design.md` 10 and returns `409 MEETING_ALREADY_PENDING` (rather than the
"replace existing" behavior described in use-case AD-06).

## Configuration

Settings load from environment variables (prefix `CAREER_`) or a local `.env`
file. See [`app/core/config.py`](app/core/config.py). Common ones:

| Variable | Default | Meaning |
| --- | --- | --- |
| `CAREER_JWT_SECRET` | `dev-secret-change-me-in-production-min-32-bytes` | JWT signing secret (use >= 32 bytes) |
| `CAREER_ACCESS_TOKEN_TTL_SECONDS` | `1800` | Access token lifetime |
| `CAREER_REFRESH_TOKEN_TTL_SECONDS` | `2592000` | Refresh token lifetime |
| `CAREER_LOCAL_DATABASE_PATH` | `app/data/career_helper.sqlite3` | Local SQLite database path |
| `CAREER_ASYNC_PROCESSING_POLLS` | `2` | Polls returning `processing` before `complete` |
| `CAREER_MOCK_QUESTION_COUNT` | `4` | Mock interview rounds |
| `CAREER_ENABLE_DEV_RESET` | `true` | Enable `POST /__dev/reset` |
| `CAREER_ENABLE_REAL_AI` | `false` | Master switch for real large-model calls (see below) |

## Real AI integration

When `CAREER_ENABLE_REAL_AI=true`, the AI features call real models through a
single switch point, [`app/services/ai_service.py`](app/services/ai_service.py).
When it is `false` (the default) everything falls back to the deterministic mock
in [`app/services/mock_ai.py`](app/services/mock_ai.py), so the demo and the test
suite run with **zero external dependencies or API keys**.

Setup:

```bash
pip install -r requirements-ai.txt       # includes the optional AI extras
cp .env.example .env                      # then fill in your keys
# set CAREER_ENABLE_REAL_AI=true and CAREER_LLM_API_KEY=...
```

The model layer lives in [`app/llm/`](app/llm):

| Capability | Module | Approach |
| --- | --- | --- |
| CV -> profile | `cv_extraction.py` | `parsing.py` (PDF/DOCX/TXT) -> structured-output extraction, run in a background task |
| Conversational onboarding | `onboarding.py` | **LangGraph** graph (`decide` -> `extract`): the model leads the chat, validates each answer, breaks big topics into small follow-ups, handles "I don't know"/multiple degrees, then emits a draft |
| Tailored CV | `tailored_cv.py` | structured-output generation (synchronous) |
| Interview coaching | `interview.py` | question generation + transcript scoring (5 fixed dimensions) |
| Voice (STT/TTS) | `voice.py` | pluggable `VoiceProvider`; `OpenAIVoiceProvider` ships (Whisper + OpenAI TTS) |

Models are chosen per purpose in [`app/llm/models.py`](app/llm/models.py) so cheap
tasks (extraction) and expensive ones (writing/scoring) can use different models
via `CAREER_LLM_CV_MODEL`, `CAREER_LLM_ONBOARDING_MODEL`,
`CAREER_LLM_TAILORED_CV_MODEL`, `CAREER_LLM_INTERVIEW_MODEL`.

### Interview coaching flows

- **Interview review**: `POST .../interview-reviews` stores the audio and starts a
  background job (transcribe -> score); `GET .../interview-reviews/{id}` reports
  `transcribing -> scoring -> complete`.
- **Mock interview**: questions are generated from the profile + job. Answers come
  in as text (`POST .../turns`) or **voice** (`POST .../turns/voice`, transcribed via
  STT). Coach questions can be played back on demand via
  `GET .../turns/{turn_id}/audio` (TTS, cached). Finishing the interview kicks off
  background scoring; poll `GET .../mock-interviews/{id}` until dimensions appear.

The voice endpoints return `SPEECH_NOT_SUPPORTED` when real AI is disabled.

### Testing the real AI

[`tests/test_llm/`](tests/test_llm) makes **real model calls** using the
credentials in `.env`. Every test is skipped automatically when
`CAREER_ENABLE_REAL_AI` is false, no key is set, or the AI extras are not
installed - so it never interferes with the mock smoke tests. Run with `-s` to
see the printed model output:

```bash
pytest tests/test_llm -s
```

| File | Covers |
| --- | --- |
| `test_01_connectivity.py` | model import + a live call proving the `.env` key works |
| `test_02_llm_functions.py` | each `app/llm/*` function on mock data; prints output, saves TTS audio |
| `test_03_api_routers.py` | the API routers end-to-end (tailored CV, CV extract, interview review, mock interview with text + voice + TTS); prints output, saves audio |
| `run_onboarding_chat.py` | interactive onboarding in your terminal (not a pytest test) |

Generated audio is written to `tests/test_llm/output/` (gitignored). The
onboarding script supports two modes:

```bash
python tests/test_llm/run_onboarding_chat.py          # drives app/llm/onboarding directly
python tests/test_llm/run_onboarding_chat.py api      # drives the real API router
```

## Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) defines three jobs:

- **test** (runs on every push / PR): installs `requirements-dev.txt`, runs
  `pip check`, and runs `pytest -q` on Python 3.11 / 3.12 / 3.13 with
  `CAREER_ENABLE_REAL_AI=false`, so only deterministic mock tests execute.
- **frontend**: installs the Vite app with `npm ci`, builds it, and runs
  `npm audit --audit-level=high`.
- **real-ai** (manual `workflow_dispatch` only): runs `tests/test_llm` against the
  real models using an `OPENAI_API_KEY` repository secret. It never runs
  automatically (the calls are billable) and is a no-op if the secret is unset.

To enable the optional real-AI job, add an `OPENAI_API_KEY` secret under the repo's
Settings -> Secrets and variables -> Actions, then trigger the workflow manually.

## Project structure

```
app/
  main.py                 # app instance, router mounting, exception handlers, CORS
  core/
    config.py             # settings
    security.py           # JWT + bcrypt + id/time helpers
    errors.py             # APIError + unified {"error": {...}} envelope (api-design 1.2 / 12)
    deps.py               # get_current_user (Bearer guard)
    pagination.py         # cursor pagination (api-design 1.4)
  schemas/                # Pydantic models (camelCase JSON via CamelModel)
  routers/                # one module per API section (§2-§11)
  llm/                    # real large-model integration (loaded only when CAREER_ENABLE_REAL_AI=true)
    models.py             # per-purpose ChatOpenAI factory
    voice.py              # pluggable STT/TTS (OpenAIVoiceProvider)
    parsing.py            # CV file -> text (pdf/docx/txt)
    prompts.py            # capability prompts
    io_schemas.py         # structured-output Pydantic models
    cv_extraction.py / onboarding.py / tailored_cv.py / interview.py
  services/
    ai_service.py         # single AI entry point; routes real vs mock by CAREER_ENABLE_REAL_AI
    store.py              # local SQLite repository + seeding
    mock_ai.py            # mock CV extract / tailored CV / interview analysis / mock interview
    mock_match.py         # matchScore + recommendation ordering
    progress.py           # goal progress formula
    goals_service.py      # tracking init + progress recompute + milestone notifications
    applications_service.py  # partner pipeline + summary + counts
    notifications_service.py # notification creation/dedup + milestone helper
  data/                   # mock seed catalogs (goal_catalog / jobs / alumni)
tests/
  test_smoke.py           # mock-mode smoke tests keyed to use-case IDs
  test_llm/               # real-AI tests (skipped unless CAREER_ENABLE_REAL_AI=true)
    test_01_connectivity.py / test_02_llm_functions.py / test_03_api_routers.py
    run_onboarding_chat.py  # interactive onboarding (direct or via API router)
    mock_data.py / conftest.py
```

## Module coverage

All 11 modules from the API design are implemented:

1. Auth (§2) - register / login / refresh / logout / me
2. Profile (§3) - get/put profile, async CV extraction
3. Goals (§4) - public catalog, user goals CRUD, reorder
4. Tracking (§5) - step/resource toggles, week focus, rerate dismiss, progress
5. Jobs + Saved Jobs (§6) - listing, detail (matchScore), save/unsave
6. Tailored CV (§7) - mock LLM CV generation
7. Applications (§8) - CRUD, summary, partner pipeline auto-advance
8. AI Coaching (§9) - summary, interview reviews (async), mock interviews (multi-turn)
9. Alumni + Meetings (§10) - directory, recommendations, meeting requests
10. Notifications (§11) - list (cursor paging), mark read, delete, dedup

## Replacing the mocks later

- AI: set `CAREER_ENABLE_REAL_AI=true` to route through `app/llm/` (real LLM / STT /
  TTS) instead of `services/mock_ai.py`. Swap in another provider by extending
  `app/llm/voice.py` / `app/llm/models.py`.
- `services/store.py` now persists to normalized local SQLite tables while
  preserving the original dict-like API used by routers. For production
  multi-process deployments, split that compatibility layer into explicit
  repository methods and move background tasks to a real queue like Celery/RQ.
- Keep `routers/` and `schemas/` mostly unchanged - they are the public contract.
