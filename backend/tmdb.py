from __future__ import annotations

import os
from typing import Optional

import requests
from dotenv import load_dotenv


load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")

TMDB_BASE_URL = "https://api.themoviedb.org/3"


class TMDBError(Exception):
    """Raised when a TMDB request fails."""


def get_movie_details(tmdb_id: int) -> Optional[dict]:
    """
    Fetch full movie details from TMDB using a movie ID.

    Returns:
        dict: TMDB movie data
        None: if the movie does not exist

    Raises:
        TMDBError: if TMDB cannot be reached or returns an error
    """

    if not TMDB_API_KEY:
        raise TMDBError("TMDB_API_KEY is not configured.")

    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"

    try:
        response = requests.get(
            url,
            params={
                "api_key": TMDB_API_KEY,
                "language": "en-US",
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise TMDBError(f"TMDB request failed: {exc}") from exc

    if response.status_code == 404:
        return None

    if response.status_code != 200:
        raise TMDBError(
            f"TMDB returned HTTP {response.status_code}: {response.text}"
        )

    return response.json()