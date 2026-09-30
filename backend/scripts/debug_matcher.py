from collections import defaultdict

from ingest.extract import clip_to_query_frames
from matcher.matcher import FingerprintDB, hamming_distance


def main():
    video = "tests/fixtures/test_movie.mp4"

    query_frames = clip_to_query_frames(video)

    db = FingerprintDB()
    rows = db.all_rows()

    hash_distance_threshold = 8
    offset_bucket_ms = 500

    votes = defaultdict(int)

    for qf in query_frames:
        for stored_hash, movie_id, stored_ts in rows:
            distance = hamming_distance(qf.hash, stored_hash)

            if distance <= hash_distance_threshold:
                implied_offset = stored_ts - qf.capture_time_ms

                bucket = (
                    round(implied_offset / offset_bucket_ms)
                    * offset_bucket_ms
                )

                votes[(movie_id, bucket)] += 1

    print("\nRAW VOTES")
    print("=" * 40)

    for key, value in sorted(votes.items()):
        print(key, "=>", value)

    print("\nTOTAL BUCKETS:", len(votes))


if __name__ == "__main__":
    main()