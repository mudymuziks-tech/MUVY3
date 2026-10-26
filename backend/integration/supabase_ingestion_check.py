"""Opt-in integration checks for staged Supabase fingerprint ingestion.

This file is intentionally outside pytest's default discovery patterns. Run it
by explicit path only, against a disposable Supabase project.
"""

from __future__ import annotations

import os
import re
import uuid
from urllib.parse import urlparse
import warnings

import pytest


def _make_supabase_client(supabase_url: str, supabase_key: str):
    """Build a client with the supported httpx configuration interface."""
    import httpx
    from supabase import ClientOptions, create_client

    http_client = httpx.Client(
        timeout=httpx.Timeout(120),
        verify=True,
        follow_redirects=True,
        http2=True,
    )
    return (
        create_client(
            supabase_url,
            supabase_key,
            options=ClientOptions(httpx_client=http_client),
        ),
        http_client,
    )


def test_supabase_client_uses_current_httpx_configuration():
    client, http_client = _make_supabase_client(
        "https://example.supabase.co",
        "integration-test-dummy-key",
    )
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            client.table("movies")
            client.storage.from_("integration-test-bucket")

        deprecated_timeout_verify = [
            warning
            for warning in caught
            if "parameter is deprecated" in str(warning.message)
            and ("timeout" in str(warning.message) or "verify" in str(warning.message))
        ]
        assert not deprecated_timeout_verify
    finally:
        http_client.close()


def _configured_supabase(monkeypatch):
    """Validate explicit disposable-project consent before creating a client."""
    if os.getenv("MUVY_RUN_SUPABASE_INGESTION_INTEGRATION") != "1":
        pytest.fail(
            "Set MUVY_RUN_SUPABASE_INGESTION_INTEGRATION=1 to opt in to the "
            "disposable Supabase integration tests."
        )

    project_ref = os.getenv("MUVY_DISPOSABLE_SUPABASE_PROJECT_REF", "").strip()
    confirmation = os.getenv("MUVY_CONFIRM_DISPOSABLE_SUPABASE_PROJECT", "").strip()
    if not project_ref or confirmation != project_ref:
        pytest.fail(
            "Set MUVY_DISPOSABLE_SUPABASE_PROJECT_REF and explicitly confirm "
            "the same disposable project with "
            "MUVY_CONFIRM_DISPOSABLE_SUPABASE_PROJECT."
        )
    if not re.fullmatch(r"[a-z0-9]{20}", project_ref):
        pytest.fail("The disposable Supabase project ref has an unexpected format.")

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_KEY", "").strip()
    parsed_url = urlparse(supabase_url)
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != f"{project_ref}.supabase.co"
        or not supabase_key
    ):
        pytest.fail(
            "SUPABASE_URL must point to the explicitly confirmed hosted project "
            "and SUPABASE_KEY must contain its service-role key."
        )

    # Imports are delayed until after pytest has set PYTEST_CURRENT_TEST and
    # after the safety checks, so app.db.supabase cannot load backend/.env.
    import audio_fingerprint
    import matcher.matcher as video_matcher

    client, http_client = _make_supabase_client(supabase_url, supabase_key)
    monkeypatch.setattr(video_matcher, "get_supabase_client", lambda: client)
    monkeypatch.setattr(audio_fingerprint, "get_supabase_client", lambda: client)
    return (
        client,
        http_client,
        video_matcher.FingerprintDB,
        audio_fingerprint.AudioFingerprintDB,
    )


@pytest.fixture
def disposable_movie(monkeypatch):
    client, http_client, video_db_class, audio_db_class = _configured_supabase(monkeypatch)
    movie_id = f"muvy-it-{uuid.uuid4().hex}"

    created = False
    try:
        existing = (
            client.table("movies")
            .select("id")
            .eq("id", movie_id)
            .execute()
            .data
        )
        if existing:
            pytest.fail("Generated integration movie ID already exists; refusing to continue.")

        client.table("movies").insert(
            {"id": movie_id, "title": "MUVY disposable ingestion integration test"}
        ).execute()
        created = True
        yield client, movie_id, video_db_class(), audio_db_class()
    finally:
        # Migration 001 and 004 foreign keys cascade from this unique test-only
        # movie to active fingerprints, runs, and any remaining staging rows.
        try:
            if created:
                client.table("movies").delete().eq("id", movie_id).execute()
        finally:
            http_client.close()


def _stored_rows(client, table: str, movie_id: str) -> list[tuple[int, int]]:
    rows = (
        client.table(table)
        .select("hash,timestamp_ms")
        .eq("movie_id", movie_id)
        .execute()
        .data
        or []
    )
    return sorted((int(row["hash"]), int(row["timestamp_ms"])) for row in rows)


def _fingerprints(movie_id: str, rows: list[tuple[int, int]]) -> list[dict]:
    return [
        {"hash": hash_value, "movie_id": movie_id, "timestamp_ms": timestamp}
        for hash_value, timestamp in rows
    ]


def _publish(db, movie_id: str, rows: list[tuple[int, int]]) -> int:
    ingestion_id = str(uuid.uuid4())
    db.create_ingestion(ingestion_id, movie_id)
    fingerprints = _fingerprints(movie_id, rows)
    db.stage_many(ingestion_id, fingerprints)
    assert db.complete_ingestion(ingestion_id, movie_id) == len(rows)
    assert db.finalize_ingestion(ingestion_id, movie_id) == len(rows)
    return len(rows)


def test_video_publication_replaces_only_video_fingerprints(disposable_movie):
    client, movie_id, video_db, _audio_db = disposable_movie
    client.table("fingerprints").insert(
        _fingerprints(movie_id, [(101, 1000)])
    ).execute()
    client.table("audio_fingerprints").insert(
        _fingerprints(movie_id, [(201, 2000)])
    ).execute()

    assert _publish(video_db, movie_id, [(102, 1100), (103, 1600)]) == 2

    assert _stored_rows(client, "fingerprints", movie_id) == [(102, 1100), (103, 1600)]
    assert _stored_rows(client, "audio_fingerprints", movie_id) == [(201, 2000)]


def test_audio_publication_replaces_only_audio_fingerprints(disposable_movie):
    client, movie_id, _video_db, audio_db = disposable_movie
    client.table("fingerprints").insert(
        _fingerprints(movie_id, [(301, 3000)])
    ).execute()
    client.table("audio_fingerprints").insert(
        _fingerprints(movie_id, [(401, 4000)])
    ).execute()

    assert _publish(audio_db, movie_id, [(402, 4100), (403, 4600)]) == 2

    assert _stored_rows(client, "audio_fingerprints", movie_id) == [(402, 4100), (403, 4600)]
    assert _stored_rows(client, "fingerprints", movie_id) == [(301, 3000)]


@pytest.mark.parametrize("modality", ["video", "audio"])
def test_staging_failure_preserves_active_fingerprints(disposable_movie, modality):
    client, movie_id, video_db, audio_db = disposable_movie
    table = "fingerprints" if modality == "video" else "audio_fingerprints"
    db = video_db if modality == "video" else audio_db
    original = [(501, 5000)] if modality == "video" else [(601, 6000)]
    client.table(table).insert(_fingerprints(movie_id, original)).execute()

    ingestion_id = str(uuid.uuid4())
    db.create_ingestion(ingestion_id, movie_id)
    db.stage_many(ingestion_id, _fingerprints(movie_id, [(502, 5100)]))

    # NULL violates the staging table's NOT NULL timestamp constraint. The RPC
    # must fail, and the run is failed without ever publishing its partial set.
    with pytest.raises(Exception):
        db.stage_many(ingestion_id, _fingerprints(movie_id, [(503, None)]))
    db.fail_ingestion(ingestion_id, movie_id)

    assert _stored_rows(client, table, movie_id) == original
    run = (
        client.table("fingerprint_ingestion_runs")
        .select("status")
        .eq("ingestion_id", ingestion_id)
        .single()
        .execute()
        .data
    )
    assert run["status"] == "failed"
