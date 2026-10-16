from __future__ import annotations

import json
import sys
from pathlib import Path

from discovery.candidates import extract_candidates
from discovery.resolver import resolve_candidates


def main() -> None:

    if len(sys.argv) != 2:
        print(
            "Usage: python -m scripts.test_lens_resolver "
            '"PATH_TO_LENS_JSON"'
        )
        raise SystemExit(1)

    json_path = Path(
        sys.argv[1]
    )

    if not json_path.exists():
        print(
            f"File not found: {json_path}"
        )
        raise SystemExit(1)

    with json_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    # ---------------------------------------------------------
    # Extract frame results
    # ---------------------------------------------------------

    frame_results: dict[int, dict] = {}

    for key, value in data.items():

        try:
            timestamp_ms = int(key)

        except (TypeError, ValueError):
            continue

        if isinstance(value, dict):
            frame_results[
                timestamp_ms
            ] = value

    # ---------------------------------------------------------
    # Candidate extraction
    # ---------------------------------------------------------

    candidates = extract_candidates(
        frame_results
    )

    print()
    print("=" * 70)
    print("LENS → MOVIE CANDIDATE NORMALIZATION")
    print("=" * 70)

    print(
        f"Frames loaded: "
        f"{len(frame_results)}"
    )

    print(
        f"Movie candidates: "
        f"{len(candidates)}"
    )

    print()

    for index, candidate in enumerate(
        candidates[:40],
        start=1,
    ):

        print(
            f"{index:02d}. "
            f"{candidate.title}"
            + (
                f" ({candidate.year})"
                if candidate.year
                else ""
            )
        )

        print(
            f"    discovery_score="
            f"{candidate.discovery_score:.1f}"
            f" frames={candidate.frame_count}"
            f" sources={candidate.source_count}"
            f" links={candidate.distinct_link_count}"
            f" best_position={candidate.best_position}"
        )

        for evidence in candidate.evidence[:5]:

            print(
                f"    - "
                f"[{evidence.frame_timestamp_ms}ms] "
                f"{evidence.title}"
            )

        if len(candidate.evidence) > 5:
            print(
                f"    ... "
                f"{len(candidate.evidence) - 5} "
                f"more evidence items"
            )

        print()

    # ---------------------------------------------------------
    # TMDB resolution
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("TMDB RESOLUTION")
    print("=" * 70)

    print()

    matches = resolve_candidates(
    candidates[:20]
)

    if not matches:
        print(
            "No TMDB matches passed the confidence threshold."
        )
        return

    for index, match in enumerate(
        matches[:40],
        start=1,
    ):

        candidate = match.candidate

        print(
            f"{index:02d}. "
            f"{match.title}"
            f" (TMDB {match.tmdb_id})"
        )

        print(
            f"    score={match.score:.2f}"
            f" release={match.release_date}"
        )

        print(
            f"    Lens candidate="
            f"{candidate.title}"
        )

        print(
            f"    discovery_score="
            f"{candidate.discovery_score:.1f}"
            f" frames={candidate.frame_count}"
            f" sources={candidate.source_count}"
        )

        print()

    # ---------------------------------------------------------
    # Explicit Reckless diagnostic
    # ---------------------------------------------------------

    reckless_matches = [
        match
        for match in matches
        if "reckless" in (
            match.title.casefold()
        )
        or "reckless" in (
            match.candidate.title.casefold()
        )
    ]

    if reckless_matches:

        print()
        print("=" * 70)
        print("RECKLESS DIAGNOSTIC")
        print("=" * 70)

        for match in reckless_matches:

            print(
                f"TMDB: {match.title}"
            )

            print(
                f"TMDB ID: "
                f"{match.tmdb_id}"
            )

            print(
                f"Score: "
                f"{match.score:.2f}"
            )

            print(
                f"Candidate: "
                f"{match.candidate.title}"
            )

            print(
                f"Frames: "
                f"{match.candidate.frame_count}"
            )

            print(
                f"Sources: "
                f"{match.candidate.source_count}"
            )

            print()

            for evidence in (
                match.candidate.evidence
            ):

                print(
                    f"- "
                    f"[{evidence.frame_timestamp_ms}ms] "
                    f"{evidence.title}"
                )

    else:

        print()
        print(
            "RECKLESS was not resolved by TMDB."
        )


if __name__ == "__main__":
    main()