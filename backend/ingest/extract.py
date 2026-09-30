from __future__ import annotations

import argparse

import cv2
import numpy as np

from matcher.matcher import FingerprintDB, QueryFrame


FRAME_INTERVAL_MS = 500
FINGERPRINT_BATCH_SIZE = 500


def phash(frame_bgr: np.ndarray) -> int:
    """
    63-bit perceptual hash.

    grayscale -> 32x32 -> DCT -> 8x8 low-frequency block,
    drop the DC term -> compare coefficients against median.
    """
    gray = cv2.cvtColor(
        frame_bgr,
        cv2.COLOR_BGR2GRAY,
    )

    small = cv2.resize(
        gray,
        (32, 32),
        interpolation=cv2.INTER_AREA,
    )

    dct = cv2.dct(
        np.float32(small)
    )

    block = dct[:8, :8].flatten()[1:]

    bits = block > np.median(block)

    h = 0

    for bit in bits:
        h = (h << 1) | int(bit)

    return h


def _sample_frames(
    path: str,
    interval_ms: int,
):
    """
    Yield:

        (timestamp_ms, frame)

    roughly every interval_ms.
    """

    cap = cv2.VideoCapture(path)

    if not cap.isOpened():
        raise FileNotFoundError(
            f"Could not open video: {path}"
        )

    fps = cap.get(
        cv2.CAP_PROP_FPS
    ) or 25.0

    step = max(
        1,
        round(
            fps * interval_ms / 1000
        ),
    )

    idx = 0

    try:
        while True:

            if not cap.grab():
                break

            if idx % step == 0:

                ok, frame = cap.retrieve()

                if ok:
                    yield (
                        int(idx / fps * 1000),
                        frame,
                    )

            idx += 1

    finally:
        cap.release()


def clip_to_query_frames(
    path: str,
    interval_ms: int = FRAME_INTERVAL_MS,
) -> list[QueryFrame]:
    """
    Extract perceptual hashes from a query video clip.
    """

    return [
        QueryFrame(
            hash=phash(frame),
            capture_time_ms=timestamp_ms,
        )
        for timestamp_ms, frame
        in _sample_frames(
            path,
            interval_ms,
        )
    ]


def ensure_movie(
    movie_id: str,
) -> None:
    """
    Create a movie record if it does not already exist.

    This function is kept here for compatibility with
    the existing ingestion workflow.
    """

    from app.db.supabase import supabase

    response = (
        supabase
        .table("movies")
        .upsert(
            {
                "id": movie_id,
                "title": movie_id,
            },
            on_conflict="id",
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            f"Failed to create movie record: {movie_id}"
        )


def ingest_movie(
    path: str,
    movie_id: str,
    db: FingerprintDB,
    interval_ms: int = FRAME_INTERVAL_MS,
) -> int:
    """
    Extract fingerprints from a movie
    and store them in Supabase.
    """

    batch: list[dict] = []
    count = 0

    for timestamp_ms, frame in _sample_frames(
        path,
        interval_ms,
    ):

        batch.append(
            {
                "hash": phash(frame),
                "movie_id": movie_id,
                "timestamp_ms": timestamp_ms,
            }
        )

        count += 1

        if len(batch) >= FINGERPRINT_BATCH_SIZE:

            db.add_many(batch)

            batch.clear()

            print(
                f"Uploaded {count} fingerprints...",
                flush=True,
            )

    if batch:
        db.add_many(batch)

    print(
        f"Finished ingesting {count} fingerprints "
        f"for '{movie_id}'."
    )

    return count


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "video",
        help="Movie file to ingest",
    )

    parser.add_argument(
        "--id",
        required=True,
        help="Unique movie ID",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=FRAME_INTERVAL_MS,
        help="Fingerprint sampling interval in milliseconds",
    )

    args = parser.parse_args()

    db = FingerprintDB()

    ingest_movie(
        args.video,
        args.id,
        db,
        interval_ms=args.interval,
    )


if __name__ == "__main__":
    main()