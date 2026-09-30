from __future__ import annotations

import os

import requests
from dotenv import load_dotenv


load_dotenv()


TMDB_API_KEY = os.getenv("TMDB_API_KEY")

TMDB_BASE_URL = "https://api.themoviedb.org/3"


def _require_api_key() -> str:
    if not TMDB_API_KEY:
        raise RuntimeError(
            "TMDB_API_KEY is not configured in .env"
        )

    return TMDB_API_KEY


def get_movie_details(tmdb_id: int) -> dict:
    """
    Fetch movie metadata from TMDB using its movie ID.
    """

    api_key = _require_api_key()

    response = requests.get(
        f"{TMDB_BASE_URL}/movie/{tmdb_id}",
        params={
            "api_key": api_key,
        },
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


def search_movies(query: str) -> list[dict]:
    """
    Search TMDB for movies matching a title.
    """

    api_key = _require_api_key()

    response = requests.get(
        f"{TMDB_BASE_URL}/search/movie",
        params={
            "api_key": api_key,
            "query": query,
            "language": "en-US",
            "include_adult": False,
        },
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    return data.get("results", [])