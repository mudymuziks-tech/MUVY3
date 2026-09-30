from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Optional

from app.db.supabase import supabase


def hamming_distance(a: int, b: int) -> int:
    """Bit difference between two 64-bit hashes. 0 = identical."""
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
    but uses PostgreSQL through Supabase instead of SQLite.
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
        distance_threshold: int = 14,
    ):
        """
        Ask PostgreSQL to find fingerprints that are within
        the Hamming-distance threshold.

        This avoids downloading the entire fingerprint table
        into Python for every identification request.
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

        Supabase writes are committed automatically by
        the API, so there is nothing to do here.
        """
        pass


def match_clip(
    query_frames: list[QueryFrame],
    db: FingerprintDB,
    hash_distance_threshold: int = 14,
    offset_bucket_ms: int = 500,
    min_votes: int = 8,
    min_margin: float = 1.5,
    min_support_ratio: float = 0.60,
    min_temporal_span_ms: int = 1500,
    max_average_distance: float = 10.0,
) -> Optional[MatchResult]:
    """
    Match a query clip against the fingerprint database.

    The matcher uses:

    1. PostgreSQL candidate retrieval.
    2. Hamming-distance filtering.
    3. Timestamp-offset voting.
    4. Neighboring timestamp bucket smoothing.
    5. Query-frame support as the main confidence signal.
    6. Movie-level support margin to reject ambiguous matches.
    """

    if not query_frames:
        return None

    # ---------------------------------------------------------
    # Stage 1: retrieve candidate fingerprints
    # ---------------------------------------------------------

    query_hashes = [
        qf.hash
        for qf in query_frames
    ]

    rows = db.find_candidates(
        query_hashes,
        distance_threshold=hash_distance_threshold,
    )

    if not rows:
        return None

    # ---------------------------------------------------------
    # Stage 2: collect votes
    # ---------------------------------------------------------

    votes: dict[
        tuple[str, int],
        float,
    ] = defaultdict(float)

    frame_support: dict[
        tuple[str, int],
        set[int],
    ] = defaultdict(set)

    for query_index, qf in enumerate(query_frames):

        for stored_hash, movie_id, stored_ts in rows:

            distance = hamming_distance(
                qf.hash,
                stored_hash,
            )

            if distance > hash_distance_threshold:
                continue

            # Closer perceptual hashes receive more weight.
            weight = (
                hash_distance_threshold - distance
            ) / hash_distance_threshold

            weight = max(
                weight,
                0.05,
            )

            implied_offset = (
                stored_ts - qf.capture_time_ms
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

            frame_support[key].add(
                query_index
            )

    if not votes:
        return None

    # ---------------------------------------------------------
    # Stage 3: smooth neighboring timestamp buckets
    # ---------------------------------------------------------

    smoothed: dict[
        tuple[str, int],
        float,
    ] = defaultdict(float)

    smoothed_support: dict[
        tuple[str, int],
        set[int],
    ] = defaultdict(set)

    for (
        movie_id,
        bucket,
    ) in votes:

        key = (
            movie_id,
            bucket,
        )

        for k in (-1, 0, 1):

            neighbor_bucket = (
                bucket
                + k * offset_bucket_ms
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
        return None

    # ---------------------------------------------------------
    # Stage 4: find strongest temporal cluster per movie
    # ---------------------------------------------------------

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

        current = movie_best.get(
            movie_id
        )

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
        return None

    # ---------------------------------------------------------
    # Stage 5: select strongest movie
    #
    # Frame support is the primary signal.
    # Weighted score breaks ties.
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Stage 6: find strongest competing movie
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Stage 7: calculate support margin
    # ---------------------------------------------------------

    margin = (
        top_support / second_support
        if second_support > 0
        else float("inf")
    )

    # ---------------------------------------------------------
    # Stage 8: calculate confidence
    # ---------------------------------------------------------

    total_frames = len(
        query_frames
    )

    confidence = (
        min(
            1.0,
            top_support / total_frames,
        )
        if total_frames
        else 0.0
    )

    # ---------------------------------------------------------
    # Stage 9: confidence requirements
    # ---------------------------------------------------------

    if top_support < min_votes:
        return None

    if margin < min_margin:
        return None

    # ---------------------------------------------------------
    # Return result
    # ---------------------------------------------------------

    return MatchResult(
        movie_id=top_movie,
        offset_ms=top_offset,
        confidence=confidence,
        margin=margin,
        votes=top_support,
        total_frames=total_frames,
    )