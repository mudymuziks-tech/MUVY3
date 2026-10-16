from __future__ import annotations

import io
import os
from pathlib import Path

import cv2
import numpy as np
import requests
from dotenv import load_dotenv


load_dotenv()


SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

SERPAPI_IMAGE_URL = "https://serpapi.com/image"
SERPAPI_SEARCH_URL = "https://serpapi.com/search"

MAX_UPLOAD_BYTES = 500 * 1024


class LensDiscoveryError(Exception):
    """Raised when Google Lens discovery fails."""


def _require_api_key() -> str:
    if not SERPAPI_API_KEY:
        raise LensDiscoveryError(
            "SERPAPI_API_KEY is not configured in .env"
        )

    return SERPAPI_API_KEY


def _encode_frame(frame) -> bytes:
    """
    Encode an OpenCV frame as a JPEG small enough for SerpApi.
    """

    quality = 90

    while quality >= 40:
        success, encoded = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, quality],
        )

        if not success:
            raise LensDiscoveryError(
                "Failed to encode video frame as JPEG."
            )

        data = encoded.tobytes()

        if len(data) <= MAX_UPLOAD_BYTES:
            return data

        quality -= 10

    raise LensDiscoveryError(
        "Could not compress frame below the 500 KB upload limit."
    )


def extract_frame(
    video_path: str,
    timestamp_ms: int,
) -> bytes:
    """
    Extract one video frame and return it as JPEG bytes.
    """

    path = Path(video_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Video file not found: {path}"
        )

    capture = cv2.VideoCapture(str(path))

    if not capture.isOpened():
        raise LensDiscoveryError(
            f"Could not open video: {path}"
        )

    try:
        capture.set(
            cv2.CAP_PROP_POS_MSEC,
            timestamp_ms,
        )

        success, frame = capture.read()

        if not success or frame is None:
            raise LensDiscoveryError(
                f"Could not extract frame at "
                f"{timestamp_ms} ms."
            )

        return _encode_frame(frame)

    finally:
        capture.release()


def discover_image(image_bytes: bytes) -> dict:
    """Run Google Lens on an uploaded still image."""
    image = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    if image is None:
        raise LensDiscoveryError("Uploaded image could not be decoded.")

    image_id = upload_image(_encode_frame(image))
    return search_lens(image_id, search_type="all")


def upload_image(image_bytes: bytes) -> str:
    """
    Upload an image to SerpApi and return its temporary image ID.
    """

    api_key = _require_api_key()

    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise LensDiscoveryError(
            "Image exceeds SerpApi's 500 KB upload limit."
        )

    try:
        response = requests.post(
            SERPAPI_IMAGE_URL,
            params={
                "api_key": api_key,
            },
            files={
                "image": (
                    "frame.jpg",
                    io.BytesIO(image_bytes),
                    "image/jpeg",
                )
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise LensDiscoveryError(
            f"SerpApi image upload failed: {exc}"
        ) from exc

    if response.status_code != 200:
        raise LensDiscoveryError(
            f"SerpApi image upload returned "
            f"HTTP {response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    if "error" in data:
        raise LensDiscoveryError(
            f"SerpApi image upload error: "
            f"{data['error']}"
        )

    image_id = data.get("image_id")

    if not image_id:
        raise LensDiscoveryError(
            "SerpApi did not return an image_id."
        )

    return image_id


def search_lens(
    image_id: str,
    search_type: str = "all",
) -> dict:
    """
    Search Google Lens using a SerpApi image ID.
    """

    api_key = _require_api_key()

    if search_type not in {
        "all",
        "exact_matches",
        "visual_matches",
    }:
        raise ValueError(
            "search_type must be one of: "
            "all, exact_matches, visual_matches"
        )

    try:
        response = requests.get(
            SERPAPI_SEARCH_URL,
            params={
                "engine": "google_lens",
                "image_id": image_id,
                "type": search_type,
                "api_key": api_key,
            },
            timeout=45,
        )
    except requests.RequestException as exc:
        raise LensDiscoveryError(
            f"Google Lens request failed: {exc}"
        ) from exc

    if response.status_code != 200:
        raise LensDiscoveryError(
            f"Google Lens returned HTTP "
            f"{response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    if "error" in data:
        raise LensDiscoveryError(
            f"Google Lens error: {data['error']}"
        )

    return data


def discover_frame(
    video_path: str,
    timestamp_ms: int,
) -> dict:
    """
    Extract one frame, upload it, and search Google Lens.

    This function intentionally returns the raw Lens response.
    Candidate extraction will be implemented separately.
    """

    frame = extract_frame(
        video_path,
        timestamp_ms,
    )

    image_id = upload_image(frame)

    return search_lens(
        image_id,
        search_type="all",
    )