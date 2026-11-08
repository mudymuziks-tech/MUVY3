from matcher.matcher import QueryFrame, hamming_distance, match_clip


class FakeFingerprintDB:
    """A test database that doesn't connect to Supabase."""

    def __init__(self, rows):
        self.rows = rows

    def find_candidates(self, query_hashes, distance_threshold=14):
        return self.rows


def make_frames(count, spacing_ms=500):
    """Create predictable query frames."""
    return [
        QueryFrame(
            hash=i + 1,
            capture_time_ms=i * spacing_ms,
        )
        for i in range(count)
    ]


def make_matching_rows(frames, movie_id="movie-a"):
    """Create exact fingerprint matches at a consistent offset."""
    return [
        (
            frame.hash,
            movie_id,
            frame.capture_time_ms + 5000,
        )
        for frame in frames
    ]


def test_exact_match_is_accepted():
    frames = make_frames(10)
    db = FakeFingerprintDB(make_matching_rows(frames))

    result = match_clip(frames, db)

    assert result is not None
    assert result.movie_id == "movie-a"


def test_empty_frames_are_rejected():
    db = FakeFingerprintDB([])

    assert match_clip([], db) is None


def test_no_candidates_are_rejected():
    frames = make_frames(10)
    db = FakeFingerprintDB([])

    assert match_clip(frames, db) is None


def test_match_clip_enforces_support_ratio():
    import random

    rng = random.Random(20261020)
    hashes = [rng.getrandbits(64) for _ in range(20)]
    assert all(
        hamming_distance(hashes[i], hashes[j]) > 14
        for i in range(len(hashes))
        for j in range(i + 1, len(hashes))
    )
    frames = [
        QueryFrame(hash=value, capture_time_ms=i * 500)
        for i, value in enumerate(hashes)
    ]

    # Eleven of twenty frames (55%) support the same offset. Distinct hashes
    # prevent cross-matches, and every stored row implies exactly 5000 ms, so
    # bucket smoothing cannot increase support.
    rejected = match_clip(
        frames,
        FakeFingerprintDB(make_matching_rows(frames[:11])),
        min_votes=8,
        min_margin=1.5,
        min_support_ratio=0.60,
        relaxed_support_ratio=0.60,
    )
    assert rejected is None

    # Twelve of twenty frames (60%) meet the configured threshold.
    accepted = match_clip(
        frames,
        FakeFingerprintDB(make_matching_rows(frames[:12])),
        min_votes=8,
        min_margin=1.5,
        min_support_ratio=0.60,
        relaxed_support_ratio=0.60,
    )
    assert accepted is not None
    assert accepted.movie_id == "movie-a"
    assert accepted.votes == 12
    assert accepted.confidence == 0.60
