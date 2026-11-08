from __future__ import annotations

import json
import sys
from pathlib import Path

from discovery.candidates import extract_candidates


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage: python -m scripts.inspect_visual_evidence "
            '"LENS_JSON_PATH"'
        )
        raise SystemExit(1)

    json_path = Path(sys.argv[1])

    with json_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    frame_results = {}

    for key, value in payload.items():
        try:
            timestamp_ms = int(key)
        except (TypeError, ValueError):
            continue

        frame_results[timestamp_ms] = value

    candidates = extract_candidates(
        frame_results
    )

    print()
    print("=" * 70)
    print("VISUAL EVIDENCE INSPECTION")
    print("=" * 70)

    for candidate in candidates[:10]:

        print()
        print(
            f"{candidate.title} "
            f"({candidate.year})"
        )

        print(
            f"frames={candidate.frame_count} "
            f"sources={candidate.source_count} "
            f"links={candidate.distinct_link_count}"
        )

        for evidence in candidate.evidence:

            print()
            print(
                f"  [{evidence.frame_timestamp_ms}ms]"
            )

            print(
                f"  title: {evidence.title}"
            )

            print(
                f"  source: {evidence.source}"
            )

            print(
                f"  link: {evidence.link}"
            )

            print(
                f"  image: "
                f"{evidence.image_url or 'NONE'}"
            )

            print(
                f"  thumbnail: "
                f"{evidence.thumbnail_url or 'NONE'}"
            )


if __name__ == "__main__":
    main()