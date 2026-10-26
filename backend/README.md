# MUVY Backend

FastAPI service that identifies movies from short video clips using
perceptual-hash fingerprint matching, with metadata from TMDB and storage in
Supabase.

## Requirements

- Python **3.14.6** (pinned in `.python-version`)
- A Supabase project (for the `movies` and `fingerprints` tables)
- A TMDB API key (for metadata/localization and catalog search)

## Setup

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuration

Create a `backend/.env` file (it is git-ignored) with:

```
SUPABASE_URL=your-supabase-project-url
SUPABASE_KEY=your-supabase-service-role-key
TMDB_API_KEY=your-tmdb-api-key
```

Never commit `.env`. Only `.env.example` (names, no values) is tracked.

## Database

Apply the migrations in `migrations/` to your Supabase Postgres instance, in
order:

1. `migrations/001_create_movie_fingerprint_schema.sql`
   - Creates `movies`, `fingerprints`, and the `match_fingerprint_candidates`
     RPC used by the matcher.
2. `migrations/002_create_catalog_requests.sql`
   - Creates `catalog_requests` for user-submitted catalog suggestions.
3. `migrations/003_create_audio_fingerprints.sql`
   - Creates `audio_fingerprints` and the `match_audio_candidates` RPC used by
     audio recognition.
4. `migrations/004_stage_fingerprint_ingestion.sql`
   - Creates the ingestion run registry, guarded video/audio staging RPCs, and
     restricted finalization RPCs.

Both enable row-level security and grant access only to the `service_role`,
so the backend must connect with the service-role key.

For a new database, apply migrations 001–004 in order. Migration 004 is a
one-time migration; if an earlier version of migration 004 has already been
applied to a database, do not rerun or replace it there. Apply these lifecycle
changes through a new forward migration tailored to that database's current
schema.

## Running the server

Run from the `backend/` directory (this matters — see "Import roots" below):

```bash
cd backend
uvicorn api:app --reload
```

The app listens on `http://127.0.0.1:8000` by default.

- Interactive API docs: `http://127.0.0.1:8000/docs`
- Health check: `GET /health` → `{"status": "healthy"}`
- Root: `GET /` → name/status/version

### Import roots (important)

The backend modules use two import styles:

- Top-level modules: `api.py` imports `identify`, `tmdb`.
- Package modules: `matcher/matcher.py` imports `app.db.supabase`,
  `ingest/movie.py` imports `app.services.movies`.

Both resolve only when the working directory is `backend/` (so that `backend/`
is on `sys.path`). Starting the server from the repo root (for example
`uvicorn backend.api:app`) will fail with `ModuleNotFoundError`. There is
currently no packaging config (`pyproject.toml`) to make the service
location-independent.

## Tests

```bash
cd backend
pytest
```

Tests set `PYTEST_CURRENT_TEST` so `.env` is not loaded; unit tests mock
Supabase/TMDB.

### Opt-in Supabase ingestion integration checks

The real-RPC integration checks are in
`integration/supabase_ingestion_check.py`. The filename and directory keep them
out of ordinary pytest discovery. Run them only against a separate, disposable
Supabase project with migrations 001–004 already applied. These checks create
and delete synthetic movie rows and publish synthetic fingerprints; never
point them at a production or shared project. They do not apply migrations.

From the repository root in PowerShell, set the disposable project's ref and
URL, explicitly confirm that same ref, and enter its service-role key without
echoing it:

```powershell
$projectRef = "<20-character-disposable-project-ref>"
$env:MUVY_RUN_SUPABASE_INGESTION_INTEGRATION = "1"
$env:MUVY_DISPOSABLE_SUPABASE_PROJECT_REF = $projectRef
$env:MUVY_CONFIRM_DISPOSABLE_SUPABASE_PROJECT = $projectRef
$env:SUPABASE_URL = "https://$projectRef.supabase.co"
$secureKey = Read-Host "Disposable project's service-role key" -AsSecureString
$env:SUPABASE_KEY = [System.Net.NetworkCredential]::new("", $secureKey).Password
```

Then change into `backend/` (the project's Python imports require this working
directory) and run only the explicitly named integration module:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q integration\supabase_ingestion_check.py
```

The checks refuse to run unless the opt-in flag is set, the disposable project
ref is confirmed twice and matches the Supabase URL, and a service-role key is
provided. Each test uses a fresh `muvy-it-<UUID>` movie ID, verifies it does not
already exist, and deletes only that movie afterward. Foreign-key cascades
remove its test fingerprints, ingestion runs, and staging rows. If teardown
cannot reach Supabase, remove that exact synthetic movie row in the disposable
project before running the checks again. The service-role key is held only in
the current PowerShell process; clear it and the opt-in variables when done:

```powershell
Remove-Item Env:SUPABASE_KEY, Env:SUPABASE_URL,
  Env:MUVY_RUN_SUPABASE_INGESTION_INTEGRATION,
  Env:MUVY_DISPOSABLE_SUPABASE_PROJECT_REF,
  Env:MUVY_CONFIRM_DISPOSABLE_SUPABASE_PROJECT
```

These checks exercise live RPC calls and rows, but do not replace PostgreSQL
transaction/permission review. They do not verify concurrent publication or
recover a lost finalization response.

## Ingestion (build the fingerprint catalog)

Recognition only works for movies that have been ingested. To add one:

```bash
cd backend
python -m ingest.movie /path/to/movie.mp4 --tmdb-id <TMDB_ID> [--interval 500]
```

Recognition only works per modality: `ingest.movie` builds the **video**
fingerprints (used by Upload Clip, Screen, and Back Camera). To also enable
**audio** recognition for the same movie, ingest its audio track (PyAV reads
the audio directly from the file — no separate audio export needed):

```bash
python -m ingest.audio /path/to/movie.mp4 --tmdb-id <TMDB_ID>
```

Each command creates a unique database run in `staging`, uploads each batch
through a guarded RPC, marks the run `ready` only after extraction and every
staging request succeeds, then calls the modality-specific finalize RPC. The
database locks the run row for every lifecycle transition. A stage request
serializes with completion, and requests arriving after completion are
rejected. Finalization requires a ready run for the requested movie and
modality, replaces only that modality's active rows, removes its staging rows,
and marks the run `published` in one transaction. A UUID cannot be reused for a
second attempt.

Extraction, staging, completion, or finalization failures leave the previous
active fingerprints available. The CLI attempts to mark the run `failed`; if
the process stops abruptly, it can remain `staging` or `ready`. A movie metadata
row created before a failed first ingestion may remain without fingerprints;
metadata behavior is unchanged in this phase. Video and audio remain
independent: publishing one modality does not delete the other modality's
active fingerprints.

If the connection is lost while waiting for a finalize RPC response, the commit
result may be ambiguous: the transaction may have completed even though the CLI
did not receive its response. Inspect the run status and active fingerprint
count before retrying. `published` means publication committed; `ready` means it
has not been published and can be finalized again; `failed` cannot be resumed,
so start a new run.

Video and audio are still refreshed independently. Running `ingest.movie`
replaces only video fingerprints; running `ingest.audio` replaces only audio
fingerprints. Neither command removes the other modality's active rows.

### Inspecting and cleaning abandoned ingestion runs

The registry records each run's UUID, movie, modality, status, and lifecycle
timestamps. Inspect runs and their staged row counts in the Supabase SQL editor:

```sql
SELECT r.ingestion_id, r.movie_id, r.modality, r.status,
       r.created_at, r.updated_at, r.ready_at, r.published_at, r.failed_at,
       CASE WHEN r.modality = 'video' THEN
           (SELECT count(*) FROM public.fingerprint_ingestion_staging s
            WHERE s.ingestion_id = r.ingestion_id)
       ELSE
           (SELECT count(*) FROM public.audio_fingerprint_ingestion_staging s
            WHERE s.ingestion_id = r.ingestion_id)
       END AS staged_fingerprints
FROM public.fingerprint_ingestion_runs r
ORDER BY r.created_at;
```

Before cleanup, confirm the ingestion process has stopped and inspect the run
status. Delete only a confirmed abandoned `staging`, `ready`, or `failed` run
from the registry; its staging rows are removed by `ON DELETE CASCADE`. This
does not touch active fingerprints. Do not delete `published` runs as routine
cleanup; they provide the publication audit record. For example, substitute the
UUID only after confirming it is the intended abandoned run:

```sql
DELETE FROM public.fingerprint_ingestion_runs
WHERE ingestion_id = '<confirmed-abandoned-run-uuid>'
  AND status IN ('staging', 'ready', 'failed');
```

The service role can inspect runs and staging rows but cannot write staging rows
or change run state directly; ingestion writes and state transitions go through
the restricted RPCs. The RPCs use `SECURITY DEFINER` so the service role does
not need direct table-write privileges. Their search paths are fixed and
application objects are schema-qualified. The database behavior should still
be verified in a nonproduction Supabase project before production use.

The low-level `FingerprintDB.add()`/`add_many()` and
`AudioFingerprintDB.add_many()` helpers write directly to active tables and
bypass staged-ingestion guarantees. `backend/scripts/test_fingerprint_db.py`
uses this direct-write path for diagnostics; do not use it for catalog
ingestion.

## Notable follow-ups (known debt)

- **Duplicated clients:** `api.py` builds its own Supabase client and TMDB
  helpers, separate from `app/db/supabase.py` and `app/services/tmdb.py`.
  These should be consolidated into one module.
- **Import roots:** as described above, the service must run from `backend/`.
  A `pyproject.toml` (or consistent package-relative imports) would remove
  this constraint.

## Deploying to Render

The repo ships a Render Blueprint at `render.yaml` (repo root) that deploys
`backend/` as a native Python web service.

- `rootDir: backend` sets the working directory so the module imports resolve.
- `startCommand` runs `uvicorn api:app --host 0.0.0.0 --port $PORT`.
- `healthCheckPath: /health` drives Render's health checks.
- `aptPackages` install the system libraries `opencv-python` needs on Linux.

To deploy:

1. Push this repository to GitHub.
2. In the Render dashboard, choose **New → Blueprint**, then select the repo.
   Render reads `render.yaml` automatically.
3. After the service is created, set these environment variables in the
   dashboard (they are marked `sync: false`, so their values are not stored in
   the repo):
   - `SUPABASE_URL`
   - `SUPABASE_KEY`  (use the Supabase **service-role** key)
   - `TMDB_API_KEY`
   - `ALLOWED_ORIGINS` (optional; comma-separated extra frontend origins)
4. Deploy. Once live, your API is at `https://<service-name>.onrender.com`.

Then point the frontend at it by setting `DEPLOYED_API_BASE_URL` in
`api-config.js` (repo root) to that URL and pushing.

Notes:

- The GitHub Pages origin (`https://mudymuziks-tech.github.io`) is already in
  the backend's default CORS list, so no `ALLOWED_ORIGINS` value is needed for
  that host.
- OpenCV + numpy video decoding generally needs more than Render's free tier
  (512 MB). A Starter or Standard web service is recommended.
- Render must have Python 3.14 available (pinned in `.python-version`). If the
  build reports an unsupported version, adjust the runtime version or the
  pinned dependencies.
