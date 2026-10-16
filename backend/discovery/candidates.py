from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


YEAR_RE = re.compile(
    r"\b(19\d{2}|20\d{2})\b"
)


NOISE_PATTERNS = [
    r"\bofficial\s+trailer\b",
    r"\bofficial\s+teaser\b",
    r"\bofficial\s+clip\b",
    r"\btrailer\b",
    r"\bteaser\b",
    r"\bhd\b",
    r"\b4k\b",
    r"\bmovie\b",
    r"\bfilm\b",
    r"\bvideo\b",
    r"\bdailymotion\b",
    r"\byoutube\b",
    r"\bnetflix\b",
    r"\bimdb\b",
    r"\bfilmaffinity\b",
    r"\brotten\s+tomatoes\b",
    r"\bthe\s+movie\s+database\b",
    r"\btmdb\b",
]


NON_MOVIE_PATTERNS = [
    r"\bepisode\b",
    r"\bseason\b",
    r"\bactor\b",
    r"\bactress\b",
    r"\bdirector\b",
    r"\bcomposer\b",
    r"\bfestival\b",
    r"\bstock\s+video\b",
    r"\bstock\s+footage\b",
    r"\bgif\b",
]


@dataclass
class LensEvidence:
    title: str
    source: str
    link: str
    frame_timestamp_ms: int
    position: int | None = None

    # Visual evidence returned by Google Lens.
    image_url: str | None = None
    thumbnail_url: str | None = None


@dataclass
class MovieCandidate:
    title: str
    year: int | None = None

    evidence: list[LensEvidence] = field(
        default_factory=list
    )

    @property
    def frame_count(self) -> int:
        return len(
            {
                evidence.frame_timestamp_ms
                for evidence in self.evidence
            }
        )

    @property
    def source_count(self) -> int:
        return len(
            {
                source_name(
                    evidence.source,
                    evidence.link,
                )
                for evidence in self.evidence
                if source_name(
                    evidence.source,
                    evidence.link,
                )
            }
        )

    @property
    def distinct_link_count(self) -> int:
        return len(
            {
                evidence.link
                for evidence in self.evidence
                if evidence.link
            }
        )

    @property
    def best_position(self) -> int:
        positions = [
            evidence.position
            for evidence in self.evidence
            if evidence.position is not None
        ]

        return (
            min(positions)
            if positions
            else 999
        )

    @property
    def key(self) -> str:
        return normalize_title(
            self.title
        )

    @property
    def discovery_score(self) -> float:
        score = 0.0

        # Cross-frame agreement is important.
        score += (
            min(
                self.frame_count,
                3,
            )
            * 12
        )

        # Multiple sources provide stronger
        # evidence than a single source.
        score += (
            min(
                self.source_count,
                3,
            )
            * 8
        )

        # Multiple distinct URLs are useful,
        # but should not dominate the score.
        score += (
            min(
                self.distinct_link_count,
                3,
            )
            * 5
        )

        # Reward strong Lens positions.
        if self.best_position <= 5:
            score += 12

        elif self.best_position <= 10:
            score += 7

        elif self.best_position <= 20:
            score += 3

        # Inspect the original Lens result titles
        # for useful semantic signals.
        for evidence in self.evidence:

            title = evidence.title.casefold()

            if "official trailer" in title:
                score += 10

            elif "official teaser" in title:
                score += 7

            if "movie" in title:
                score += 5

            source = source_name(
                evidence.source,
                evidence.link,
            )

            if source in {
                "dailymotion",
                "youtube",
                "filmaffinity",
                "imdb",
                "tmdb",
                "rottentomatoes",
                "netflix",
            }:
                score += 4

        return score


def source_name(
    source: str,
    link: str,
) -> str:

    if source:

        value = (
            source
            .casefold()
            .strip()
        )

        if "dailymotion" in value:
            return "dailymotion"

        if "youtube" in value:
            return "youtube"

        if "filmaffinity" in value:
            return "filmaffinity"

        if "imdb" in value:
            return "imdb"

        if (
            "tmdb" in value
            or "movie database" in value
        ):
            return "tmdb"

        if "rotten tomatoes" in value:
            return "rottentomatoes"

        if "netflix" in value:
            return "netflix"

        return value

    try:
        host = (
            urlparse(link)
            .netloc
            .casefold()
        )

    except Exception:
        return ""

    host = host.removeprefix(
        "www."
    )

    return host


def normalize_title(
    title: str,
) -> str:

    value = title.strip()

    value = re.sub(
        r"\s*[-|]\s*"
        r"(IMDb|Filmaffinity|TMDB|Rotten Tomatoes)"
        r"\s*$",
        "",
        value,
        flags=re.IGNORECASE,
    )

    for pattern in NOISE_PATTERNS:

        value = re.sub(
            pattern,
            " ",
            value,
            flags=re.IGNORECASE,
        )

    value = YEAR_RE.sub(
        " ",
        value,
    )

    value = re.sub(
        r"[|:/]+",
        " ",
        value,
    )

    value = re.sub(
        r"[-–—]+",
        " ",
        value,
    )

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

    return value.casefold()


def extract_year(
    title: str,
) -> int | None:

    match = YEAR_RE.search(
        title
    )

    if not match:
        return None

    return int(
        match.group(0)
    )


def looks_like_movie_result(
    title: str,
) -> bool:

    lowered = title.casefold()

    return not any(
        re.search(
            pattern,
            lowered,
        )
        for pattern in NON_MOVIE_PATTERNS
    )


def clean_candidate_title(
    title: str,
) -> str:

    value = title.strip()

    # Remove database / review-site suffixes.
    value = re.sub(
        r"\s*[-|]\s*"
        r"(IMDb|Filmaffinity|TMDB|Rotten Tomatoes)"
        r".*$",
        "",
        value,
        flags=re.IGNORECASE,
    )

    # Remove video-platform suffixes.
    value = re.sub(
        r"\s*[-|:]?\s*"
        r"(?:video\s+)?"
        r"(Dailymotion|YouTube)"
        r".*$",
        "",
        value,
        flags=re.IGNORECASE,
    )

    # Remove trailer / teaser descriptions.
    value = re.sub(
        r"\s*[-|:]?\s*"
        r"(Official\s+Trailer|Official\s+Teaser|"
        r"Trailer|Teaser).*$",
        "",
        value,
        flags=re.IGNORECASE,
    )

    # Remove known source / platform noise.
    for pattern in NOISE_PATTERNS:

        value = re.sub(
            pattern,
            " ",
            value,
            flags=re.IGNORECASE,
        )

    # Remove years after extracting them.
    value = YEAR_RE.sub(
        " ",
        value,
    )

    value = re.sub(
        r"[|:/]+",
        " ",
        value,
    )

    value = re.sub(
        r"[-–—]+",
        " ",
        value,
    )

    # Clean empty brackets created by
    # removing years/noise.
    value = re.sub(
        r"\(\s*\)",
        "",
        value,
    )

    value = re.sub(
        r"\[\s*\]",
        "",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return value


def _iter_result_objects(
    value: Any,
):
    if isinstance(value, dict):

        if (
            isinstance(
                value.get("title"),
                str,
            )
            and isinstance(
                value.get("link"),
                str,
            )
        ):
            yield value

        for child in value.values():

            yield from _iter_result_objects(
                child
            )

    elif isinstance(value, list):

        for child in value:

            yield from _iter_result_objects(
                child
            )


def extract_candidates(
    frame_results: dict[
        int,
        dict[str, Any],
    ],
) -> list[MovieCandidate]:

    candidates: dict[
        tuple[str, int | None],
        MovieCandidate,
    ] = {}

    # Prevent the same Lens result from being
    # counted multiple times within one frame.
    seen_evidence: set[
        tuple[int, str, str]
    ] = set()

    for (
        timestamp_ms,
        response,
    ) in frame_results.items():

        for result in _iter_result_objects(
            response
        ):

            title = result.get(
                "title",
                "",
            ).strip()

            link = result.get(
                "link",
                "",
            ).strip()

            source = result.get(
                "source",
                "",
            ).strip()

            if not title or not link:
                continue

            evidence_key = (
                timestamp_ms,
                title.casefold(),
                link,
            )

            if evidence_key in seen_evidence:
                continue

            seen_evidence.add(
                evidence_key
            )

            if not looks_like_movie_result(
                title
            ):
                continue

            clean_title = (
                clean_candidate_title(
                    title
                )
            )

            if len(clean_title) < 2:
                continue

            year = extract_year(
                title
            )

            normalized = normalize_title(
                clean_title
            )

            if not normalized:
                continue

            key = (
                normalized,
                year,
            )

            candidate = candidates.get(
                key
            )

            if candidate is None:

                candidate = MovieCandidate(
                    title=clean_title,
                    year=year,
                )

                candidates[key] = (
                    candidate
                )

            candidate.evidence.append(
                LensEvidence(
                    title=title,
                    source=source,
                    link=link,
                    frame_timestamp_ms=(
                        timestamp_ms
                    ),
                    position=result.get(
                        "position"
                    ),
                    image_url=result.get(
                        "image"
                    ),
                    thumbnail_url=result.get(
                        "thumbnail"
                    ),
                )
            )

    candidates_list = list(
        candidates.values()
    )

    candidates_list.sort(
        key=lambda candidate: (
            candidate.discovery_score,
            candidate.frame_count,
            candidate.source_count,
            candidate.distinct_link_count,
            -candidate.best_position,
        ),
        reverse=True,
    )

    return candidates_list
