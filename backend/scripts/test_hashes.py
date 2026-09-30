from ingest.extract import clip_to_query_frames
from matcher.matcher import FingerprintDB, hamming_distance


def main():
    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: python -m scripts.test_hashes <clip>"
        )
        return

    clip_path = sys.argv[1]

    query_frames = clip_to_query_frames(
        clip_path
    )

    db = FingerprintDB()
    rows = db.all_rows()

    print(f"Query frames: {len(query_frames)}")
    print(f"Stored rows: {len(rows)}")
    print()

    for index, query in enumerate(query_frames):
        best_distance = None
        best_row = None

        for stored_hash, movie_id, timestamp_ms in rows:
            distance = hamming_distance(
                query.hash,
                stored_hash,
            )

            if (
                best_distance is None
                or distance < best_distance
            ):
                best_distance = distance
                best_row = (
                    stored_hash,
                    movie_id,
                    timestamp_ms,
                )

        print(
            f"Query frame {index + 1}:"
        )

        print(
            f"  Query timestamp: "
            f"{query.capture_time_ms} ms"
        )

        print(
            f"  Closest distance: "
            f"{best_distance}"
        )

        if best_row:
            print(
                f"  Movie: "
                f"{best_row[1]}"
            )

            print(
                f"  Stored timestamp: "
                f"{best_row[2]} ms"
            )

        print()


if __name__ == "__main__":
    main()