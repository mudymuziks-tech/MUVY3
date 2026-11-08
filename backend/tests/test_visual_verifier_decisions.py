
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from discovery import visual_verifier as verifier
from discovery.candidates import LensEvidence, MovieCandidate
from discovery.resolver import TMDBMatch, consolidate_tmdb_matches


def make_match():
    candidate = SimpleNamespace(
        title="Reckless",
        year=2026,
        evidence=[],
    )

    tmdb_match = SimpleNamespace(
        candidate=candidate,
        title="Reckless",
        release_date="2026-02-07",
    )

    return candidate, tmdb_match


@pytest.fixture
def stub_scoring(monkeypatch):
    def configure(
        *,
        frames=3,
        sources=3,
        links=4,
        evidence_score=70.0,
        title_score=30.0,
        year_score=20.0,
        visual_score=0.0,
        images_checked=4,
        visual_comparisons=0,
        visual_matches=0,
    ):
        monkeypatch.setattr(
            verifier,
            "_evidence_metrics",
            lambda candidate: (frames, sources, links),
        )
        monkeypatch.setattr(
            verifier,
            "_calculate_evidence_score",
            lambda candidate: evidence_score,
        )
        monkeypatch.setattr(
            verifier,
            "_calculate_title_score",
            lambda candidate, match: title_score,
        )
        monkeypatch.setattr(
            verifier,
            "_calculate_year_score",
            lambda candidate, match: year_score,
        )
        monkeypatch.setattr(
            verifier,
            "_calculate_visual_score",
            lambda path, candidate: (
                visual_score,
                images_checked,
                visual_matches,
                visual_comparisons,
            ),
        )

    return configure


def test_visual_mismatch_never_counts_as_verified(
    stub_scoring,
):
    stub_scoring(images_checked=4, visual_comparisons=4)
    _, match = make_match()

    result = verifier.verify_candidate("unused.mp4", match)

    assert result.verified is False
    assert result.status == "inconclusive"
    assert result.visual_matches == 0
    assert "did not corroborate" in result.reason


def test_strong_evidence_without_visual_images_is_only_likely(
    stub_scoring,
):
    stub_scoring(images_checked=0)
    _, match = make_match()

    result = verifier.verify_candidate("unused.mp4", match)

    assert result.verified is False
    assert result.status == "likely"
    assert "not verified" in result.reason


def test_failed_visual_download_is_likely_not_a_visual_mismatch(
    stub_scoring,
):
    stub_scoring(images_checked=4, visual_comparisons=0)
    _, match = make_match()

    result = verifier.verify_candidate("unused.mp4", match)

    assert result.verified is False
    assert result.status == "likely"
    assert result.images_checked == 4
    assert result.visual_comparisons == 0


def test_visual_match_can_support_candidate(stub_scoring):
    stub_scoring(
        frames=2,
        sources=2,
        links=2,
        evidence_score=50.0,
        visual_score=8.0,
        visual_matches=1,
    )
    _, match = make_match()

    result = verifier.verify_candidate("unused.mp4", match)

    assert result.verified is True
    assert result.visual_matches == 1
    assert "visual corroboration" in result.reason


@pytest.mark.parametrize(
    "overrides",
    [
        {"frames": 2, "sources": 2, "links": 3},
        {"frames": 3, "sources": 2, "links": 4},
        {"frames": 3, "sources": 3, "links": 3},
        {"frames": 3, "sources": 3, "links": 4,
         "evidence_score": 60.0},
        {"frames": 3, "sources": 3, "links": 4,
         "title_score": 15.0},
        {"frames": 3, "sources": 3, "links": 4,
         "year_score": 8.0},
    ],
)
def test_weak_evidence_without_visual_match_is_rejected(
    stub_scoring,
    overrides,
):
    stub_scoring(**overrides)
    _, match = make_match()

    result = verifier.verify_candidate("unused.mp4", match)

    assert result.verified is False


def test_consolidate_tmdb_matches_merges_multilingual_titles_for_same_movie():
    english = TMDBMatch(
        candidate=MovieCandidate(
            title="Reckless",
            year=2026,
            evidence=[
                LensEvidence(
                    title="Reckless",
                    source="google lens",
                    link="https://example.com/reckless-english",
                    frame_timestamp_ms=1200,
                    position=1,
                )
            ],
        ),
        tmdb_id=42,
        title="Reckless",
        release_date="2026-02-07",
        score=92.0,
        tmdb_result={"title": "Reckless", "release_date": "2026-02-07"},
    )

    portuguese = TMDBMatch(
        candidate=MovieCandidate(
            title="Ajuste de Contas",
            year=2026,
            evidence=[
                LensEvidence(
                    title="Ajuste de Contas",
                    source="google lens",
                    link="https://example.com/ajuste-de-contas",
                    frame_timestamp_ms=2200,
                    position=2,
                )
            ],
        ),
        tmdb_id=42,
        title="Reckless",
        release_date="2026-02-07",
        score=88.0,
        tmdb_result={"title": "Reckless", "release_date": "2026-02-07"},
    )

    consolidated = consolidate_tmdb_matches([english, portuguese])

    assert len(consolidated) == 1
    assert consolidated[0].tmdb_id == 42
    assert consolidated[0].title == "Reckless"
    assert len(consolidated[0].candidate.evidence) == 2
    assert {item.link for item in consolidated[0].candidate.evidence} == {
        "https://example.com/reckless-english",
        "https://example.com/ajuste-de-contas",
    }


def test_unique_evidence_deduplicates_tracking_variants_and_same_video_results():
    candidate = MovieCandidate(
        title="Reckless",
        evidence=[
            LensEvidence(
                title="Reckless",
                source="youtube",
                link="https://www.youtube.com/watch?v=abcdef123456&feature=share&si=abc",
                frame_timestamp_ms=1200,
                image_url="https://img.example.com/frame.jpg?utm_source=foo",
                thumbnail_url="https://img.example.com/frame.jpg?utm_source=foo",
            ),
            LensEvidence(
                title="Reckless",
                source="youtube",
                link="https://youtube.com/watch?v=abcdef123456",
                frame_timestamp_ms=1200,
                image_url="https://img.example.com/frame.jpg",
                thumbnail_url="https://img.example.com/frame.jpg",
            ),
        ],
    )

    unique = verifier._unique_evidence(candidate)

    assert len(unique) == 1


def test_visual_similarity_uses_nearby_frames_for_known_clip(monkeypatch):
    clip_path = Path("tests/fixtures/small_clips/reckless.mp4")
    evidence = LensEvidence(
        title="Reckless",
        source="google lens",
        link="https://example.com/reckless",
        frame_timestamp_ms=1000,
        image_url="https://example.com/reckless.jpg",
    )

    def fake_download(_):
        return b"reference"

    def fake_phash(bytes_data):
        if bytes_data == b"reference":
            return 0b11110000
        if bytes_data == b"nearby":
            return 0b11110001
        return 0b00000000

    def fake_extract(video_path, timestamp_ms):
        if timestamp_ms == 1000:
            return b"wrong"
        if timestamp_ms in {750, 1000, 1250, 1500, 2000}:
            return b"nearby"
        return None

    monkeypatch.setattr(verifier, "_download_image", fake_download)
    monkeypatch.setattr(verifier, "_phash_from_image", fake_phash)
    monkeypatch.setattr(verifier, "_extract_frame", fake_extract)

    matched, score, compared = verifier._visual_similarity(str(clip_path), evidence)

    assert matched is True
    assert compared is True
    assert score > 0.0


def test_visual_similarity_rejects_unknown_clip(monkeypatch):
    clip_path = Path("tests/fixtures/small_clips/unknown.mp4")
    evidence = LensEvidence(
        title="Unrelated movie",
        source="google lens",
        link="https://example.com/unrelated",
        frame_timestamp_ms=1000,
        image_url="https://example.com/unrelated.jpg",
    )

    def fake_hash(data):
        if data == b"reference":
            return 0xFFFFFFFFFFFFFFFF
        return 0x0000000000000000

    monkeypatch.setattr(verifier, "_download_image", lambda _: b"reference")
    monkeypatch.setattr(verifier, "_phash_from_image", fake_hash)
    monkeypatch.setattr(
        verifier,
        "_extract_frame",
        lambda *_args, **_kwargs: b"other-frame",
    )

    matched, score, compared = verifier._visual_similarity(str(clip_path), evidence)

    assert matched is False
    assert compared is True
    assert score == 0.0
