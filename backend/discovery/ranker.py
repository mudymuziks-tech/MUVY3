from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class CandidateEvidence:
    title: str
    source: str
    link: str
    position: int
    frame: str
    score: float


MOVIE_SOURCES = {
    "imdb",
    "tmdb",
    "rottentomatoes",
    "filmaffinity",
    "letterboxd",
    "metacritic",
    "netflix",
    "youtube",
    "dailymotion",
    "vimeo",
}

WEAK_SOURCES = {
    "reddit",
    "tumblr",
    "x",
    "twitter",
    "pinterest",
}


def normalize_title(title: str) -> str:
    title = title.lower()

    # Remove common result noise.
    title = re.sub(
        r"\b(official|trailer|teaser|clip|movie|film|watch|"
        r"new|hd|4k|full|review)\b",
        " ",
        title,
        flags=re.IGNORECASE,
    )

    # Remove years.
    title = re.sub(r"\b(19|20)\d{2}\b", " ", title)

    # Remove punctuation.
    title = re.sub(r"[^\w\s]", " ", title)

    return " ".join(title.split())


def source_name(link: str, source: str) -> str:
    if source:
        return source.strip().lower()

    try:
        hostname = urlparse(link).netloc.lower()
        return hostname.replace("www.", "")
    except Exception:
        return ""


def score_result(
    title: str,
    source: str,
    link: str,
    position: int,
) -> float:
    score = 0.0

    title_lower = title.lower()
    source_lower = source_name(link, source)

    # Search position matters, but only mildly.
    score += max(0.0, 10.0 - position * 0.20)

    # Strong movie/entertainment sources.
    for strong_source in MOVIE_SOURCES:
        if strong_source in source_lower:
            score += 8.0
            break

    # Weaker community/social sources.
    for weak_source in WEAK_SOURCES:
        if weak_source in source_lower:
            score -= 2.0
            break

    # Strong semantic signals.
    if "official trailer" in title_lower:
        score += 7.0

    if "official teaser" in title_lower:
        score += 6.0

    if "movie" in title_lower:
        score += 4.0

    if "film" in title_lower:
        score += 2.0

    # A result explicitly tied to a movie database is useful.
    if "imdb" in title_lower:
        score += 5.0

    if "tmdb" in title_lower:
        score += 5.0

    # Generic unrelated-looking results get penalized.
    if any(
        word in title_lower
        for word in (
            "episode",
            "season",
            "actor",
            "director",
            "stock video",
            "festival guide",
        )
    ):
        score -= 5.0

    return score


def extract_result_objects(obj):
    """
    Recursively find dictionaries that look like Lens search results.
    """
    if isinstance(obj, dict):
        if (
            isinstance(obj.get("title"), str)
            and (
                isinstance(obj.get("link"), str)
                or isinstance(obj.get("url"), str)
            )
        ):
            yield obj

        for value in obj.values():
            yield from extract_result_objects(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from extract_result_objects(item)


def rank_frame_results(response: dict, frame: str):
    results = []

    seen = set()

    for item in extract_result_objects(response):
        title = item.get("title", "").strip()
        link = (
            item.get("link")
            or item.get("url")
            or ""
        ).strip()

        if not title or not link:
            continue

        position = item.get("position", 999)

        key = (
            normalize_title(title),
            link,
        )

        if key in seen:
            continue

        seen.add(key)

        source = item.get("source", "")

        score = score_result(
            title,
            source,
            link,
            position,
        )

        results.append(
            CandidateEvidence(
                title=title,
                source=source,
                link=link,
                position=position,
                frame=frame,
                score=score,
            )
        )

    return sorted(
        results,
        key=lambda result: result.score,
        reverse=True,
    )


def aggregate_candidates(frame_results):
    candidates = defaultdict(
        lambda: {
            "score": 0.0,
            "frames": set(),
            "evidence": [],
        }
    )

    for results in frame_results:
        for result in results:
            normalized = normalize_title(result.title)

            if not normalized:
                continue

            candidates[normalized]["score"] += result.score
            candidates[normalized]["frames"].add(result.frame)
            candidates[normalized]["evidence"].append(result)

    ranked = []

    for normalized, data in candidates.items():
        frame_count = len(data["frames"])

        # Cross-frame agreement is extremely important.
        cross_frame_bonus = frame_count * 12.0

        total_score = (
            data["score"]
            + cross_frame_bonus
        )

        ranked.append(
            {
                "candidate": normalized,
                "score": total_score,
                "frame_count": frame_count,
                "evidence": data["evidence"],
            }
        )

    return sorted(
        ranked,
        key=lambda item: item["score"],
        reverse=True,
    )
