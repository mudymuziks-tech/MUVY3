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


def _read_json(response: requests.Response) -> dict:
    try:
        data = response.json()
    except ValueError as exc:
        raise TMDBError("TMDB returned an invalid JSON response.") from exc

    if not isinstance(data, dict):
        raise TMDBError("TMDB returned an invalid JSON response.")

    return data


def get_movie_details(
    tmdb_id: int,
    language: str = "en-US",
    append_to_response: Optional[str] = None,
) -> Optional[dict]:
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

    params = {
        "api_key": TMDB_API_KEY,
        "language": language,
    }
    if append_to_response:
        params["append_to_response"] = append_to_response

    try:
        response = requests.get(
            url,
            params=params,
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

    return _read_json(response)


def search_movies(
    query: str,
    language: str = "en-US",
) -> list[dict]:
    """Search TMDB for movie titles."""

    if not TMDB_API_KEY:
        raise TMDBError("TMDB_API_KEY is not configured.")

    try:
        response = requests.get(
            f"{TMDB_BASE_URL}/search/movie",
            params={
                "api_key": TMDB_API_KEY,
                "query": query,
                "language": language,
                "include_adult": False,
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise TMDBError(f"TMDB request failed: {exc}") from exc

    if response.status_code != 200:
        raise TMDBError(
            f"TMDB returned HTTP {response.status_code}: {response.text}"
        )

    results = _read_json(response).get("results", [])
    if not isinstance(results, list):
        raise TMDBError("TMDB returned an invalid movie search response.")

    return results