from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client

from identify import identify_video
from tmdb import TMDBError, get_movie_details


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY must be set in the environment."
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Local development
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",

        # Production frontend
        "https://mudymuziks-tech.github.io",
    ],
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
    try:
        response = (
            supabase
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
            supabase
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
        result = identify_video(
            temp_path
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