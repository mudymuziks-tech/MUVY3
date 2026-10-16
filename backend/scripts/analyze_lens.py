from __future__ import annotations

import json
import sys
from pathlib import Path

from discovery.ranker import (
    aggregate_candidates,
    rank_frame_results,
)


def main():
    if len(sys.argv) != 2:
        print(
            'Usage: python -m scripts.analyze_lens '
            '"RESULT_JSON"'
        )
        raise SystemExit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"File not found: {path}")
        raise SystemExit(1)

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    frame_results = []

    for frame, response in data.items():
        ranked = rank_frame_results(
            response,
            frame,
        )

        frame_results.append(ranked)

        print()
        print("=" * 70)
        print(f"FRAME {frame}")
        print("=" * 70)

        for result in ranked[:10]:
            print(
                f"{result.score:6.1f} | "
                f"{result.title}"
            )
            print(
                f"       source={result.source or 'unknown'}"
            )
            print(
                f"       {result.link}"
            )

    ranked_candidates = aggregate_candidates(
        frame_results
    )

    print()
    print("=" * 70)
    print("AGGREGATED CANDIDATES")
    print("=" * 70)

    for index, candidate in enumerate(
        ranked_candidates[:15],
        start=1,
    ):
        print()
        print(
            f"{index}. "
            f"{candidate['candidate']}"
        )
        print(
            f"   score={candidate['score']:.1f}"
        )
        print(
            f"   frames={candidate['frame_count']}"
        )

        for evidence in candidate["evidence"][:3]:
            print(
                f"   - [{evidence.frame}] "
                f"{evidence.title}"
            )
            print(
                f"     {evidence.source}"
            )


if __name__ == "__main__":
    main()
