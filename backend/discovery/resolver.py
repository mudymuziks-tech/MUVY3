from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.tmdb import search_movies

from .candidates import MovieCandidate


@dataclass
class TMDBMatch:
    candidate: MovieCandidate
    tmdb_id: int
    title: str
    release_date: str | None
    score: float
    tmdb_result: dict


def _normalize(value: str) -> str:
    value = value.casefold()

    value = re.sub(
        r"[^\w\s]",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


def _similarity(
    left: str,
    right: str,
) -> float:
    """
    Simple token-based similarity.

    Returns 0.0 - 1.0.
    """

    left_tokens = set(
        _normalize(left).split()
    )

    right_tokens = set(
        _normalize(right).split()
    )

    if not left_tokens or not right_tokens:
        return 0.0

    intersection = left_tokens & right_tokens

    union = left_tokens | right_tokens

    return len(intersection) / len(union)


def _release_year(
    release_date: str | None,
) -> int | None:

    if not release_date:
        return None

    match = re.match(
        r"(\d{4})",
        release_date,
    )

    if not match:
        return None

    return int(match.group(1))


def score_tmdb_result(
    candidate: MovieCandidate,
    result: dict,
) -> float:

    title = (
        result.get("title")
        or result.get("original_title")
        or ""
    )

    original_title = (
        result.get("original_title")
        or ""
    )

    score = 0.0

    # Candidate title vs TMDB title.
    title_similarity = _similarity(
        candidate.title,
        title,
    )

    score += title_similarity * 60

    # Candidate title vs original title.
    if original_title:
        original_similarity = _similarity(
            candidate.title,
            original_title,
        )

        score += original_similarity * 25

    # Exact normalized title.
    candidate_normalized = _normalize(
        candidate.title
    )

    title_normalized = _normalize(
        title
    )

    original_normalized = _normalize(
        original_title
    )

    if (
        candidate_normalized
        and candidate_normalized == title_normalized
    ):
        score += 25

    elif (
        candidate_normalized
        and candidate_normalized == original_normalized
    ):
        score += 20

    # Release year agreement.
    tmdb_year = _release_year(
        result.get("release_date")
    )

    if (
        candidate.year is not None
        and tmdb_year is not None
    ):

        if candidate.year == tmdb_year:
            score += 25

        elif abs(candidate.year - tmdb_year) == 1:
            score += 8

        else:
            score -= 15

    # Lens evidence.
    score += min(
        candidate.frame_count,
        3,
    ) * 5

    score += min(
        candidate.source_count,
        3,
    ) * 3

    return score


def resolve_candidate(
    candidate: MovieCandidate,
) -> TMDBMatch | None:
    """
    Resolve one Lens movie candidate through TMDB.
    """

    results = search_movies(
        candidate.title
    )

    if not results:
        return None

    scored = []

    for result in results:

        score = score_tmdb_result(
            candidate,
            result,
        )

        scored.append(
            (
                score,
                result,
            )
        )

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    best_score, best_result = scored[0]

    # Do not accept weak TMDB matches.
    if best_score < 55:
        return None

    tmdb_id = best_result.get(
        "id"
    )

    if not tmdb_id:
        return None

    title = (
        best_result.get("title")
        or best_result.get("original_title")
        or candidate.title
    )

    return TMDBMatch(
        candidate=candidate,
        tmdb_id=int(tmdb_id),
        title=title,
        release_date=best_result.get(
            "release_date"
        ),
        score=best_score,
        tmdb_result=best_result,
    )


def _dedupe_evidence(
    evidence: list,
) -> list:
    seen: set[tuple[int, str, str, str]] = set()
    unique: list = []

    for item in evidence:
        identity = (
            item.frame_timestamp_ms,
            (item.link or "").strip(),
            (item.image_url or "").strip(),
            (item.thumbnail_url or "").strip(),
        )

        if identity in seen:
            continue

        seen.add(identity)
        unique.append(item)

    return unique


def consolidate_tmdb_matches(
    matches: list[TMDBMatch],
) -> list[TMDBMatch]:
    """
    Merge multilingual Lens variants that resolve to the same TMDB movie.

    This keeps the evidence trail intact while avoiding false title drift
    between English, Russian, Portuguese, and other localized titles.
    """

    grouped: dict[int, dict[str, object]] = {}

    for match in matches:
        existing = grouped.get(match.tmdb_id)

        if existing is None:
            candidate = MovieCandidate(
                title=match.title,
                year=match.candidate.year,
                evidence=list(match.candidate.evidence),
            )

            grouped[match.tmdb_id] = {
                "candidate": candidate,
                "tmdb_id": match.tmdb_id,
                "title": match.title,
                "release_date": match.release_date,
                "score": match.score,
                "tmdb_result": match.tmdb_result,
            }
            continue

        candidate = existing["candidate"]
        candidate.evidence.extend(match.candidate.evidence)
        candidate.evidence = _dedupe_evidence(candidate.evidence)

        if match.score > float(existing["score"]):
            existing["title"] = match.title
            existing["release_date"] = match.release_date
            existing["score"] = match.score
            existing["tmdb_result"] = match.tmdb_result
            candidate.title = match.title

        if candidate.year is None and match.candidate.year is not None:
            candidate.year = match.candidate.year

    consolidated: list[TMDBMatch] = []

    for item in grouped.values():
        candidate = item["candidate"]
        candidate.title = str(item["title"])
        consolidated.append(
            TMDBMatch(
                candidate=candidate,
                tmdb_id=int(item["tmdb_id"]),
                title=str(item["title"]),
                release_date=item["release_date"],
                score=float(item["score"]),
                tmdb_result=item["tmdb_result"],
            )
        )

    consolidated.sort(
        key=lambda match: (
            match.score,
            match.candidate.discovery_score,
            match.candidate.frame_count,
        ),
        reverse=True,
    )

    return consolidated


def resolve_candidates(
    candidates: list[MovieCandidate],
) -> list[TMDBMatch]:
    """
    Resolve all viable Lens candidates through TMDB.

    Results are sorted by TMDB confidence and multilingual Lens variants are
    merged after resolution by shared TMDB movie ID.
    """

    matches: list[TMDBMatch] = []

    for candidate in candidates:
        try:
            match = resolve_candidate(
                candidate
            )
        except Exception as exc:
            print(
                f"[TMDB] Failed to resolve "
                f"'{candidate.title}': {exc}"
            )
            continue

        if match is not None:
            matches.append(match)

    matches.sort(
        key=lambda match: (
            match.score,
            match.candidate.discovery_score,
            match.candidate.frame_count,
        ),
        reverse=True,
    )

    return consolidate_tmdb_matches(matches)