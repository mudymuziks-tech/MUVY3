from types import SimpleNamespace

from discovery import pipeline
from discovery.lens import LensDiscoveryError


def test_discovery_pipeline_returns_only_explicitly_verified_candidate(monkeypatch):
    candidate = object()
    verification = SimpleNamespace(
        status="verified",
        reason="visual evidence corroborated",
    )
    monkeypatch.setattr(pipeline, "_sample_timestamps", lambda _: [1000, 5000, 9000])
    monkeypatch.setattr(pipeline, "discover_frame", lambda _path, timestamp: {"timestamp": timestamp})
    monkeypatch.setattr(pipeline, "extract_candidates", lambda _results: [candidate])
    monkeypatch.setattr(pipeline, "resolve_candidates", lambda _candidates: [object()])
    monkeypatch.setattr(
        pipeline,
        "verify_candidates",
        lambda *_args, **_kwargs: [verification],
    )

    result = pipeline.discover_video("clip.mp4")

    assert result.status == "verified"
    assert result.verification is verification


def test_discovery_pipeline_keeps_likely_candidate_unverified(monkeypatch):
    verification = SimpleNamespace(
        status="likely",
        verified=False,
        reason="visual evidence unavailable",
    )
    monkeypatch.setattr(pipeline, "_sample_timestamps", lambda _: [1000, 5000])
    monkeypatch.setattr(pipeline, "discover_frame", lambda *_args: {})
    monkeypatch.setattr(pipeline, "extract_candidates", lambda _results: [object()])
    monkeypatch.setattr(pipeline, "resolve_candidates", lambda _candidates: [object()])
    monkeypatch.setattr(
        pipeline,
        "verify_candidates",
        lambda *_args, **_kwargs: [verification],
    )

    result = pipeline.discover_video("clip.mp4")

    assert result.status == "likely"
    assert result.verification.verified is not True


def test_discovery_pipeline_handles_failed_external_searches(monkeypatch):
    def fail_search(*_args):
        raise LensDiscoveryError("service unavailable")

    monkeypatch.setattr(pipeline, "_sample_timestamps", lambda _: [1000, 5000])
    monkeypatch.setattr(pipeline, "discover_frame", fail_search)

    result = pipeline.discover_video("clip.mp4")

    assert result.status == "inconclusive"
    assert result.verification is None
    assert "unavailable" in result.reason
