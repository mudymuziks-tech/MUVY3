from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Literal, Optional

import cv2
from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from supabase import create_client

from identify import identify_video
from discovery.pipeline import DiscoveryOutcome, discover_image, discover_video
from matcher.matcher import FingerprintDatabaseError
from tmdb import TMDBError, get_movie_details

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY must be set in the environment."
    )

MAX_UPLOAD_SIZE_BYTES = int(
    os.getenv("MAX_UPLOAD_SIZE_BYTES", str(100 * 1024 * 1024))
)
if MAX_UPLOAD_SIZE_BYTES <= 0:
    raise RuntimeError("MAX_UPLOAD_SIZE_BYTES must be a positive integer.")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "MUVY_ALLOWED_ORIGINS",
        "https://mudymuziks-tech.github.io",
    ).split(",")
    if origin.strip()
]

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
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept-Language", "Content-Type"],
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
    timestamp_seconds: Optional[float] = None
    confidence: Optional[float] = None
    margin: Optional[float] = None
    votes: Optional[int] = None
    frames: Optional[int] = None


class IdentifySuccessResponse(BaseModel):
    matched: bool
    status: Literal["verified"] = "verified"
    movie: MovieResponse
    match: MatchResponse


class IdentifyFailureResponse(BaseModel):
    matched: bool
    status: Literal["likely", "inconclusive"] = "inconclusive"
    message: str
    candidate_title: Optional[str] = None


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


def save_verified_discovery(outcome: DiscoveryOutcome) -> Optional[dict]:
    verification = outcome.verification
    if outcome.status != "verified" or verification is None:
        return None

    match = verification.tmdb_match
    movie_id = f"muvy-tmdb-{match.tmdb_id}"

    try:
        from app.services.movies import get_movie_by_tmdb_id, upsert_movie

        existing = get_movie_by_tmdb_id(match.tmdb_id)
        if existing:
            return existing

        tmdb_movie = match.tmdb_result
        title = tmdb_movie.get("title") or tmdb_movie.get("original_title")
        if not title:
            raise ValueError("Verified TMDB movie has no title.")

        return upsert_movie(
            movie_id=movie_id,
            tmdb_id=match.tmdb_id,
            title=title,
            release_date=tmdb_movie.get("release_date"),
            poster_path=tmdb_movie.get("poster_path"),
            backdrop_path=tmdb_movie.get("backdrop_path"),
            overview=tmdb_movie.get("overview"),
            runtime=tmdb_movie.get("runtime"),
        )
    except Exception as exc:
        logger.warning("Could not save verified discovery to Supabase: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="The verified movie could not be saved. Please try again.",
        ) from exc


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

    video_extensions = {
        ".mp4",
        ".mov",
        ".mkv",
        ".avi",
        ".webm",
        ".m4v",
    }
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    is_image = suffix in image_extensions

    if suffix not in video_extensions | image_extensions:
        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported media format. Supported video formats: "
                "mp4, mov, mkv, avi, webm, m4v; image formats: jpg, jpeg, png, webp."
            ),
        )

    temp_path = None
    total_bytes = 0

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

                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Uploaded video exceeds the configured size limit.",
                    )

                temp_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded video is empty.",
            )

        if is_image:
            image = await run_in_threadpool(cv2.imread, temp_path)
            if image is None:
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded image could not be decoded.",
                )
            result = None
        else:
            try:
                result = await run_in_threadpool(identify_video, temp_path)
            except FingerprintDatabaseError as exc:
                logger.warning("Fingerprint service is unavailable.")
                raise HTTPException(
                    status_code=503,
                    detail="Movie matching is temporarily unavailable. Please retry shortly.",
                ) from exc
            except (FileNotFoundError, cv2.error) as exc:
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded video could not be decoded.",
                ) from exc

        if result is None:
            discovery: DiscoveryOutcome = await run_in_threadpool(
                discover_image if is_image else discover_video,
                temp_path,
            )
            if discovery.status != "verified":
                verification = discovery.verification
                title = (
                    verification.tmdb_match.title
                    if verification is not None
                    else None
                )
                if discovery.status == "likely" and title:
                    message = (
                        f"MUVY found a likely match for {title}, but could not "
                        "visually verify it. Try a clearer clip."
                    )
                else:
                    message = "No confident match found. Try a clearer clip."
                return IdentifyFailureResponse(
                    matched=False,
                    status=discovery.status,
                    message=message,
                    candidate_title=title,
                )

            movie_data = await run_in_threadpool(
                save_verified_discovery,
                discovery,
            )
            if movie_data is None:
                raise HTTPException(
                    status_code=503,
                    detail="The verified movie could not be saved. Please try again.",
                )
            movie_data = await run_in_threadpool(
                localize_movie,
                movie_data,
                language,
            )
            return IdentifySuccessResponse(
                matched=True,
                status="verified",
                movie=movie_data,
                match=MatchResponse(
                    frames=discovery.verification.unique_frames,
                ),
            )

        movie_data = await run_in_threadpool(
            get_movie,
            result.movie_id,
        )

        if movie_data is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "The matcher identified a movie, "
                    "but its metadata was not found."
                ),
            )

        movie_data = await run_in_threadpool(
            localize_movie,
            movie_data,
            language,
        )

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

    except Exception:
        logger.exception("Video identification failed")
        raise HTTPException(
            status_code=500,
            detail="Video identification failed. Please try again.",
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