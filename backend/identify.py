from __future__ import annotations

import argparse

from ingest.extract import clip_to_query_frames
from matcher.matcher import FingerprintDB, match_clip


DEFAULT_INTERVAL_MS = 500

# Temporary diagnostic version.
# This helps us confirm exactly which identification code
# Render is running.
IDENTIFIER_VERSION = "0.4.0-strict-matching"


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

    # ---------------------------------------------------------
    # Stage 1: Extract query frames
    # ---------------------------------------------------------

    query_frames = clip_to_query_frames(
        clip_path,
        interval_ms=interval_ms,
    )

    if not query_frames:
        print(
            "[IDENTIFY] No query frames extracted.",
            flush=True,
        )
        return None

    # ---------------------------------------------------------
    # Stage 2: Create fingerprint database interface
    # ---------------------------------------------------------

    db = FingerprintDB()

    # ---------------------------------------------------------
    # Diagnostic information
    # ---------------------------------------------------------

    print(
        f"[IDENTIFY] version={IDENTIFIER_VERSION} "
        f"frames={len(query_frames)} "
        f"interval_ms={interval_ms}",
        flush=True,
    )

    # ---------------------------------------------------------
    # Stage 3: Run matcher
    # ---------------------------------------------------------

    result = match_clip(
        query_frames,
        db,
    )

    # ---------------------------------------------------------
    # Diagnostic result
    # ---------------------------------------------------------

    print(
        f"[IDENTIFY] result={result}",
        flush=True,
    )

    if result is None:
        print(
            "[IDENTIFY] No confident match returned by matcher.",
            flush=True,
        )
    else:
        print(
            "[IDENTIFY] Match accepted: "
            f"movie_id={result.movie_id}, "
            f"confidence={result.confidence:.2f}, "
            f"margin={result.margin:.2f}, "
            f"votes={result.votes}, "
            f"frames={result.total_frames}, "
            f"offset_ms={result.offset_ms}",
            flush=True,
        )

    return result


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
    print(
        f"Timestamp: "
        f"{result.offset_ms / 1000:.2f}s"
    )
    print(
        f"Confidence: "
        f"{result.confidence:.2f}"
    )
    print(
        f"Margin: "
        f"{result.margin:.2f}"
    )
    print(
        f"Votes: "
        f"{result.votes}"
    )
    print(
        f"Frames: "
        f"{result.total_frames}"
    )


if __name__ == "__main__":
    main()