from __future__ import annotations

import argparse
from pathlib import Path

from app.services.movies import (
    create_movie_from_tmdb,
    get_movie_by_tmdb_id,
)
from ingest.extract import ingest_movie as extract_and_store
from matcher.matcher import FingerprintDB


def ingest_real_movie(
    video_path: str,
    tmdb_id: int,
    interval_ms: int = 500,
) -> None:
    """
    Ingest a real movie into MUVY.

    1. Validate the video file.
    2. Find the movie in Supabase using its TMDB ID.
    3. Create the movie from TMDB if necessary.
    4. Extract perceptual fingerprints.
    5. Store fingerprints in Supabase.
    """

    path = Path(video_path)

    # ---------------------------------------------------------
    # Validate video
    # ---------------------------------------------------------

    if not path.exists():
        raise FileNotFoundError(
            f"Movie file not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Movie path is not a file: {path}"
        )

    print()
    print("=" * 60)
    print("MUVY MOVIE INGESTION")
    print("=" * 60)
    print()
    print(f"File: {path}")
    print(f"TMDB ID: {tmdb_id}")
    print()

    # ---------------------------------------------------------
    # Find existing movie
    # ---------------------------------------------------------

    movie = get_movie_by_tmdb_id(tmdb_id)

    if movie:
        print("Movie already exists in Supabase.")
    else:
        print("Movie not found in Supabase.")
        print("Fetching metadata from TMDB...")

        movie = create_movie_from_tmdb(
            movie_id=f"muvy-tmdb-{tmdb_id}",
            tmdb_id=tmdb_id,
        )

        print("Movie metadata stored successfully.")

    print()
    print(f"Movie ID: {movie['id']}")
    print(f"Title: {movie['title']}")
    print()

    # ---------------------------------------------------------
    # Extract and store fingerprints
    # ---------------------------------------------------------

    print("Extracting fingerprints...")
    print(
        f"Sampling interval: {interval_ms} ms"
    )
    print()

    db = FingerprintDB()

    count = extract_and_store(
        str(path),
        movie["id"],
        db,
        interval_ms=interval_ms,
    )

    # ---------------------------------------------------------
    # Complete
    # ---------------------------------------------------------

    print()
    print("=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print()
    print(f"Movie: {movie['title']}")
    print(f"Movie ID: {movie['id']}")
    print(f"TMDB ID: {movie['tmdb_id']}")
    print(f"Fingerprints stored: {count}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Ingest a movie into MUVY."
    )

    parser.add_argument(
        "video",
        help="Path to the movie video file.",
    )

    parser.add_argument(
        "--tmdb-id",
        type=int,
        required=True,
        help="TMDB movie ID.",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=500,
        help=(
            "Fingerprint sampling interval "
            "in milliseconds."
        ),
    )

    args = parser.parse_args()

    ingest_real_movie(
        video_path=args.video,
        tmdb_id=args.tmdb_id,
        interval_ms=args.interval,
    )


if __name__ == "__main__":
    main()