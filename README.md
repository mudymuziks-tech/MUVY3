# MUVY

MUVY is a static web frontend with a FastAPI movie-identification service. The identification API accepts short video clips, samples frames, matches visual fingerprints stored in Supabase, and looks up movie metadata.

## Local development

1. Create `backend/.env` from `backend/.env.example` and set `SUPABASE_URL`, `SUPABASE_KEY`, and `TMDB_API_KEY`.
2. Start the API from `backend` with `python -m uvicorn api:app --host 127.0.0.1 --port 8000`.
3. Serve the repository root over HTTP, for example with `python -m http.server 5500`.
4. Open `http://127.0.0.1:5500/home.html`.

The frontend selects the local API automatically on `localhost` and `127.0.0.1`. Do not expose Supabase or TMDB credentials in frontend files.

## Deployment

GitHub Pages serves the static frontend, and the FastAPI service is hosted separately at `https://muvy3.onrender.com`. The frontend selects that Render URL for hosted pages and `http://127.0.0.1:8000` for local development. The Render service needs `SUPABASE_URL`, `SUPABASE_KEY`, and `TMDB_API_KEY`; `MUVY_ALLOWED_ORIGINS` should include `https://mudymuziks-tech.github.io`. Override `window.MUVY_API_BASE_URL` in `api-config.js` only when switching to a different API host.

Render may take a while to answer the first request after an idle period. Check `https://muvy3.onrender.com/health` to verify availability.

## Current release scope

Video upload, screen recording, and back-camera video capture are supported identification inputs. Audio matching, account-backed authentication, title search, and persistent watchlists are not connected to backend services yet.
