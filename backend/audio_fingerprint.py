from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import av
import numpy as np

from app.db.supabase import get_supabase_client


# Fingerprinting parameters. These MUST be identical for ingestion and for
# query matching, so both sides go through extract_audio_hashes() below.
SAMPLE_RATE = 11025
FFT_SIZE = 2048
HOP_LENGTH = 512
PEAK_FREQ_NEIGHBORHOOD = 10
PEAK_TIME_NEIGHBORHOOD = 5
PEAK_THRESHOLD_REL = 0.10
TARGET_TIME_DELTA_MIN = 1
TARGET_TIME_DELTA_MAX = 40
FAN_OUT = 5
OFFSET_BUCKET_MS = 500
MIN_VOTES = 5


@dataclass
class AudioHash:
    hash: int
    time_ms: int


def _decode_audio_mono(file_like):
    """Decode any audio container/codec to mono float32 at SAMPLE_RATE."""
    container = av.open(file_like)
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=SAMPLE_RATE)
    chunks = []

    for frame in container.decode(audio=0):
        frame.pts = None
        for out in resampler.resample(frame):
            chunks.append(out.to_ndarray().reshape(-1))

    for out in resampler.resample(None):
        chunks.append(out.to_ndarray().reshape(-1))

    container.close()

    if not chunks:
        return np.zeros(0, dtype=np.float32)

    return np.concatenate(chunks).astype(np.float32)


def _spectrogram(audio):
    """Magnitude spectrogram of shape (frames, freq_bins)."""
    if audio.size < FFT_SIZE:
        audio = np.pad(audio, (0, FFT_SIZE - audio.size))

    window = np.hanning(FFT_SIZE)
    view = np.lib.stride_tricks.sliding_window_view(audio, FFT_SIZE)[::HOP_LENGTH]
    return np.abs(np.fft.rfft(view * window, axis=1))


def _spectral_peaks(spec):
    """Vectorised local-maxima detection in the (time, frequency) plane."""
    t_nb, f_nb = PEAK_TIME_NEIGHBORHOOD, PEAK_FREQ_NEIGHBORHOOD
    padded = np.pad(spec, ((t_nb, t_nb), (f_nb, f_nb)), mode="constant")
    local_max = np.copy(spec)

    for dt in range(-t_nb, t_nb + 1):
        for df in range(-f_nb, f_nb + 1):
            shifted = padded[
                dt + t_nb : dt + t_nb + spec.shape[0],
                df + f_nb : df + f_nb + spec.shape[1],
            ]
            local_max = np.maximum(local_max, shifted)

    threshold = spec.max() * PEAK_THRESHOLD_REL if spec.size else 0.0
    is_peak = (spec == local_max) & (spec > threshold)
    return np.argwhere(is_peak)  # rows of (time_index, freq_index)


def _constellation_hashes(peaks):
    """Pair each anchor peak with forward target peaks to form int64 hashes."""
    by_time = {}
    for t, f in peaks:
        by_time.setdefault(int(t), []).append(int(f))

    times = sorted(by_time)
    hashes = []

    for t_a in times:
        targets = 0
        for t_b in times:
            if t_b <= t_a:
                continue
            dt = t_b - t_a
            if dt > TARGET_TIME_DELTA_MAX:
                break
            if dt < TARGET_TIME_DELTA_MIN:
                continue
            for f_a in by_time[t_a]:
                for f_b in by_time[t_b]:
                    if abs(f_b - f_a) <= PEAK_FREQ_NEIGHBORHOOD:
                        combined = (f_a << 20) | (f_b << 10) | (dt & 0x3FF)
                        hashes.append(
                            AudioHash(
                                hash=combined,
                                time_ms=int(t_a * HOP_LENGTH / SAMPLE_RATE * 1000),
                            )
                        )
                        targets += 1
                        if targets >= FAN_OUT:
                            break
                if targets >= FAN_OUT:
                    break
            if targets >= FAN_OUT:
                break

    return hashes


def extract_audio_hashes(file_like):
    """Full audio fingerprint pipeline: decode -> spectrogram -> hashes."""
    audio = _decode_audio_mono(file_like)
    if audio.size == 0:
        return []

    spec = _spectrogram(audio)
    if spec.size == 0 or spec.max() <= 0:
        return []

    peaks = _spectral_peaks(spec)
    return _constellation_hashes(peaks)


class AudioFingerprintDB:
    """Supabase-backed audio fingerprint store (mirrors the video store)."""

    def add_many(self, fingerprints):
        if not fingerprints:
            return
        client = get_supabase_client()
        response = (
            client
            .table("audio_fingerprints")
            .insert(fingerprints)
            .execute()
        )
        if not response.data:
            raise RuntimeError("Failed to insert audio fingerprints")

    def create_ingestion(self, ingestion_id, movie_id):
        response = get_supabase_client().rpc(
            "create_fingerprint_ingestion",
            {
                "p_ingestion_id": ingestion_id,
                "p_movie_id": movie_id,
                "p_modality": "audio",
            },
        ).execute()
        if response.data is None:
            raise RuntimeError("Failed to create audio fingerprint ingestion run")

    def stage_many(self, ingestion_id, fingerprints):
        """Upload a batch through the database-guarded staging RPC."""
        if not fingerprints:
            raise ValueError("Cannot stage an empty audio fingerprint batch")
        movie_id = fingerprints[0]["movie_id"]
        if any(fingerprint["movie_id"] != movie_id for fingerprint in fingerprints):
            raise ValueError("A staging batch must contain fingerprints for one movie")
        payload = [
            {"hash": fingerprint["hash"], "timestamp_ms": fingerprint["timestamp_ms"]}
            for fingerprint in fingerprints
        ]
        response = get_supabase_client().rpc(
            "stage_audio_fingerprint_batch",
            {
                "p_ingestion_id": ingestion_id,
                "p_movie_id": movie_id,
                "p_fingerprints": payload,
            },
        ).execute()
        if int(response.data or 0) != len(payload):
            raise RuntimeError("Audio staging RPC did not accept the complete batch")

    def complete_ingestion(self, ingestion_id, movie_id):
        response = get_supabase_client().rpc(
            "complete_fingerprint_ingestion",
            {
                "p_ingestion_id": ingestion_id,
                "p_movie_id": movie_id,
                "p_modality": "audio",
            },
        ).execute()
        if response.data is None:
            raise RuntimeError("Failed to complete audio fingerprint ingestion run")
        return int(response.data)

    def fail_ingestion(self, ingestion_id, movie_id):
        get_supabase_client().rpc(
            "fail_fingerprint_ingestion",
            {
                "p_ingestion_id": ingestion_id,
                "p_movie_id": movie_id,
                "p_modality": "audio",
            },
        ).execute()

    def finalize_ingestion(self, ingestion_id, movie_id):
        """Atomically publish a ready audio run."""
        response = get_supabase_client().rpc(
            "finalize_audio_fingerprint_ingestion",
            {"p_ingestion_id": ingestion_id, "p_movie_id": movie_id},
        ).execute()
        if response.data is None:
            raise RuntimeError("Failed to finalize audio fingerprint ingestion")
        return int(response.data)

    def find_candidates(self, query_hashes):
        if not query_hashes:
            return []
        client = get_supabase_client()
        response = (
            client
            .rpc(
                "match_audio_candidates",
                {"query_hashes": query_hashes},
            )
            .execute()
        )
        return response.data or []


def match_audio_clip(query_hashes, db):
    """Match query hashes against the DB using offset voting."""
    if not query_hashes:
        return None

    query_values = [h.hash for h in query_hashes]
    rows = db.find_candidates(query_values)

    if not rows:
        return None

    query_time = {h.hash: h.time_ms for h in query_hashes}
    votes = defaultdict(int)

    for row in rows:
        stored_hash = int(row["hash"])
        stored_time = int(row["timestamp_ms"])
        query_ms = query_time.get(stored_hash)
        if query_ms is None:
            continue
        delta = stored_time - query_ms
        bucket = round(delta / OFFSET_BUCKET_MS)
        votes[(row["movie_id"], bucket)] += 1

    if not votes:
        return None

    (movie_id, bucket), top_votes = max(votes.items(), key=lambda item: item[1])

    if top_votes < MIN_VOTES:
        return None

    support = sum(1 for (mid, _), count in votes.items() if mid == movie_id)
    return {
        "movie_id": movie_id,
        "votes": top_votes,
        "clusters": support,
        "confidence": min(1.0, top_votes / max(1, len(query_hashes))),
        "offset_ms": int(bucket * OFFSET_BUCKET_MS),
    }
