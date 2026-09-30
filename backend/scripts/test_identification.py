from ingest.extract import clip_to_query_frames
from matcher.matcher import FingerprintDB, match_clip


def main():
    video = "tests/fixtures/test_movie.mp4"

    print("Extracting query frames...")
    query_frames = clip_to_query_frames(video)

    print(f"Query frames: {len(query_frames)}")

    db = FingerprintDB()

    rows = db.all_rows()

    print(f"Stored fingerprints: {len(rows)}")

    result = match_clip(
        query_frames,
        db,
        hash_distance_threshold=8,
        offset_bucket_ms=500,
        min_votes=3,
        min_margin=2.0,
    )

    print()
    print("Result:")

    if result is None:
        print("NO MATCH")
    else:
        print(result)


if __name__ == "__main__":
    main()