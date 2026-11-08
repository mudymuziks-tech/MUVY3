from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2

from .candidates import MovieCandidate, extract_candidates
from .lens import LensDiscoveryError, discover_frame, discover_image as lens_discover_image
from .resolver import TMDBMatch, resolve_candidates
from .visual_verifier import VerificationResult, verify_candidates


logger = logging.getLogger(__name__)

MAX_DISCOVERY_FRAMES = 3
MAX_CANDIDATES_TO_RESOLVE = 8
MAX_CANDIDATES_TO_VERIFY = 5


@dataclass
class DiscoveryOutcome:
    status: Literal["verified", "likely", "inconclusive"]
    verification: VerificationResult | None
    reason: str


def _sample_timestamps(video_path: str) -> list[int]:
    capture = cv2.VideoCapture(str(Path(video_path)))
    if not capture.isOpened():
        capture.release()
        return []

    try:
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = capture.get(cv2.CAP_PROP_FPS)
        if frame_count <= 0 or fps <= 0:
            return []

        duration_ms = frame_count / fps * 1000
        return sorted({
            min(int(duration_ms * fraction), max(0, int(duration_ms) - 1))
            for fraction in (0.2, 0.5, 0.8)
        })[:MAX_DISCOVERY_FRAMES]
    finally:
        capture.release()


def _resolve_discoveries(
    media_path: str,
    frame_results: dict[int, dict],
    *,
    is_image: bool = False,
) -> DiscoveryOutcome:
    if not frame_results:
        return DiscoveryOutcome(
            status="inconclusive",
            verification=None,
            reason="Visual discovery was unavailable for this clip.",
        )

    candidates: list[MovieCandidate] = extract_candidates(frame_results)
    matches: list[TMDBMatch] = resolve_candidates(
        candidates[:MAX_CANDIDATES_TO_RESOLVE]
    )
    if not matches:
        return DiscoveryOutcome(
            status="inconclusive",
            verification=None,
            reason="No movie candidate could be resolved with enough evidence.",
        )

    results = verify_candidates(
        media_path,
        matches[:MAX_CANDIDATES_TO_VERIFY],
        require_multiple_frames=not is_image,
    )
    for result in results:
        if result.status == "verified":
            return DiscoveryOutcome(
                status="verified",
                verification=result,
                reason=result.reason,
            )

    for result in results:
        if result.status == "likely":
            return DiscoveryOutcome(
                status="likely",
                verification=result,
                reason=result.reason,
            )

    best_result = results[0] if results else None
    return DiscoveryOutcome(
        status="inconclusive",
        verification=best_result,
        reason=(
            best_result.reason
            if best_result
            else "No candidate could be visually verified."
        ),
    )


def discover_video(video_path: str) -> DiscoveryOutcome:
    """Run bounded Lens discovery and return only evidence-qualified outcomes."""
    timestamps = _sample_timestamps(video_path)
    if not timestamps:
        return DiscoveryOutcome(
            status="inconclusive",
            verification=None,
            reason="Could not sample frames for visual discovery.",
        )

    frame_results: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=MAX_DISCOVERY_FRAMES) as executor:
        futures = {
            executor.submit(discover_frame, video_path, timestamp): timestamp
            for timestamp in timestamps
        }
        for future in as_completed(futures):
            timestamp = futures[future]
            try:
                frame_results[timestamp] = future.result()
            except LensDiscoveryError:
                logger.warning("Visual discovery failed for a sampled frame.")
            except Exception:
                logger.warning("Unexpected visual discovery failure.")

    return _resolve_discoveries(video_path, frame_results)


def discover_image(image_path: str) -> DiscoveryOutcome:
    """Run Lens discovery on a screenshot and compare corroboration to that still."""
    try:
        image_bytes = Path(image_path).read_bytes()
        frame_result = lens_discover_image(image_bytes)
    except (OSError, LensDiscoveryError):
        logger.warning("Screenshot discovery was unavailable.")
        return DiscoveryOutcome(
            status="inconclusive",
            verification=None,
            reason="Screenshot discovery was unavailable for this image.",
        )
    except Exception:
        logger.exception("Unexpected screenshot discovery failure")
        return DiscoveryOutcome(
            status="inconclusive",
            verification=None,
            reason="Screenshot discovery failed.",
        )

    return _resolve_discoveries(image_path, {0: frame_result}, is_image=True)
