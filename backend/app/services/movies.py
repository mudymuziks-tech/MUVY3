from __future__ import annotations

from typing import Optional

from app.db.supabase import supabase
from app.services.tmdb import get_movie_details


def get_movie(movie_id: str) -> Optional[dict]:
    """
    Get a MUVY movie by its internal ID.
    """

    response = (
        supabase
        .table("movies")
        .select("*")
        .eq("id", movie_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def get_movie_by_tmdb_id(
    tmdb_id: int,
) -> Optional[dict]:
    """
    Get a MUVY movie using its TMDB ID.
    """

    response = (
        supabase
        .table("movies")
        .select("*")
        .eq("tmdb_id", tmdb_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def create_movie(
    movie_id: str,
    tmdb_id: int,
    title: str,
    release_date: str | None = None,
    poster_path: str | None = None,
    backdrop_path: str | None = None,
    overview: str | None = None,
    runtime: int | None = None,
) -> dict:
    """
    Create a movie record in Supabase.
    """

    payload = {
        "id": movie_id,
        "tmdb_id": tmdb_id,
        "title": title,
        "release_date": release_date,
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "overview": overview,
        "runtime": runtime,
    }

    response = (
        supabase
        .table("movies")
        .insert(payload)
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            f"Failed to create movie: {title}"
        )

    return response.data[0]


def upsert_movie(
    movie_id: str,
    tmdb_id: int,
    title: str,
    release_date: str | None = None,
    poster_path: str | None = None,
    backdrop_path: str | None = None,
    overview: str | None = None,
    runtime: int | None = None,
) -> dict:
    """
    Create or update a movie record.
    """

    payload = {
        "id": movie_id,
        "tmdb_id": tmdb_id,
        "title": title,
        "release_date": release_date,
        "poster_path": poster_path,
        "backdrop_path": backdrop_path,
        "overview": overview,
        "runtime": runtime,
    }

    response = (
        supabase
        .table("movies")
        .upsert(
            payload,
            on_conflict="id",
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            f"Failed to upsert movie: {title}"
        )

    return response.data[0]


def create_movie_from_tmdb(
    movie_id: str,
    tmdb_id: int,
) -> dict:
    """
    Fetch a movie from TMDB and create/update
    the corresponding MUVY movie record.
    """

    tmdb_movie = get_movie_details(tmdb_id)

    title = tmdb_movie.get("title")

    if not title:
        raise RuntimeError(
            f"TMDB movie {tmdb_id} has no title"
        )

    return upsert_movie(
        movie_id=movie_id,
        tmdb_id=tmdb_id,
        title=title,
        release_date=tmdb_movie.get(
            "release_date"
        ),
        poster_path=tmdb_movie.get(
            "poster_path"
        ),
        backdrop_path=tmdb_movie.get(
            "backdrop_path"
        ),
        overview=tmdb_movie.get(
            "overview"
        ),
        runtime=tmdb_movie.get(
            "runtime"
        ),
    )