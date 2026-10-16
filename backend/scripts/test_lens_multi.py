from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from discovery.lens import discover_frame


TIMESTAMPS = [3000, 5000, 7000]


def collect_strings(obj, results):
    """Recursively collect useful Lens result fields."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = str(key).lower()

            if key_lower in {
                "title",
                "name",
                "source",
                "snippet",
                "text",
            }:
                if isinstance(value, str) and value.strip():
                    results.append((key_lower, value.strip()))

            if key_lower in {"link", "url"}:
                if isinstance(value, str) and value.startswith("http"):
                    results.append(("link", value))

            collect_strings(value, results)

    elif isinstance(obj, list):
        for item in obj:
            collect_strings(item, results)


def extract_candidates(response):
    raw = []
    collect_strings(response, raw)

    candidates = []

    for key, value in raw:
        if key in {"title", "name", "text", "snippet"}:
            cleaned = " ".join(value.split())

            if len(cleaned) >= 3:
                candidates.append(cleaned)

    return candidates


def main():
    if len(sys.argv) < 2:
        print(
            'Usage: python -m scripts.test_lens_multi '
            '"VIDEO_PATH"'
        )
        raise SystemExit(1)

    video_path = Path(sys.argv[1])

    if not video_path.exists():
        print(f"Video not found: {video_path}")
        raise SystemExit(1)

    all_candidates = Counter()
    raw_results = {}

    for timestamp in TIMESTAMPS:
        print()
        print("=" * 70)
        print(f"[LENS] Frame at {timestamp} ms")
        print("=" * 70)

        try:
            result = discover_frame(
                str(video_path),
                timestamp,
            )

            raw_results[str(timestamp)] = result

            candidates = extract_candidates(result)

            # Keep output readable.
            seen = set()
            displayed = 0

            for candidate in candidates:
                normalized = candidate.lower()

                if normalized in seen:
                    continue

                seen.add(normalized)
                all_candidates[candidate] += 1

                print(f"  - {candidate}")

                displayed += 1

                if displayed >= 15:
                    break

            if not candidates:
                print("  No obvious textual candidates found.")

        except Exception as exc:
            print(f"[LENS] ERROR: {exc}")

    print()
    print("=" * 70)
    print("CROSS-FRAME CANDIDATES")
    print("=" * 70)

    if not all_candidates:
        print("No candidates found.")
    else:
        for candidate, count in all_candidates.most_common(20):
            print(f"{count}x  {candidate}")

    output_dir = Path("tests/fixtures/lens_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = (
        output_dir
        / f"{video_path.stem}_multi.json"
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            raw_results,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print(f"[LENS] Raw results saved to:")
    print(output_file)


if __name__ == "__main__":
    main()