from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

import cv2
import numpy as np
import requests

from .candidates import LensEvidence, MovieCandidate
from .resolver import TMDBMatch


@dataclass
class VerificationResult:
    candidate: MovieCandidate
    tmdb_match: TMDBMatch

    verified: bool
    score: float

    evidence_score: float
    title_score: float
    year_score: float
    visual_score: float

    unique_frames: int
    unique_sources: int
    unique_links: int
    images_checked: int
    visual_matches: int

    reason: str


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VISUAL_HAMMING_THRESHOLD = 18

MIN_EVIDENCE_SCORE = 45.0
MIN_VERIFICATION_SCORE = 65.0

MIN_UNIQUE_FRAMES = 2
MIN_UNIQUE_SOURCES = 2
MIN_UNIQUE_LINKS = 2

REQUEST_TIMEOUT_SECONDS = 15


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.casefold()
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def _extract_year(value: str | None) -> int | None:
    if not value:
        return None

    match = re.search(r"\b(19|20)\d{2}\b", value)

    if not match:
        return None

    return int(match.group(0))


def _canonical_url(url: str | None) -> str:
    if not url:
        return ""

    try:
        parsed = urlparse(url)
    except Exception:
        return url.strip().lower()

    hostname = (parsed.hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]

    path = parsed.path.rstrip("/")

    relevant_params = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        normalized_key = key.lower()
        if normalized_key in {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "fbclid",
            "gclid",
            "si",
            "feature",
            "mc_cid",
            "mc_eid",
            "igshid",
        }:
            continue
        relevant_params.append((normalized_key, value))

    relevant_params.sort()
    query_string = "&".join(
        f"{key}={value}"
        for key, value in relevant_params
    )

    canonical = f"{parsed.scheme.lower()}://{hostname}{path}"
    if query_string:
        canonical += f"?{query_string}"

    return canonical


def _domain(url: str | None) -> str:
    if not url:
        return ""

    try:
        hostname = urlparse(url).hostname

        if not hostname:
            return ""

        hostname = hostname.lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        return hostname

    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Evidence independence
# ---------------------------------------------------------------------------

def _unique_evidence(candidate: MovieCandidate) -> list[LensEvidence]:
    """
    Remove duplicate evidence.

    Google Lens can return the same underlying image/video multiple times
    through different result blocks. Those should NOT count as independent
    evidence.
    """

    seen: set[tuple[str, str, str]] = set()
    unique: list[LensEvidence] = []

    for evidence in candidate.evidence:
        identity = (
            evidence.frame_timestamp_ms,
            _canonical_url(evidence.link),
            _canonical_url(evidence.image_url),
            _canonical_url(evidence.thumbnail_url),
        )

        if identity in seen:
            continue

        seen.add(identity)
        unique.append(evidence)

    return unique



def _evidence_metrics(
    candidate: MovieCandidate,
) -> tuple[int, int, int]:
    evidence = _unique_evidence(candidate)

    frames = {
        item.frame_timestamp_ms
        for item in evidence
    }

    # Prefer the actual URL hostname over a provider's display label.
    sources = {
        _domain(item.link) or item.source.casefold().strip()
        for item in evidence
        if item.link or item.source
    }

    links = {
        item.link.strip()
        for item in evidence
        if item.link
    }

    return len(frames), len(sources), len(links)


# ---------------------------------------------------------------------------
# Title / year verification
# ---------------------------------------------------------------------------

def _title_similarity(left: str, right: str) -> float:
    left_normalized = _normalize_text(left)
    right_normalized = _normalize_text(right)

    if not left_normalized or not right_normalized:
        return 0.0

    if left_normalized == right_normalized:
        return 1.0

    left_tokens = set(left_normalized.split())
    right_tokens = set(right_normalized.split())

    if not left_tokens or not right_tokens:
        return 0.0

    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens

    return len(intersection) / len(union)


def _calculate_title_score(
    candidate: MovieCandidate,
    tmdb_match: TMDBMatch,
) -> float:
    candidate_title = _normalize_text(candidate.title)
    tmdb_title = _normalize_text(tmdb_match.title)

    if not candidate_title or not tmdb_title:
        return 0.0

    similarity = _title_similarity(
        candidate_title,
        tmdb_title,
    )

    if similarity >= 1.0:
        return 30.0

    if similarity >= 0.75:
        return 24.0

    if similarity >= 0.50:
        return 15.0

    if similarity >= 0.30:
        return 7.0

    return 0.0


def _calculate_year_score(
    candidate: MovieCandidate,
    tmdb_match: TMDBMatch,
) -> float:
    candidate_year = candidate.year
    tmdb_year = _extract_year(tmdb_match.release_date)

    if candidate_year is None or tmdb_year is None:
        return 0.0

    if candidate_year == tmdb_year:
        return 20.0

    if abs(candidate_year - tmdb_year) == 1:
        return 8.0

    return -15.0


# ---------------------------------------------------------------------------
# Evidence scoring
# ---------------------------------------------------------------------------

def _calculate_evidence_score(
    candidate: MovieCandidate,
) -> float:
    """
    Score independent Lens evidence.

    Important:
    Repeated copies of the same URL/image do not increase the score.
    """

    frames, sources, links = _evidence_metrics(candidate)

    score = 0.0

    # Independent clip timestamps
    if frames >= 3:
        score += 30.0
    elif frames >= 2:
        score += 25.0
    elif frames == 1:
        score += 10.0

    # Independent domains
    if sources >= 3:
        score += 30.0
    elif sources >= 2:
        score += 25.0
    elif sources == 1:
        score += 10.0

    # Independent result URLs
    if links >= 4:
        score += 20.0
    elif links >= 2:
        score += 15.0
    elif links == 1:
        score += 5.0

    return min(score, 75.0)


# ---------------------------------------------------------------------------
# Image downloading
# ---------------------------------------------------------------------------

def _download_image(url: str) -> bytes | None:
    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/120 Safari/537.36"
                )
            },
        )

        if response.status_code != 200:
            return None

        return response.content

    except requests.RequestException:
        return None


# ---------------------------------------------------------------------------
# pHash
# ---------------------------------------------------------------------------

def _phash_from_image(image_bytes: bytes) -> int | None:
    array = np.frombuffer(
        image_bytes,
        dtype=np.uint8,
    )

    image = cv2.imdecode(
        array,
        cv2.IMREAD_GRAYSCALE,
    )

    if image is None:
        return None

    image = cv2.resize(
        image,
        (32, 32),
        interpolation=cv2.INTER_AREA,
    )

    image = np.asarray(
        image,
        dtype=np.float32,
    )

    image = np.ascontiguousarray(image)

    dct = cv2.dct(image)

    low_frequency = dct[:8, :8].flatten()

    # Remove DC component.
    low_frequency = low_frequency[1:]

    median = np.median(low_frequency)

    bits = low_frequency > median

    result = 0

    for bit in bits:
        result = (result << 1) | int(bit)

    return result


def _hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


# ---------------------------------------------------------------------------
# Video frame extraction
# ---------------------------------------------------------------------------

def _extract_frame(
    video_path: str,
    timestamp_ms: int,
) -> bytes | None:
    path = Path(video_path)

    if not path.exists():
        return None

    try:
        timestamp = float(timestamp_ms)
    except (TypeError, ValueError, OverflowError):
        return None

    if not np.isfinite(timestamp) or timestamp < 0:
        return None

    capture = cv2.VideoCapture(str(path))

    if not capture.isOpened():
        capture.release()
        return None

    try:
        capture.set(
            cv2.CAP_PROP_POS_MSEC,
            timestamp,
        )

        success, frame = capture.read()

        if not success or frame is None:
            return None

        success, encoded = cv2.imencode(
            ".jpg",
            frame,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                90,
            ],
        )

        if not success:
            return None

        return encoded.tobytes()

    finally:
        capture.release()

def _visual_similarity(
    video_path: str,
    evidence: LensEvidence,
) -> tuple[bool, float]:
    """
    Compare one Lens image against the corresponding video frame.

    This is deliberately a SUPPORTING signal.

    A failure here does not mean the candidate is wrong because Lens may
    return thumbnails/keyframes that are visually related but not identical
    to the exact frame in the uploaded clip. We therefore allow a narrow
    search around the expected timestamp before concluding there is no
    visual corroboration.
    """

    image_url = (
        evidence.image_url
        or evidence.thumbnail_url
    )

    if not image_url:
        return False, 0.0

    reference_bytes = _download_image(image_url)

    if not reference_bytes:
        return False, 0.0

    reference_hash = _phash_from_image(
        reference_bytes
    )

    if reference_hash is None:
        return False, 0.0

    candidate_timestamps = [
        evidence.frame_timestamp_ms,
        evidence.frame_timestamp_ms - 250,
        evidence.frame_timestamp_ms + 250,
        evidence.frame_timestamp_ms - 500,
        evidence.frame_timestamp_ms + 500,
        evidence.frame_timestamp_ms - 1000,
        evidence.frame_timestamp_ms + 1000,
    ]

    best_distance = None
    best_similarity = 0.0

    for timestamp_ms in candidate_timestamps:
        video_bytes = _extract_frame(
            video_path,
            timestamp_ms,
        )

        if not video_bytes:
            continue

        video_hash = _phash_from_image(
            video_bytes
        )

        if video_hash is None:
            continue

        distance = _hamming_distance(
            reference_hash,
            video_hash,
        )

        if best_distance is None or distance < best_distance:
            best_distance = distance
            similarity = (
                1.0
                - distance / VISUAL_HAMMING_THRESHOLD
            )
            best_similarity = max(0.0, similarity)

    if best_distance is None:
        return False, 0.0

    if best_distance <= VISUAL_HAMMING_THRESHOLD:
        return True, best_similarity

    return False, 0.0


def _calculate_visual_score(
    video_path: str,
    candidate: MovieCandidate,
) -> tuple[float, int, int]:
    """
    Return:

        visual_score
        images_checked
        visual_matches

    Visual evidence is capped so that it cannot overpower strong
    evidence-diversity/title/year signals.
    """

    evidence = _unique_evidence(candidate)

    images_checked = 0
    visual_matches = 0
    similarity_total = 0.0

    # Avoid downloading the same image repeatedly.
    seen_images: set[str] = set()

    for item in evidence:
        image_url = (
            item.image_url
            or item.thumbnail_url
        )

        if not image_url:
            continue

        if image_url in seen_images:
            continue

        seen_images.add(image_url)

        matched, similarity = _visual_similarity(
            video_path,
            item,
        )

        images_checked += 1

        if matched:
            visual_matches += 1
            similarity_total += similarity

    if visual_matches == 0:
        return 0.0, images_checked, 0

    average_similarity = (
        similarity_total / visual_matches
    )

    # Maximum visual contribution: 20 points.
    visual_score = min(
        20.0,
        visual_matches * 8.0
        + average_similarity * 8.0,
    )

    return (
        visual_score,
        images_checked,
        visual_matches,
    )


# ---------------------------------------------------------------------------
# Main verification
# ---------------------------------------------------------------------------

def verify_candidate(
    video_path: str,
    tmdb_match: TMDBMatch,
) -> VerificationResult:
    candidate = tmdb_match.candidate

    frames, sources, links = _evidence_metrics(
        candidate
    )

    evidence_score = _calculate_evidence_score(
        candidate
    )

    title_score = _calculate_title_score(
        candidate,
        tmdb_match,
    )

    year_score = _calculate_year_score(
        candidate,
        tmdb_match,
    )

    visual_score, images_checked, visual_matches = (
        _calculate_visual_score(
            video_path,
            candidate,
        )
    )

    total_score = (
        evidence_score
        + title_score
        + year_score
        + visual_score
    )

    # ---------------------------------------------------------
    # Hard evidence requirements
    # ---------------------------------------------------------

    if frames < MIN_UNIQUE_FRAMES:
        return VerificationResult(
            candidate=candidate,
            tmdb_match=tmdb_match,
            verified=False,
            score=total_score,
            evidence_score=evidence_score,
            title_score=title_score,
            year_score=year_score,
            visual_score=visual_score,
            unique_frames=frames,
            unique_sources=sources,
            unique_links=links,
            images_checked=images_checked,
            visual_matches=visual_matches,
            reason=(
                "Insufficient independent clip-frame evidence."
            ),
        )

    if sources < MIN_UNIQUE_SOURCES:
        return VerificationResult(
            candidate=candidate,
            tmdb_match=tmdb_match,
            verified=False,
            score=total_score,
            evidence_score=evidence_score,
            title_score=title_score,
            year_score=year_score,
            visual_score=visual_score,
            unique_frames=frames,
            unique_sources=sources,
            unique_links=links,
            images_checked=images_checked,
            visual_matches=visual_matches,
            reason=(
                "Evidence does not come from enough "
                "independent sources."
            ),
        )

    if links < MIN_UNIQUE_LINKS:
        return VerificationResult(
            candidate=candidate,
            tmdb_match=tmdb_match,
            verified=False,
            score=total_score,
            evidence_score=evidence_score,
            title_score=title_score,
            year_score=year_score,
            visual_score=visual_score,
            unique_frames=frames,
            unique_sources=sources,
            unique_links=links,
            images_checked=images_checked,
            visual_matches=visual_matches,
            reason=(
                "Not enough independent result links."
            ),
        )

    # A strong title contradiction should kill the candidate.
    if title_score == 0:
        return VerificationResult(
            candidate=candidate,
            tmdb_match=tmdb_match,
            verified=False,
            score=total_score,
            evidence_score=evidence_score,
            title_score=title_score,
            year_score=year_score,
            visual_score=visual_score,
            unique_frames=frames,
            unique_sources=sources,
            unique_links=links,
            images_checked=images_checked,
            visual_matches=visual_matches,
            reason=(
                "Lens candidate title does not sufficiently "
                "match the TMDB title."
            ),
        )

    if year_score < 0:
        return VerificationResult(
            candidate=candidate,
            tmdb_match=tmdb_match,
            verified=False,
            score=total_score,
            evidence_score=evidence_score,
            title_score=title_score,
            year_score=year_score,
            visual_score=visual_score,
            unique_frames=frames,
            unique_sources=sources,
            unique_links=links,
            images_checked=images_checked,
            visual_matches=visual_matches,
            reason=(
                "Lens year conflicts with the TMDB release year."
            ),
        )

    
    # A visual match is ideal. If none exists, require a much
    # stronger combination of independent evidence.
    visual_corroborated = visual_matches >= 1

    strong_independent_fallback = (
        frames >= 3
        and sources >= 3
        and links >= 4
        and evidence_score >= 70.0
        and title_score >= 24.0
        and year_score >= 20.0
    )

    verified = (
        evidence_score >= MIN_EVIDENCE_SCORE
        and total_score >= MIN_VERIFICATION_SCORE
        and (
            visual_corroborated
            or strong_independent_fallback
        )
    )

    if verified and visual_corroborated:
        reason = (
            "Verified using independent Lens evidence, "
            "TMDB title/year consistency, and visual "
            "corroboration."
        )
    elif verified:
        reason = (
            "Verified using strong independent Lens evidence "
            "and exact TMDB title/year agreement; "
            "visual corroboration was unavailable."
        )
    else:
        reason = (
            "Evidence was not strong enough to verify "
            "the movie confidently."
        )

    return VerificationResult(
        candidate=candidate,
        tmdb_match=tmdb_match,
        verified=verified,
        score=total_score,
        evidence_score=evidence_score,
        title_score=title_score,
        year_score=year_score,
        visual_score=visual_score,
        unique_frames=frames,
        unique_sources=sources,
        unique_links=links,
        images_checked=images_checked,
        visual_matches=visual_matches,
        reason=reason,
    )


def verify_candidates(
    video_path: str,
    tmdb_matches: list[TMDBMatch],
) -> list[VerificationResult]:
    results = []

    for match in tmdb_matches:
        result = verify_candidate(
            video_path,
            match,
        )

        results.append(result)

    results.sort(
        key=lambda result: (
            result.verified,
            result.score,
            result.evidence_score,
            result.title_score,
        ),
        reverse=True,
    )

    return results


def best_verified_match(
    video_path: str,
    tmdb_matches: list[TMDBMatch],
) -> VerificationResult | None:
    results = verify_candidates(
        video_path,
        tmdb_matches,
    )

    for result in results:
        if result.verified:
            return result

    return None