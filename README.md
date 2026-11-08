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

Video upload, screen recording, and back-camera video capture are supported identification inputs. Bookmarks are stored locally in the browser. Notifications, AI discovery, and personalized recommendations are not connected to backend services yet.

## MUVY discovery-first UI (November 2026)

The frontend now uses a discovery-first navigation model:

- `home.html` — cinematic Home with a MUVY product-advertisement hero, recommendation coverflow and Trending This Week.
- `recognize.html` — Discover/Recognize entry point. Existing recognition handlers and API upload flow are retained.
- `ai.html` — AI conversation interface prototype. The UI is present, but responses are illustrative until connected to a discovery service.
- `recommendations.html` and `trending.html` — focused listing views opened by their matching Home section's View all action.
- `notifications.html` — notification centre with an empty state until a notification source is connected.
- `movie-profile.html` — dedicated cinematic movie details, enriched through TMDB when the API is available.
- `watchlist.html` — Bookmarks collection, using the existing `muvy.savedMovies` browser storage key.
- `profile.html` — profile and account preferences entry point.

Shared presentation and interaction files:

- `muvy-app.css` — shared header, menu, floating navigation, home and cinematic card styling.
- `muvy-pages.css` — AI, Saved Movies and profile page styling.
- `muvy-listings.css` — shared Recommendations and Trending listing-page styling.
- `muvy-discover.css` — discovery page styling overrides.
- `muvy-app.js` — shared menu, recommendation coverflow interactions and local bookmark collection.
- `movie-profile.js` — movie metadata rendering and bookmark/share actions on the dedicated details page.
- `notifications.js` — notification-centre rendering interface and honest empty state.

The existing identification endpoints and Supabase schema are unchanged. The additive `/tmdb/movies/{tmdb_id}` endpoint returns TMDB detail data for movie profiles. AI discovery and personalized recommendations remain presentation-level placeholders and must not be treated as connected functionality yet. Existing backend recognition remains the current functional integration to validate after the frontend pass.
