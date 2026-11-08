from __future__ import annotations

import json
import sys
from pathlib import Path

from discovery.candidates import extract_candidates
from discovery.resolver import resolve_candidates
from discovery.visual_verifier import verify_candidates


def main() -> None:
    if len(sys.argv) != 3:
        print(
            'Usage: python -m scripts.test_visual_verifier '
            '"VIDEO_PATH" "LENS_JSON_PATH"'
        )
        raise SystemExit(1)

    video_path = Path(sys.argv[1])
    lens_json_path = Path(sys.argv[2])

    if not video_path.exists():
        print(f"Video not found: {video_path}")
        raise SystemExit(1)

    if not lens_json_path.exists():
        print(f"Lens JSON not found: {lens_json_path}")
        raise SystemExit(1)

    with lens_json_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        lens_results = json.load(file)

    candidates = extract_candidates(lens_results)

    print("=" * 70)
    print("VISUAL VERIFICATION")
    print("=" * 70)
    print(f"Candidates available: {len(candidates)}")

    # Keep the discovery experiment bounded.
    candidates_to_resolve = candidates[:20]

    tmdb_matches = resolve_candidates(
        candidates_to_resolve
    )

    print(f"TMDB candidates resolved: {len(tmdb_matches)}")

    if not tmdb_matches:
        print("\nNo TMDB candidates could be resolved.")
        return

    print("\n" + "=" * 70)
    print("TESTING VISUAL CANDIDATES")
    print("=" * 70)

    results = verify_candidates(
        str(video_path),
        tmdb_matches,
    )

    for index, result in enumerate(results, start=1):
        match = result.tmdb_match

        print()
        print(
            f"[{index}] "
            f"{match.title} "
            f"(TMDB {match.tmdb_id})"
        )

        print(
            f"    TMDB score: "
            f"{match.score:.2f}"
        )

        print(
            f"    Lens candidate: "
            f"{result.candidate.title}"
        )

        print(
            f"    Evidence score: "
            f"{result.evidence_score:.2f}"
        )

        print(
            f"    Title score: "
            f"{result.title_score:.2f}"
        )

        print(
            f"    Year score: "
            f"{result.year_score:.2f}"
        )

        print(
            f"    Visual score: "
            f"{result.visual_score:.2f}"
        )

        print(
            f"    Total score: "
            f"{result.score:.2f}"
        )

        print(
            f"    Unique frames: "
            f"{result.unique_frames}"
        )

        print(
            f"    Unique sources: "
            f"{result.unique_sources}"
        )

        print(
            f"    Unique links: "
            f"{result.unique_links}"
        )

        print(
            f"    Images checked: "
            f"{result.images_checked}"
        )

        print(
            f"    Visual matches: "
            f"{result.visual_matches}"
        )

        print(
            f"    VERIFIED: "
            f"{result.verified}"
        )

        print(
            f"    Reason: "
            f"{result.reason}"
        )

    print("\n" + "=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    verified = [
        result
        for result in results
        if result.verified
    ]

    if not verified:
        print("No candidate was confidently verified.")
        return

    best = verified[0]

    print(
        f"Movie: {best.tmdb_match.title}"
    )

    print(
        f"TMDB ID: {best.tmdb_match.tmdb_id}"
    )

    print(
        f"Total score: {best.score:.2f}"
    )

    print(
        f"Evidence score: {best.evidence_score:.2f}"
    )

    print(
        f"Visual score: {best.visual_score:.2f}"
    )

    print(
        f"Verified: {best.verified}"
    )


if __name__ == "__main__":
    main()
