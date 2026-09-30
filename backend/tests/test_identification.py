from __future__ import annotations

from pathlib import Path

from ingest.extract import clip_to_query_frames
from matcher.matcher import FingerprintDB, match_clip


TEST_CASES = [
    {
        "name": "Reckless",
        "path": Path(
            r"C:\Users\fhourtune\Videos\Recording 2026-09-29 090227.mp4"
        ),
        "movie_id": "muvy-tmdb-1449400",
        "expected_timestamp_seconds": 856.0,
        "timestamp_tolerance_seconds": 15.0,
    },
    {
        "name": "Interstellar",
        "path": Path(
            r"C:\Users\fhourtune\Videos\Recording 2026-09-29 094707.mp4"
        ),
        "movie_id": "muvy-tmdb-157336",
        "expected_timestamp_seconds": 1031.0,
        "timestamp_tolerance_seconds": 15.0,
    },
    {
        "name": "Michael",
        "path": Path(
            r"C:\Users\fhourtune\Videos\Recording 2026-09-29 094547.mp4"
        ),
        "movie_id": "muvy-tmdb-936075",
        "expected_timestamp_seconds": 644.5,
        "timestamp_tolerance_seconds": 15.0,
    },
    {
        "name": "Enola Holmes 3",
        "path": Path(
            r"C:\Users\fhourtune\Videos\Recording 2026-09-29 094421.mp4"
        ),
        "movie_id": "muvy-tmdb-1202033",
        "expected_timestamp_seconds": 654.5,
        "timestamp_tolerance_seconds": 15.0,
    },
]


def test_movie_identification_regression():
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

        print(f"Expected movie: {case['movie_id']}")
        print(f"Detected movie: {result.movie_id}")

        print(
            f"Expected timestamp: "
            f"{case['expected_timestamp_seconds']:.2f}s"
        )

        print(
            f"Detected timestamp: "
            f"{result.offset_ms / 1000:.2f}s"
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

        assert result.movie_id == case["movie_id"], (
            f"Wrong movie for {case['name']}: "
            f"{result.movie_id}"
        )

        timestamp_seconds = (
            result.offset_ms / 1000
        )

        difference = abs(
            timestamp_seconds
            - case["expected_timestamp_seconds"]
        )

        assert difference <= case[
            "timestamp_tolerance_seconds"
        ], (
            f"Timestamp for {case['name']} "
            f"is off by {difference:.2f}s"
        )