from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import Client, create_client

if not os.environ.get("PYTEST_CURRENT_TEST"):
    load_dotenv()

from identify import identify_video
from tmdb import TMDBError, get_movie_details, search_movies
from audio_fingerprint import AudioFingerprintDB, extract_audio_hashes, match_audio_clip


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client | None = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
    )


def get_supabase_client() -> Client:
    if supabase is None:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY.",
        )
    return supabase


# ---------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------

app = FastAPI(
    title="Muvy API",
    description="Movie identification API powered by video fingerprint matching.",
    version="0.3.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

DEFAULT_ALLOWED_ORIGINS = [
    # Local development
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5500",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5500",

    # Production frontend (GitHub Pages)
    "https://mudymuziks-tech.github.io",
]

# Extra origins from the ALLOWED_ORIGINS env var (comma-separated), so a
# custom frontend domain can be added without editing code. Falls back to the
# defaults above when unset.
_extra_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=DEFAULT_ALLOWED_ORIGINS + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Response models
# ---------------------------------------------------------

class MovieResponse(BaseModel):
    id: str
    tmdb_id: Optional[int] = None
    title: Optional[str] = None
    release_date: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    overview: Optional[str] = None
    runtime: Optional[int] = None
    genres: Optional[list[dict]] = None
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    created_at: Optional[str] = None


class MatchResponse(BaseModel):
    timestamp_seconds: float
    confidence: float
    margin: float
    votes: int
    frames: int


class IdentifySuccessResponse(BaseModel):
    matched: bool
    movie: MovieResponse
    match: MatchResponse


class IdentifyFailureResponse(BaseModel):
    matched: bool
    message: str


class TMDBSearchResult(BaseModel):
    id: int
    title: str
    release_date: Optional[str] = None
    overview: Optional[str] = None
    poster_path: Optional[str] = None


class CatalogRequest(BaseModel):
    tmdb_id: int = Field(gt=0)


# ---------------------------------------------------------
# Basic routes
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "name": "Muvy API",
        "status": "running",
        "version": "0.3.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


# ---------------------------------------------------------
# Database helpers
# ---------------------------------------------------------

def get_movie(movie_id: str) -> Optional[dict]:
    client = get_supabase_client()

    try:
        response = (
            client
            .table("movies")
            .select("*")
            .eq("id", movie_id)
            .limit(1)
            .execute()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Movie database lookup failed: {exc}",
        )

    if not response.data:
        return None

    return response.data[0]


SUPPORTED_TMDB_LANGUAGES = {
    "en-US", "es-ES", "fr-FR", "de-DE", "pt-BR", "ar-SA",
    "zh-CN", "hi-IN", "ja-JP", "ko-KR", "it-IT", "sw-KE",
}


def localize_movie(movie_data: dict, language: str) -> dict:
    language = language if language in SUPPORTED_TMDB_LANGUAGES else "en-US"
    tmdb_id = movie_data.get("tmdb_id")
    if not tmdb_id:
        return movie_data

    try:
        localized_movie = get_movie_details(int(tmdb_id), language=language)
    except (TMDBError, TypeError, ValueError):
        return movie_data

    if not localized_movie:
        return movie_data

    localized_fields = (
        "title",
        "overview",
        "release_date",
        "poster_path",
        "backdrop_path",
        "runtime",
        "genres",
        "vote_average",
        "vote_count",
    )
    return {
        **movie_data,
        **{
            field: localized_movie.get(field) or movie_data.get(field)
            for field in localized_fields
        },
    }


# ---------------------------------------------------------
# Movie endpoint
# ---------------------------------------------------------

@app.get(
    "/movies/{movie_id}",
    response_model=MovieResponse,
)
def movie(
    movie_id: str,
    language: str = Header(default="en-US", alias="Accept-Language"),
):
    result = get_movie(movie_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Movie not found.",
        )

    return localize_movie(result, language)


@app.get(
    "/tmdb/search",
    response_model=list[TMDBSearchResult],
)
def search_tmdb_movies(
    q: str = Query(min_length=2, max_length=100),
    language: str = Header(default="en-US", alias="Accept-Language"),
):
    query = q.strip()
    if len(query) < 2:
        raise HTTPException(
            status_code=422,
            detail="Search query must contain at least two non-whitespace characters.",
        )

    language = language if language in SUPPORTED_TMDB_LANGUAGES else "en-US"

    try:
        return search_movies(query, language=language)
    except TMDBError as exc:
        raise HTTPException(
            status_code=502,
            detail="Movie search is temporarily unavailable.",
        ) from exc


@app.post("/catalog-requests")
def submit_catalog_request(request: CatalogRequest):
    # Resolve the client once so an unconfigured Supabase returns a clear
    # 503 instead of an AttributeError masked as a generic failure.
    client = get_supabase_client()

    try:
        existing_request = (
            client
            .table("catalog_requests")
            .select("title,status")
            .eq("tmdb_id", request.tmdb_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not check whether this movie was already suggested.",
        ) from exc

    if existing_request.data:
        existing = existing_request.data[0]
        return {
            "submitted": True,
            "already_submitted": True,
            "title": existing["title"],
            "message": f"{existing['title']} has already been suggested and is {existing['status']}.",
        }

    try:
        tmdb_movie = get_movie_details(request.tmdb_id)
    except TMDBError as exc:
        raise HTTPException(
            status_code=502,
            detail="The selected movie could not be verified with TMDB.",
        ) from exc

    if tmdb_movie is None:
        raise HTTPException(
            status_code=404,
            detail="The selected movie was not found on TMDB.",
        )

    title = tmdb_movie.get("title")
    if not title:
        raise HTTPException(
            status_code=502,
            detail="TMDB did not provide a title for the selected movie.",
        )

    try:
        response = (
            client
            .table("catalog_requests")
            .insert(
                {
                    "tmdb_id": request.tmdb_id,
                    "title": title,
                    "release_date": tmdb_movie.get("release_date") or None,
                }
            )
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="The catalog suggestion could not be saved. Please try again.",
        ) from exc

    if not response.data:
        raise HTTPException(
            status_code=503,
            detail="The catalog suggestion could not be saved. Please try again.",
        )

    return {
        "submitted": True,
        "already_submitted": False,
        "title": title,
        "message": "Suggestion submitted and is pending review. It will be recognizable by clip after it is added to MUVY's fingerprint catalog.",
    }


# ---------------------------------------------------------
# TMDB metadata refresh
# ---------------------------------------------------------

@app.post(
    "/movies/{movie_id}/refresh",
    response_model=MovieResponse,
)
def refresh_movie(movie_id: str):

    # First find the movie in our database.
    movie_data = get_movie(movie_id)

    if movie_data is None:
        raise HTTPException(
            status_code=404,
            detail="Movie not found.",
        )

    tmdb_id = movie_data.get("tmdb_id")

    if not tmdb_id:
        raise HTTPException(
            status_code=400,
            detail="Movie does not have a TMDB ID.",
        )

    # Fetch the latest metadata from TMDB.
    try:
        tmdb_movie = get_movie_details(
            int(tmdb_id)
        )

    except TMDBError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    if tmdb_movie is None:
        raise HTTPException(
            status_code=404,
            detail="Movie was not found on TMDB.",
        )

    # Only update columns that exist in our movies table.
    update_data = {
        "title": tmdb_movie.get("title"),
        "release_date": tmdb_movie.get("release_date") or None,
        "poster_path": tmdb_movie.get("poster_path"),
        "backdrop_path": tmdb_movie.get("backdrop_path"),
        "overview": tmdb_movie.get("overview"),
        "runtime": tmdb_movie.get("runtime"),
    }

    try:
        response = (
            get_supabase_client()
            .table("movies")
            .update(update_data)
            .eq("id", movie_id)
            .execute()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Movie update failed: {exc}",
        )

    if not response.data:
        raise HTTPException(
            status_code=404,
            detail="Movie could not be updated.",
        )

    return response.data[0]


# ---------------------------------------------------------
# Identification endpoint
# ---------------------------------------------------------

@app.post(
    "/identify",
    response_model=IdentifySuccessResponse | IdentifyFailureResponse,
)
async def identify(
    file: UploadFile = File(...),
    language: str = Header(default="en-US", alias="Accept-Language"),
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A video file is required.",
        )

    suffix = Path(
        file.filename
    ).suffix.lower()

    if not suffix:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file must have a file extension.",
        )

    allowed_extensions = {
        ".mp4",
        ".mov",
        ".mkv",
        ".avi",
        ".webm",
        ".m4v",
    }

    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported video format. "
                "Supported formats: mp4, mov, mkv, avi, webm, m4v."
            ),
        )

    # Fail fast when Supabase is not configured so the request returns a
    # clear 503 before any expensive video decoding or hashing begins.
    get_supabase_client()

    temp_path = None

    try:

        # Create a temporary file while preserving
        # the video extension.
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            temp_path = temp_file.name

            while True:
                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                temp_file.write(chunk)

        # Run the proven identification engine.
        # identify_video is synchronous and CPU-bound (OpenCV decode + DCT
        # hashing) plus blocking Supabase I/O, so run it in the threadpool to
        # keep the async event loop responsive for concurrent requests.
        result = await run_in_threadpool(
            identify_video,
            temp_path,
        )

        if result is None:
            return IdentifyFailureResponse(
                matched=False,
                message="No confident match found.",
            )

        movie_data = get_movie(
            result.movie_id
        )

        if movie_data is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "The matcher identified a movie, "
                    "but its metadata was not found."
                ),
            )

        movie_data = localize_movie(movie_data, language)

        return IdentifySuccessResponse(
            matched=True,
            movie=movie_data,
            match=MatchResponse(
                timestamp_seconds=(
                    result.offset_ms / 1000
                ),
                confidence=result.confidence,
                margin=result.margin,
                votes=result.votes,
                frames=result.total_frames,
            ),
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Video identification failed: {exc}",
        )

    finally:

        if temp_path:
            try:
                Path(temp_path).unlink(
                    missing_ok=True
                )
            except Exception:
                pass

        await file.close()


@app.post(
    "/identify-audio",
    response_model=IdentifySuccessResponse | IdentifyFailureResponse,
)
async def identify_audio(
    file: UploadFile = File(...),
    language: str = Header(default="en-US", alias="Accept-Language"),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="An audio file is required.",
        )

    content_type = (file.content_type or "").lower()
    if not content_type.startswith("audio/"):
        raise HTTPException(
            status_code=415,
            detail="An audio file is required.",
        )

    # Fail fast when Supabase is not configured.
    get_supabase_client()

    try:
        payload = await file.read()
        hashes = await run_in_threadpool(extract_audio_hashes, io.BytesIO(payload))

        if not hashes:
            return IdentifyFailureResponse(
                matched=False,
                message="No usable audio was captured. Try again with clearer sound.",
            )

        result = await run_in_threadpool(
            match_audio_clip,
            hashes,
            AudioFingerprintDB(),
        )

        if result is None:
            return IdentifyFailureResponse(
                matched=False,
                message="No confident audio match found.",
            )

        movie_data = get_movie(result["movie_id"])

        if movie_data is None:
            raise HTTPException(
                status_code=404,
                detail="The matcher identified a movie, but its metadata was not found.",
            )

        movie_data = localize_movie(movie_data, language)

        return IdentifySuccessResponse(
            matched=True,
            movie=movie_data,
            match=MatchResponse(
                timestamp_seconds=result["offset_ms"] / 1000,
                confidence=result["confidence"],
                margin=float(result["clusters"]),
                votes=result["votes"],
                frames=len(hashes),
            ),
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Audio identification failed: {exc}",
        )

    finally:
        await file.close()