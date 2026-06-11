# AI Career Helper - Mock Backend (FastAPI)

A FastAPI backend that implements the full API contract from
[`design-docs/api-design.md`](design-docs/api-design.md) (11 modules) against the
page use cases in [`design-docs/use-cases.md`](design-docs/use-cases.md).

The **interface contracts are real** (paths, methods, status codes, schemas,
validation rules, and error codes all follow the design docs), while the
**business logic is mocked** (in-memory store, mock AI, mock matching). This lets
the frontend integrate immediately; later you replace the `services/` layer with
real implementations without changing the routers.

## Quick start

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- Interactive docs (Swagger): http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json
- Health check: http://127.0.0.1:8000/health
- API base path: `/v1` (e.g. `POST /v1/auth/register`)

Run tests:

```bash
pytest
```

## Design decisions (mock phase)

These are the defaults chosen for this mock backend. Each is intentionally easy
to swap for a real implementation later.

| Area | Decision |
| --- | --- |
| Storage | Process-wide **in-memory** store ([`app/services/store.py`](app/services/store.py)). Data resets on restart. |
| Auth | **Real JWT** (access + refresh) with rotation and refresh-token revocation, via `PyJWT`; passwords hashed with `bcrypt`. |
| Async tasks | CV extraction and interview-review analysis simulate progress by **advancing a stage on each poll** (first 2 polls `processing`, 3rd `complete`). Controlled by `CAREER_ASYNC_PROCESSING_POLLS`. |
| Public catalogs | Mock seed data for goal catalog / jobs / alumni in [`app/data/`](app/data). |
| matchScore / ranking | Simple **skill-overlap** rule ([`app/services/mock_match.py`](app/services/mock_match.py)). |
| Goal progress | `progress = 0.5 * normalized average confidence + 0.5 * average module step completion` ([`app/services/progress.py`](app/services/progress.py)). |
| File uploads | CV and audio files are **validated (type/size) then discarded** (not persisted). |
| Notifications | Server-side event generation on milestones, partner pipeline advances, and meeting updates; de-duplicated by `dedupKey`. |
| Partner pipeline | Status advances automatically by elapsed time since `submittedAt`: 8h, 24h, 48h, 120h (use-case APP-05). |
| Mock interview | Fixed **4 rounds** (`CAREER_MOCK_QUESTION_COUNT`); evaluation returns mock dimension scores. |
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
| `CAREER_ASYNC_PROCESSING_POLLS` | `2` | Polls returning `processing` before `complete` |
| `CAREER_MOCK_QUESTION_COUNT` | `4` | Mock interview rounds |
| `CAREER_ENABLE_DEV_RESET` | `true` | Enable `POST /__dev/reset` |

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
  services/
    store.py              # in-memory repository + seeding
    mock_ai.py            # CV extract / tailored CV / interview analysis / mock interview
    mock_match.py         # matchScore + recommendation ordering
    progress.py           # goal progress formula
    goals_service.py      # tracking init + progress recompute + milestone notifications
    applications_service.py  # partner pipeline + summary + counts
    notifications_service.py # notification creation/dedup + milestone helper
  data/                   # mock seed catalogs (goal_catalog / jobs / alumni)
tests/                    # pytest smoke tests keyed to use-case IDs
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

- Swap `services/mock_ai.py` with real LLM / STT / TTS calls.
- Swap `services/store.py` with a database-backed repository.
- Keep `routers/` and `schemas/` mostly unchanged - they are the public contract.
