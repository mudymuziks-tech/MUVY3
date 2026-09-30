from __future__ import annotations

import sys

from ingest.extract import clip_to_query_frames
from matcher.matcher import FingerprintDB


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print(
            'python -m scripts.test_candidates "path_to_clip.mp4"'
        )
        raise SystemExit(1)

    path = sys.argv[1]

    print("Extracting query frames...")

    query_frames = clip_to_query_frames(path)

    print(f"Query frames: {len(query_frames)}")

    db = FingerprintDB()

    query_hashes = [
        frame.hash
        for frame in query_frames
    ]

    print("Calling PostgreSQL candidate search...")

    rows = db.find_candidates(
        query_hashes,
        distance_threshold=14,
    )

    print(f"Candidate rows: {len(rows)}")

    if not rows:
        print("NO CANDIDATES FOUND")
        return

    movies = {}

    for stored_hash, movie_id, timestamp_ms in rows:
        movies.setdefault(movie_id, 0)
        movies[movie_id] += 1

    print()
    print("Candidates by movie:")
    print("=" * 50)

    for movie_id, count in sorted(
        movies.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        print(
            f"{movie_id}: {count}"
        )


if __name__ == "__main__":
    main()