from __future__ import annotations

import argparse

from ingest.extract import clip_to_query_frames
from matcher.matcher import FingerprintDB, match_clip


DEFAULT_INTERVAL_MS = 500


def identify_video(
    clip_path: str,
    interval_ms: int = DEFAULT_INTERVAL_MS,
):
    """
    Identify a movie from a video clip.

    This is the reusable identification function used by
    both the command-line interface and the API.

    Returns:
        MatchResult if a confident match is found.
        None otherwise.
    """

    # Extract query frames from the clip.
    query_frames = clip_to_query_frames(
        clip_path,
        interval_ms=interval_ms,
    )

    if not query_frames:
        return None

    # Supabase-backed fingerprint database.
    db = FingerprintDB()

    # Run the existing matcher.
    return match_clip(
        query_frames,
        db,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Identify a movie from a video clip."
    )

    parser.add_argument(
        "clip",
        help="Path to the video clip.",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_MS,
        help="Frame sampling interval in milliseconds.",
    )

    args = parser.parse_args()

    result = identify_video(
        args.clip,
        interval_ms=args.interval,
    )

    if result is None:
        print("No confident match found.")
        return

    print(f"Movie: {result.movie_id}")
    print(f"Timestamp: {result.offset_ms / 1000:.2f}s")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Margin: {result.margin:.2f}")
    print(f"Votes: {result.votes}")
    print(f"Frames: {result.total_frames}")


if __name__ == "__main__":
    main()