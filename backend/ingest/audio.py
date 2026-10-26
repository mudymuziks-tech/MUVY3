from __future__ import annotations

import argparse
import uuid
from pathlib import Path

from app.services.movies import create_movie_from_tmdb, get_movie_by_tmdb_id
from audio_fingerprint import AudioFingerprintDB, extract_audio_hashes


def ingest_movie_audio(video_path: str, tmdb_id: int) -> int:
    """Extract the audio track from a movie file and store audio fingerprints."""
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Movie file not found: {path}")

    movie = get_movie_by_tmdb_id(tmdb_id)
    if movie is None:
        movie = create_movie_from_tmdb(
            movie_id=f"muvy-tmdb-{tmdb_id}",
            tmdb_id=tmdb_id,
        )

    print(f"Extracting audio fingerprints for '{movie['title']}' ...")
    ingestion_id = str(uuid.uuid4())
    print(f"Audio fingerprint ingestion run: {ingestion_id}")
    db = AudioFingerprintDB()
    db.create_ingestion(ingestion_id, movie["id"])

    try:
        hashes = extract_audio_hashes(str(path))
        if not hashes:
            raise RuntimeError(
                "No audio fingerprints were generated; active audio fingerprints were not changed."
            )

        batch = [
            {"hash": h.hash, "movie_id": movie["id"], "timestamp_ms": h.time_ms}
            for h in hashes
        ]
        db.stage_many(ingestion_id, batch)
        staged_count = db.complete_ingestion(ingestion_id, movie["id"])
        if staged_count != len(batch):
            raise RuntimeError(
                f"Audio run staged {staged_count} fingerprints but extracted {len(batch)}."
            )
        db.finalize_ingestion(ingestion_id, movie["id"])
    except Exception:
        try:
            db.fail_ingestion(ingestion_id, movie["id"])
        except Exception as failure_error:
            print(
                f"Could not mark audio ingestion run {ingestion_id} failed: "
                f"{failure_error}"
            )
        raise

    print(f"Stored {len(hashes)} audio fingerprints for '{movie['title']}'.")
    return len(hashes)


def main():
    parser = argparse.ArgumentParser(description="Ingest a movie's audio track.")
    parser.add_argument("video", help="Path to the movie file (its audio track is used).")
    parser.add_argument("--tmdb-id", type=int, required=True)
    args = parser.parse_args()
    ingest_movie_audio(args.video, args.tmdb_id)


if __name__ == "__main__":
    main()
