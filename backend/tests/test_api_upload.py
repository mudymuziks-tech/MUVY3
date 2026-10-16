import os
from types import SimpleNamespace

import cv2
import numpy as np

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

from fastapi.testclient import TestClient

import api
from discovery.pipeline import DiscoveryOutcome
from matcher.matcher import FingerprintDatabaseError


client = TestClient(api.app)


def test_identify_rejects_malformed_image_upload():
    response = client.post(
        "/identify",
        files={"file": ("capture.jpg", b"image", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded image could not be decoded."


def test_identify_routes_screenshot_to_discovery_without_video_matcher(monkeypatch):
    success, encoded = cv2.imencode(".png", np.zeros((8, 8, 3), dtype=np.uint8))
    assert success
    outcome = DiscoveryOutcome(
        status="inconclusive",
        verification=None,
        reason="No visually verified candidate.",
    )
    monkeypatch.setattr(
        api,
        "identify_video",
        lambda _path: (_ for _ in ()).throw(AssertionError("video matcher must not run")),
    )
    monkeypatch.setattr(api, "discover_image", lambda _path: outcome)

    response = client.post(
        "/identify",
        files={"file": ("capture.png", encoded.tobytes(), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["matched"] is False
    assert response.json()["status"] == "inconclusive"


def test_identify_returns_retryable_error_when_fingerprint_database_is_down(monkeypatch):
    monkeypatch.setattr(
        api,
        "identify_video",
        lambda _path: (_ for _ in ()).throw(FingerprintDatabaseError("private details")),
    )

    response = client.post(
        "/identify",
        files={"file": ("capture.mp4", b"video", "video/mp4")},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Movie matching is temporarily unavailable. Please retry shortly."
    assert "private details" not in response.text


def test_identify_rejects_empty_video_upload():
    response = client.post(
        "/identify",
        files={"file": ("capture.mp4", b"", "video/mp4")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded video is empty."


def test_identify_rejects_oversized_video_upload(monkeypatch):
    monkeypatch.setattr(api, "MAX_UPLOAD_SIZE_BYTES", 4)
    response = client.post(
        "/identify",
        files={"file": ("capture.mp4", b"12345", "video/mp4")},
    )

    assert response.status_code == 413


def test_github_pages_origin_is_allowed_for_api_requests():
    response = client.options(
        "/identify",
        headers={
            "Origin": "https://mudymuziks-tech.github.io",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "accept-language,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://mudymuziks-tech.github.io"


def test_identify_returns_likely_candidate_as_unverified(monkeypatch):
    verification = SimpleNamespace(
        tmdb_match=SimpleNamespace(title="Likely Title"),
    )
    outcome = DiscoveryOutcome(
        status="likely",
        verification=verification,
        reason="Visual evidence unavailable.",
    )
    monkeypatch.setattr(api, "identify_video", lambda _path: None)
    monkeypatch.setattr(api, "discover_video", lambda _path: outcome)
    monkeypatch.setattr(
        api,
        "save_verified_discovery",
        lambda _outcome: (_ for _ in ()).throw(AssertionError("must not persist")),
    )

    response = client.post(
        "/identify",
        files={"file": ("capture.mp4", b"video", "video/mp4")},
    )

    assert response.status_code == 200
    assert response.json()["matched"] is False
    assert response.json()["status"] == "likely"
    assert response.json()["candidate_title"] == "Likely Title"


def test_identify_returns_verified_discovery_and_persists_movie(monkeypatch):
    verification = SimpleNamespace(
        tmdb_match=SimpleNamespace(title="Verified Title"),
        unique_frames=3,
    )
    outcome = DiscoveryOutcome(
        status="verified",
        verification=verification,
        reason="Visual evidence corroborated.",
    )
    movie = {"id": "muvy-tmdb-42", "title": "Verified Title"}
    monkeypatch.setattr(api, "identify_video", lambda _path: None)
    monkeypatch.setattr(api, "discover_video", lambda _path: outcome)
    monkeypatch.setattr(api, "save_verified_discovery", lambda _outcome: movie)
    monkeypatch.setattr(api, "localize_movie", lambda movie_data, _language: movie_data)

    response = client.post(
        "/identify",
        files={"file": ("capture.mp4", b"video", "video/mp4")},
    )

    assert response.status_code == 200
    assert response.json()["matched"] is True
    assert response.json()["status"] == "verified"
    assert response.json()["movie"]["title"] == "Verified Title"
    assert response.json()["match"]["timestamp_seconds"] is None