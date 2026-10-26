from __future__ import annotations

from collections import defaultdict
from unittest.mock import Mock

import pytest

import audio_fingerprint
from ingest import audio, extract
from matcher.matcher import FingerprintDB


class MemoryIngestionDB:
    """Small modality-aware fake for ingestion orchestration tests."""

    def __init__(self):
        self.active = {"video": defaultdict(list), "audio": defaultdict(list)}
        self.staged = {"video": defaultdict(list), "audio": defaultdict(list)}
        self.runs = {}
        self.fail_stage = False
        self.fail_finalize = False
        self.finalized = []

    def create(self, ingestion_id, movie_id, modality):
        if ingestion_id in self.runs:
            raise RuntimeError("run ID already exists")
        self.runs[ingestion_id] = {
            "movie_id": movie_id,
            "modality": modality,
            "status": "staging",
        }

    def stage(self, modality, ingestion_id, fingerprints):
        run = self.runs.get(ingestion_id)
        if (run is None or run["status"] != "staging"
                or run["modality"] != modality
                or any(row["movie_id"] != run["movie_id"] for row in fingerprints)):
            raise RuntimeError("run mismatch or not staging")
        if self.fail_stage:
            raise RuntimeError("stage failed")
        self.staged[modality][ingestion_id].extend(fingerprints)

    def complete(self, modality, ingestion_id, movie_id):
        run = self.runs.get(ingestion_id)
        if (run is None or run["status"] != "staging"
                or run["modality"] != modality or run["movie_id"] != movie_id):
            raise RuntimeError("run mismatch or invalid transition")
        rows = self.staged[modality].get(ingestion_id, [])
        if not rows:
            raise RuntimeError("empty run")
        run["status"] = "ready"
        return len(rows)

    def fail(self, modality, ingestion_id, movie_id):
        run = self.runs.get(ingestion_id)
        if (run is None or run["modality"] != modality
                or run["movie_id"] != movie_id
                or run["status"] not in ("staging", "ready")):
            raise RuntimeError("run cannot be failed")
        run["status"] = "failed"

    def finalize(self, modality, ingestion_id, movie_id):
        run = self.runs.get(ingestion_id)
        if (run is None or run["status"] != "ready"
                or run["modality"] != modality or run["movie_id"] != movie_id):
            raise RuntimeError("run mismatch or not ready")
        self.finalized.append((modality, ingestion_id, movie_id))
        rows = self.staged[modality].get(ingestion_id, [])
        if self.fail_finalize or not rows:
            raise RuntimeError("finalize failed")
        self.active[modality][movie_id] = list(rows)
        del self.staged[modality][ingestion_id]
        run["status"] = "published"
        return len(rows)


class FakeVideoDB:
    def __init__(self, store):
        self.store = store

    def create_ingestion(self, ingestion_id, movie_id):
        self.store.create(ingestion_id, movie_id, "video")

    def stage_many(self, ingestion_id, fingerprints):
        self.store.stage("video", ingestion_id, fingerprints)

    def complete_ingestion(self, ingestion_id, movie_id):
        return self.store.complete("video", ingestion_id, movie_id)

    def fail_ingestion(self, ingestion_id, movie_id):
        self.store.fail("video", ingestion_id, movie_id)

    def finalize_ingestion(self, ingestion_id, movie_id):
        return self.store.finalize("video", ingestion_id, movie_id)


class FakeAudioDB:
    def __init__(self, store):
        self.store = store

    def create_ingestion(self, ingestion_id, movie_id):
        self.store.create(ingestion_id, movie_id, "audio")

    def stage_many(self, ingestion_id, fingerprints):
        self.store.stage("audio", ingestion_id, fingerprints)

    def complete_ingestion(self, ingestion_id, movie_id):
        return self.store.complete("audio", ingestion_id, movie_id)

    def fail_ingestion(self, ingestion_id, movie_id):
        self.store.fail("audio", ingestion_id, movie_id)

    def finalize_ingestion(self, ingestion_id, movie_id):
        return self.store.finalize("audio", ingestion_id, movie_id)


def set_video_frames(monkeypatch, frames):
    def sample_frames(*_args, **_kwargs):
        yield from frames

    monkeypatch.setattr(extract, "_sample_frames", sample_frames)
    monkeypatch.setattr(extract, "phash", lambda frame: frame)


def test_video_reingestion_replaces_active_rows_and_preserves_audio(monkeypatch):
    store = MemoryIngestionDB()
    store.active["video"]["movie-1"] = [{"hash": 1}]
    store.active["audio"]["movie-1"] = [{"hash": 90}]
    db = FakeVideoDB(store)

    set_video_frames(monkeypatch, [(1000, 2), (1500, 3)])
    assert extract.ingest_movie("movie.mp4", "movie-1", db) == 2
    first_set = list(store.active["video"]["movie-1"])

    set_video_frames(monkeypatch, [(1000, 4)])
    assert extract.ingest_movie("movie.mp4", "movie-1", db) == 1

    assert first_set != store.active["video"]["movie-1"]
    assert store.active["video"]["movie-1"] == [
        {"hash": 4, "movie_id": "movie-1", "timestamp_ms": 1000}
    ]
    assert store.active["audio"]["movie-1"] == [{"hash": 90}]
    assert all(run["status"] == "published" for run in store.runs.values())


def test_video_empty_extraction_does_not_finalize(monkeypatch):
    store = MemoryIngestionDB()
    previous = [{"hash": 8}]
    store.active["video"]["movie-1"] = list(previous)
    set_video_frames(monkeypatch, [])

    with pytest.raises(RuntimeError, match="No video fingerprints"):
        extract.ingest_movie("movie.mp4", "movie-1", FakeVideoDB(store))

    assert store.active["video"]["movie-1"] == previous
    assert store.finalized == []


def test_video_extraction_failure_after_staging_keeps_active_set(monkeypatch):
    store = MemoryIngestionDB()
    previous = [{"hash": 8}]
    store.active["video"]["movie-1"] = list(previous)

    def failing_sample(*_args, **_kwargs):
        for index in range(extract.FINGERPRINT_BATCH_SIZE):
            yield index * 500, index
        raise RuntimeError("decode failed")

    monkeypatch.setattr(extract, "_sample_frames", failing_sample)
    monkeypatch.setattr(extract, "phash", lambda frame: frame)

    with pytest.raises(RuntimeError, match="decode failed"):
        extract.ingest_movie("movie.mp4", "movie-1", FakeVideoDB(store))

    assert store.active["video"]["movie-1"] == previous
    assert len(store.staged["video"]) == 1
    assert store.finalized == []
    assert next(iter(store.runs.values()))["status"] == "failed"


@pytest.mark.parametrize("failure", ["stage", "finalize"])
def test_video_write_failures_do_not_replace_active_set(monkeypatch, failure):
    store = MemoryIngestionDB()
    previous = [{"hash": 8}]
    store.active["video"]["movie-1"] = list(previous)
    setattr(store, "fail_" + failure, True)
    set_video_frames(monkeypatch, [(1000, 2)])

    with pytest.raises(RuntimeError, match="failed"):
        extract.ingest_movie("movie.mp4", "movie-1", FakeVideoDB(store))

    assert store.active["video"]["movie-1"] == previous


def run_audio_ingestion(monkeypatch, tmp_path, store, hashes):
    movie_file = tmp_path / "movie.mp4"
    movie_file.write_bytes(b"placeholder")
    monkeypatch.setattr(audio, "get_movie_by_tmdb_id", lambda _tmdb_id: {
        "id": "movie-1", "title": "Test movie", "tmdb_id": 123,
    })
    monkeypatch.setattr(audio, "create_movie_from_tmdb", Mock())
    monkeypatch.setattr(audio, "AudioFingerprintDB", lambda: FakeAudioDB(store))
    monkeypatch.setattr(audio, "extract_audio_hashes", lambda _path: hashes)
    return audio.ingest_movie_audio(str(movie_file), 123)


def test_audio_reingestion_replaces_active_rows_and_preserves_video(
    monkeypatch, tmp_path
):
    store = MemoryIngestionDB()
    store.active["audio"]["movie-1"] = [{"hash": 1}]
    store.active["video"]["movie-1"] = [{"hash": 90}]

    assert run_audio_ingestion(
        monkeypatch, tmp_path, store,
        [audio_fingerprint.AudioHash(hash=2, time_ms=1000)],
    ) == 1
    first_set = list(store.active["audio"]["movie-1"])

    assert run_audio_ingestion(
        monkeypatch, tmp_path, store,
        [audio_fingerprint.AudioHash(hash=3, time_ms=1500)],
    ) == 1

    assert first_set != store.active["audio"]["movie-1"]
    assert store.active["audio"]["movie-1"] == [
        {"hash": 3, "movie_id": "movie-1", "timestamp_ms": 1500}
    ]
    assert store.active["video"]["movie-1"] == [{"hash": 90}]
    assert all(run["status"] == "published" for run in store.runs.values())


def test_audio_empty_extraction_does_not_finalize(monkeypatch, tmp_path):
    store = MemoryIngestionDB()
    previous = [{"hash": 8}]
    store.active["audio"]["movie-1"] = list(previous)

    with pytest.raises(RuntimeError, match="No audio fingerprints"):
        run_audio_ingestion(monkeypatch, tmp_path, store, [])

    assert store.active["audio"]["movie-1"] == previous
    assert store.finalized == []


def test_audio_extraction_failure_does_not_finalize(monkeypatch, tmp_path):
    store = MemoryIngestionDB()
    previous = [{"hash": 8}]
    store.active["audio"]["movie-1"] = list(previous)

    def fail_extract(_path):
        raise RuntimeError("decode failed")

    monkeypatch.setattr(audio, "get_movie_by_tmdb_id", lambda _tmdb_id: {
        "id": "movie-1", "title": "Test movie", "tmdb_id": 123,
    })
    monkeypatch.setattr(audio, "extract_audio_hashes", fail_extract)
    monkeypatch.setattr(audio, "AudioFingerprintDB", lambda: FakeAudioDB(store))
    movie_file = tmp_path / "movie.mp4"
    movie_file.write_bytes(b"placeholder")

    with pytest.raises(RuntimeError, match="decode failed"):
        audio.ingest_movie_audio(str(movie_file), 123)

    assert store.active["audio"]["movie-1"] == previous
    assert store.finalized == []


@pytest.mark.parametrize("failure", ["stage", "finalize"])
def test_audio_write_failures_do_not_replace_active_set(
    monkeypatch, tmp_path, failure
):
    store = MemoryIngestionDB()
    previous = [{"hash": 8}]
    store.active["audio"]["movie-1"] = list(previous)
    setattr(store, "fail_" + failure, True)

    with pytest.raises(RuntimeError, match="failed"):
        run_audio_ingestion(
            monkeypatch, tmp_path, store,
            [audio_fingerprint.AudioHash(hash=2, time_ms=1000)],
        )

    assert store.active["audio"]["movie-1"] == previous


def test_fingerprint_matchers_still_query_only_active_rpc(monkeypatch):
    video_client = Mock()
    video_client.rpc.return_value.execute.return_value.data = []
    monkeypatch.setattr("matcher.matcher.get_supabase_client", lambda: video_client)
    FingerprintDB().find_candidates([1])
    assert video_client.rpc.call_args.args[0] == "match_fingerprint_candidates"

    audio_client = Mock()
    audio_client.rpc.return_value.execute.return_value.data = []
    monkeypatch.setattr("audio_fingerprint.get_supabase_client", lambda: audio_client)
    audio_fingerprint.AudioFingerprintDB().find_candidates([1])
    assert audio_client.rpc.call_args.args[0] == "match_audio_candidates"


@pytest.mark.parametrize(
    ("database_class", "client_target", "modality", "stage_rpc", "finalize_rpc"),
    [
        (FingerprintDB, "matcher.matcher.get_supabase_client", "video",
         "stage_video_fingerprint_batch", "finalize_video_fingerprint_ingestion"),
        (audio_fingerprint.AudioFingerprintDB,
         "audio_fingerprint.get_supabase_client", "audio",
         "stage_audio_fingerprint_batch", "finalize_audio_fingerprint_ingestion"),
    ],
)
def test_database_adapters_use_lifecycle_rpcs(
    monkeypatch, database_class, client_target, modality, stage_rpc, finalize_rpc
):
    client = Mock()
    client.rpc.return_value.execute.return_value.data = 1
    monkeypatch.setattr(client_target, lambda: client)
    db = database_class()
    row = {"hash": 7, "movie_id": "movie-1", "timestamp_ms": 125}

    db.create_ingestion("run-1", "movie-1")
    db.stage_many("run-1", [row])
    db.complete_ingestion("run-1", "movie-1")
    db.fail_ingestion("run-1", "movie-1")
    db.finalize_ingestion("run-1", "movie-1")

    names = [call.args[0] for call in client.rpc.call_args_list]
    assert names == [
        "create_fingerprint_ingestion",
        stage_rpc,
        "complete_fingerprint_ingestion",
        "fail_fingerprint_ingestion",
        finalize_rpc,
    ]
    assert client.rpc.call_args_list[0].args[1] == {
        "p_ingestion_id": "run-1",
        "p_movie_id": "movie-1",
        "p_modality": modality,
    }
    assert client.rpc.call_args_list[1].args[1]["p_fingerprints"] == [
        {"hash": 7, "timestamp_ms": 125}
    ]


def test_run_registry_fake_rejects_reuse_wrong_movie_and_wrong_modality():
    store = MemoryIngestionDB()
    store.create("run-1", "movie-1", "video")

    with pytest.raises(RuntimeError, match="already exists"):
        store.create("run-1", "movie-1", "video")
    with pytest.raises(RuntimeError, match="mismatch"):
        store.stage("audio", "run-1", [{"movie_id": "movie-1", "hash": 1}])
    with pytest.raises(RuntimeError, match="mismatch"):
        store.stage("video", "run-1", [{"movie_id": "movie-2", "hash": 1}])
    with pytest.raises(RuntimeError, match="mismatch"):
        store.complete("video", "run-1", "movie-2")


def test_run_registry_fake_rejects_empty_and_invalid_transitions():
    store = MemoryIngestionDB()
    store.create("empty", "movie-1", "audio")
    with pytest.raises(RuntimeError, match="empty"):
        store.complete("audio", "empty", "movie-1")

    store.create("run-2", "movie-1", "video")
    store.stage("video", "run-2", [{"movie_id": "movie-1", "hash": 1}])
    store.complete("video", "run-2", "movie-1")
    with pytest.raises(RuntimeError, match="not staging"):
        store.stage("video", "run-2", [{"movie_id": "movie-1", "hash": 2}])
    store.finalize("video", "run-2", "movie-1")
    with pytest.raises(RuntimeError, match="not ready"):
        store.finalize("video", "run-2", "movie-1")

