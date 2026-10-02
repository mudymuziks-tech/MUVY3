from pathlib import Path

from ingest.extract import clip_to_query_frames
from matcher.matcher import FingerprintDB, match_clip


TEST_CASES = [
    {
        "name": "Reckless",
        "path": Path(
            r"C:\Users\fhourtune\Videos\Recording 2026-09-29 090227.mp4"
        ),
        "expected_movie_id": "muvy-tmdb-1449400",
        "expected_timestamp_seconds": 856.0,
    },
    {
        "name": "Interstellar",
        "path": Path(
            r"C:\Users\fhourtune\Videos\Recording 2026-09-29 094707.mp4"
        ),
        "expected_movie_id": "muvy-tmdb-157336",
        "expected_timestamp_seconds": 1031.0,
    },
    {
        "name": "Michael",
        "path": Path(
            r"C:\Users\fhourtune\Videos\Recording 2026-09-29 094547.mp4"
        ),
        "expected_movie_id": "muvy-tmdb-936075",
        "expected_timestamp_seconds": 644.5,
    },
    {
        "name": "Enola Holmes 3",
        "path": Path(
            r"C:\Users\fhourtune\Videos\Recording 2026-09-29 094421.mp4"
        ),
        "expected_movie_id": "muvy-tmdb-1202033",
        "expected_timestamp_seconds": 654.5,
    },
]


UNKNOWN_CLIP = Path(
    r"C:\Users\fhourtune\Videos\record test1.mp4"
)


TIMESTAMP_TOLERANCE_SECONDS = 15.0


def test_movie_identification_regression():
    """
    Regression test for all known movies.

    Every known movie must:
    - produce query frames
    - return a confident match
    - return the expected movie
    - identify a timestamp within the allowed tolerance
    """

    db = FingerprintDB()

    for case in TEST_CASES:

        print()
        print("=" * 60)
        print(f"TEST: {case['name']}")
        print("=" * 60)

        assert case["path"].exists(), (
            f"Test video not found: {case['path']}"
        )

        query_frames = clip_to_query_frames(
            str(case["path"])
        )

        assert query_frames, (
            f"No query frames extracted from {case['name']}"
        )

        result = match_clip(
            query_frames,
            db,
        )

        assert result is not None, (
            f"No confident match for {case['name']}"
        )

        print(
            f"Expected movie: {case['expected_movie_id']}"
        )
        print(
            f"Detected movie: {result.movie_id}"
        )

        assert result.movie_id == case["expected_movie_id"], (
            f"Wrong movie detected for {case['name']}: "
            f"expected {case['expected_movie_id']}, "
            f"got {result.movie_id}"
        )

        expected_timestamp = (
            case["expected_timestamp_seconds"]
        )

        detected_timestamp = (
            result.offset_ms / 1000
        )

        timestamp_difference = abs(
            detected_timestamp
            - expected_timestamp
        )

        print(
            f"Expected timestamp: "
            f"{expected_timestamp:.2f}s"
        )
        print(
            f"Detected timestamp: "
            f"{detected_timestamp:.2f}s"
        )
        print(
            f"Timestamp difference: "
            f"{timestamp_difference:.2f}s"
        )
        print(
            f"Confidence: {result.confidence:.2f}"
        )
        print(
            f"Margin: {result.margin:.2f}"
        )
        print(
            f"Votes: {result.votes}"
        )
        print(
            f"Frames: {result.total_frames}"
        )

        assert (
            timestamp_difference
            <= TIMESTAMP_TOLERANCE_SECONDS
        ), (
            f"Timestamp mismatch for {case['name']}: "
            f"expected around {expected_timestamp:.2f}s, "
            f"got {detected_timestamp:.2f}s"
        )


def test_unknown_movie_is_rejected():
    """
    Negative regression test.

    The clip is intentionally not one of the movies
    fingerprinted in the database.

    Muvy must NOT return an arbitrary movie match.
    """

    print()
    print("=" * 60)
    print("TEST: Unknown movie rejection")
    print("=" * 60)

    assert UNKNOWN_CLIP.exists(), (
        f"Unknown test video not found: {UNKNOWN_CLIP}"
    )

    query_frames = clip_to_query_frames(
        str(UNKNOWN_CLIP)
    )

    assert query_frames, (
        "No query frames extracted from unknown movie clip"
    )

    db = FingerprintDB()

    result = match_clip(
        query_frames,
        db,
    )

    print(
        f"Result: {result}"
    )

    assert result is None, (
        "Unknown movie was incorrectly matched to "
        f"{result.movie_id}"
    )