# Muvy Matching Baseline

## Status

Verified baseline — September 2026.

## Acceptance thresholds

Normal matching:

- Hamming distance threshold: 14
- Offset bucket: 500 ms
- Minimum votes: 8
- Minimum margin: 1.5
- Minimum support ratio: 0.60
- Minimum temporal span: 1500 ms

Relaxed matching:

- Minimum support ratio: 0.50
- Minimum margin: 3.0
- Minimum temporal span: 5000 ms

## Verified behavior

Known movies:

- Reckless — PASS
- Interstellar — PASS
- Michael — PASS
- Enola Holmes 3 — PASS

Unknown movie:

- record test1.mp4 — correctly rejected

## Rule

Do not change matching thresholds without running the
known-movie regression tests and the unknown-movie rejection test.
