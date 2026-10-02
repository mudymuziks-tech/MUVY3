from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from app.db.supabase import supabase


logger = logging.getLogger(__name__)


# ============================================================
# VERIFIED MATCHING BASELINE
#
# Do not change these values casually.
#
# These thresholds were verified against:
#   - Reckless
#   - Interstellar
#   - Michael
#   - Enola Holmes 3
#   - Unknown movie rejection test
#
# Any threshold change should be accompanied by regression
# testing against both known and unknown clips.
# ============================================================

DEFAULT_HASH_DISTANCE_THRESHOLD = 14
DEFAULT_OFFSET_BUCKET_MS = 500
DEFAULT_MIN_VOTES = 8
DEFAULT_MIN_MARGIN = 1.5
DEFAULT_MIN_SUPPORT_RATIO = 0.60
DEFAULT_MIN_TEMPORAL_SPAN_MS = 1500

DEFAULT_RELAXED_SUPPORT_RATIO = 0.50
DEFAULT_RELAXED_MARGIN = 3.0
DEFAULT_RELAXED_TEMPORAL_SPAN_MS = 5000


def hamming_distance(a: int, b: int) -> int:
    """Return the number of differing bits between two hashes."""
    return bin(a ^ b).count("1")


@dataclass
class QueryFrame:
    hash: int
    capture_time_ms: int


@dataclass
class MatchResult:
    movie_id: str
    offset_ms: int
    confidence: float
    margin: float
    votes: int
    total_frames: int


class FingerprintDB:
    """
    Supabase-backed fingerprint store.

    Keeps the same interface that the matcher expects,
    while using PostgreSQL through Supabase.
    """

    def add(
        self,
        hash_: int,
        movie_id: str,
        timestamp_ms: int,
    ) -> None:
        response = (
            supabase
            .table("fingerprints")
            .insert(
                {
                    "hash": hash_,
                    "movie_id": movie_id,
                    "timestamp_ms": timestamp_ms,
                }
            )
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Failed to insert fingerprint"
            )

    def add_many(
        self,
        fingerprints: list[dict],
    ) -> None:
        if not fingerprints:
            return

        response = (
            supabase
            .table("fingerprints")
            .insert(fingerprints)
            .execute()
        )

        if not response.data:
            raise RuntimeError(
                "Failed to insert fingerprints"
            )

    def find_candidates(
        self,
        query_hashes: list[int],
        distance_threshold: int = DEFAULT_HASH_DISTANCE_THRESHOLD,
    ) -> list[tuple[int, str, int]]:
        """
        Ask PostgreSQL to find fingerprints within
        the configured Hamming-distance threshold.
        """

        if not query_hashes:
            return []

        response = (
            supabase
            .rpc(
                "match_fingerprint_candidates",
                {
                    "query_hashes": query_hashes,
                    "distance_threshold": distance_threshold,
                },
            )
            .execute()
        )

        rows = response.data or []

        return [
            (
                row["hash"],
                row["movie_id"],
                row["timestamp_ms"],
            )
            for row in rows
        ]

    def commit(self) -> None:
        """
        Kept for compatibility with the old SQLite interface.

        Supabase writes are committed automatically.
        """
        pass


def match_clip(
    query_frames: list[QueryFrame],
    db: FingerprintDB,
    hash_distance_threshold: int = DEFAULT_HASH_DISTANCE_THRESHOLD,
    offset_bucket_ms: int = DEFAULT_OFFSET_BUCKET_MS,
    min_votes: int = DEFAULT_MIN_VOTES,
    min_margin: float = DEFAULT_MIN_MARGIN,
    min_support_ratio: float = DEFAULT_MIN_SUPPORT_RATIO,
    min_temporal_span_ms: int = DEFAULT_MIN_TEMPORAL_SPAN_MS,
    relaxed_support_ratio: float = DEFAULT_RELAXED_SUPPORT_RATIO,
    relaxed_margin: float = DEFAULT_RELAXED_MARGIN,
    relaxed_temporal_span_ms: int = DEFAULT_RELAXED_TEMPORAL_SPAN_MS,
) -> Optional[MatchResult]:
    """
    Match a query clip against the fingerprint database.

    The matching baseline is intentionally kept stable.

    Normal acceptance requires:
        - minimum votes
        - support ratio >= 0.60
        - margin >= 1.5
        - temporal span >= 1500 ms

    Relaxed acceptance requires:
        - minimum votes
        - support ratio >= 0.50
        - margin >= 3.0
        - temporal span >= 5000 ms

    These thresholds are the currently verified Muvy baseline.
    """

    if hash_distance_threshold <= 0:
        raise ValueError(
            "hash_distance_threshold must be greater than 0"
        )

    if offset_bucket_ms <= 0:
        raise ValueError(
            "offset_bucket_ms must be greater than 0"
        )

    if min_votes <= 0:
        raise ValueError(
            "min_votes must be greater than 0"
        )

    if not query_frames:
        return None

    query_hashes = [
        query_frame.hash
        for query_frame in query_frames
    ]

    rows = db.find_candidates(
        query_hashes,
        distance_threshold=hash_distance_threshold,
    )

    if not rows:
        logger.info(
            "[MATCHER] No fingerprint candidates found."
        )
        return None

    votes: dict[tuple[str, int], float] = defaultdict(float)

    frame_support: dict[
        tuple[str, int],
        set[int],
    ] = defaultdict(set)

    for query_index, query_frame in enumerate(query_frames):

        for stored_hash, movie_id, stored_timestamp in rows:

            distance = hamming_distance(
                query_frame.hash,
                stored_hash,
            )

            if distance > hash_distance_threshold:
                continue

            weight = (
                hash_distance_threshold - distance
            ) / hash_distance_threshold

            weight = max(weight, 0.05)

            implied_offset = (
                stored_timestamp
                - query_frame.capture_time_ms
            )

            bucket = (
                round(
                    implied_offset / offset_bucket_ms
                )
                * offset_bucket_ms
            )

            key = (
                movie_id,
                bucket,
            )

            votes[key] += weight
            frame_support[key].add(query_index)

    if not votes:
        logger.info(
            "[MATCHER] No valid fingerprint votes."
        )
        return None

    smoothed: dict[
        tuple[str, int],
        float,
    ] = defaultdict(float)

    smoothed_support: dict[
        tuple[str, int],
        set[int],
    ] = defaultdict(set)

    for movie_id, bucket in votes:

        key = (
            movie_id,
            bucket,
        )

        for neighbor in (-1, 0, 1):

            neighbor_bucket = (
                bucket
                + neighbor * offset_bucket_ms
            )

            neighbor_key = (
                movie_id,
                neighbor_bucket,
            )

            smoothed[key] += votes.get(
                neighbor_key,
                0.0,
            )

            smoothed_support[key].update(
                frame_support.get(
                    neighbor_key,
                    set(),
                )
            )

    if not smoothed:
        logger.info(
            "[MATCHER] No smoothed fingerprint votes."
        )
        return None

    movie_best: dict[
        str,
        tuple[int, float, int],
    ] = {}

    for (
        movie_id,
        bucket,
    ), vote_score in smoothed.items():

        support_count = len(
            smoothed_support[
                (movie_id, bucket)
            ]
        )

        current = movie_best.get(movie_id)

        if (
            current is None
            or support_count > current[2]
            or (
                support_count == current[2]
                and vote_score > current[1]
            )
        ):
            movie_best[movie_id] = (
                bucket,
                vote_score,
                support_count,
            )

    if not movie_best:
        logger.info(
            "[MATCHER] No movie-level candidates."
        )
        return None

    top_movie, (
        top_offset,
        top_score,
        top_support,
    ) = max(
        movie_best.items(),
        key=lambda item: (
            item[1][2],
            item[1][1],
        ),
    )

    rival_support = [
        support_count
        for movie_id, (
            bucket,
            vote_score,
            support_count,
        ) in movie_best.items()
        if movie_id != top_movie
    ]

    second_support = (
        max(rival_support)
        if rival_support
        else 0
    )

    margin = (
        top_support / second_support
        if second_support > 0
        else float("inf")
    )

    total_frames = len(query_frames)

    support_ratio = (
        top_support / total_frames
        if total_frames
        else 0.0
    )

    winning_support_frames = smoothed_support.get(
        (top_movie, top_offset),
        set(),
    )

    if len(winning_support_frames) >= 2:

        support_times = [
            query_frames[index].capture_time_ms
            for index in winning_support_frames
        ]

        temporal_span_ms = (
            max(support_times)
            - min(support_times)
        )

    else:
        temporal_span_ms = 0

    logger.info(
        "[MATCHER] verification: "
        "movie=%s support=%d/%d "
        "support_ratio=%.4f required_ratio=%.4f "
        "temporal_span=%dms required_span=%dms "
        "margin=%.4f required_margin=%.4f "
        "votes=%d required_votes=%d",
        top_movie,
        top_support,
        total_frames,
        support_ratio,
        min_support_ratio,
        temporal_span_ms,
        min_temporal_span_ms,
        margin,
        min_margin,
        top_support,
        min_votes,
    )

    if top_support < min_votes:

        logger.warning(
            "[MATCHER] REJECTED: insufficient votes. "
            "votes=%d required=%d",
            top_support,
            min_votes,
        )

        return None

    normal_match = (
        support_ratio >= min_support_ratio
        and margin >= min_margin
        and temporal_span_ms >= min_temporal_span_ms
    )

    if normal_match:

        logger.info(
            "[MATCHER] ACCEPTED: normal verification "
            "movie=%s support=%d/%d "
            "confidence=%.4f margin=%.4f "
            "offset=%dms",
            top_movie,
            top_support,
            total_frames,
            support_ratio,
            margin,
            top_offset,
        )

        return MatchResult(
            movie_id=top_movie,
            offset_ms=top_offset,
            confidence=support_ratio,
            margin=margin,
            votes=top_support,
            total_frames=total_frames,
        )

    relaxed_match = (
        support_ratio >= relaxed_support_ratio
        and margin >= relaxed_margin
        and temporal_span_ms >= relaxed_temporal_span_ms
    )

    if relaxed_match:

        logger.info(
            "[MATCHER] ACCEPTED: relaxed verification "
            "movie=%s support=%d/%d "
            "confidence=%.4f margin=%.4f "
            "temporal_span=%dms offset=%dms",
            top_movie,
            top_support,
            total_frames,
            support_ratio,
            margin,
            temporal_span_ms,
            top_offset,
        )

        return MatchResult(
            movie_id=top_movie,
            offset_ms=top_offset,
            confidence=support_ratio,
            margin=margin,
            votes=top_support,
            total_frames=total_frames,
        )

    if support_ratio < relaxed_support_ratio:

        logger.warning(
            "[MATCHER] REJECTED: support ratio too low. "
            "%.4f < %.4f",
            support_ratio,
            relaxed_support_ratio,
        )

    elif margin < relaxed_margin:

        logger.warning(
            "[MATCHER] REJECTED: match margin too weak. "
            "%.4f < %.4f",
            margin,
            relaxed_margin,
        )

    elif temporal_span_ms < relaxed_temporal_span_ms:

        logger.warning(
            "[MATCHER] REJECTED: temporal span too short. "
            "%dms < %dms",
            temporal_span_ms,
            relaxed_temporal_span_ms,
        )

    else:

        logger.warning(
            "[MATCHER] REJECTED: verification failed."
        )

    return None
