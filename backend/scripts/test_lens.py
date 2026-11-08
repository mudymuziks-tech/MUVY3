from __future__ import annotations

import json
import sys

from discovery.lens import discover_frame


def main() -> None:
    if len(sys.argv) != 3:
        print(
            "Usage: python scripts/test_lens.py "
            '"VIDEO_PATH" TIMESTAMP_MS'
        )
        raise SystemExit(1)

    video_path = sys.argv[1]
    timestamp_ms = int(sys.argv[2])

    print(
        f"[LENS] Extracting frame at "
        f"{timestamp_ms} ms..."
    )

    result = discover_frame(
        video_path,
        timestamp_ms,
    )

    print()
    print("[LENS] Raw response:")
    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()