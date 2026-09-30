from __future__ import annotations

import sys
from collections import defaultdict

from ingest.extract import clip_to_query_frames
from matcher.matcher import (
    FingerprintDB,
    hamming_distance,
)


def main():
    if len(sys.argv) != 2:
        print(
            'Usage: python -m scripts.test_match_debug "clip.mp4"'
        )
        raise SystemExit(1)

    path = sys.argv[1]

    query_frames = clip_to_query_frames(path)

    db = FingerprintDB()

    query_hashes = [
        frame.hash
        for frame in query_frames
    ]

    rows = db.find_candidates(
        query_hashes,
        distance_threshold=14,
    )

    print(f"Query frames: {len(query_frames)}")
    print(f"Candidate rows: {len(rows)}")

    votes = defaultdict(int)

    frame_support = defaultdict(set)

    threshold = 14
    bucket_size = 500

    for query_index, qf in enumerate(query_frames):

        for stored_hash, movie_id, stored_ts in rows:

            distance = hamming_distance(
                qf.hash,
                stored_hash,
            )

            if distance > threshold:
                continue

            implied_offset = (
                stored_ts - qf.capture_time_ms
            )

            bucket = (
                round(
                    implied_offset / bucket_size
                )
                * bucket_size
            )

            key = (
                movie_id,
                bucket,
            )

            votes[key] += 1

            frame_support[key].add(
                query_index
            )

    print()
    print("RAW TEMPORAL CLUSTERS")
    print("=" * 70)

    movie_best = {}

    for key, vote_count in votes.items():

        movie_id, bucket = key

        support = len(
            frame_support[key]
        )

        current = movie_best.get(movie_id)

        if (
            current is None
            or support > current[1]
        ):
            movie_best[movie_id] = (
                bucket,
                support,
                vote_count,
            )

    for movie_id, (
        bucket,
        support,
        vote_count,
    ) in sorted(
        movie_best.items(),
        key=lambda item: item[1][1],
        reverse=True,
    ):

        print(
            f"{movie_id}"
        )

        print(
            f"  Best bucket: {bucket} ms"
        )

        print(
            f"  Frame support: {support}"
        )

        print(
            f"  Raw votes: {vote_count}"
        )


if __name__ == "__main__":
    main()