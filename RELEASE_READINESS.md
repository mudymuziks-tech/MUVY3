# MUVY Release Readiness

Updated: 2026-10-16

This ledger records evidence, not intent. A gate is not complete until its listed checks have run successfully against the intended release build and production-like services.

## Release Gates

| Gate | Status | Evidence and remaining work |
| --- | --- | --- |
| Recognition accuracy | PARTIAL | The four curated known-title regressions passed against Supabase on 2026-10-16. Proposed target: at least 95% on a representative held-out set. The current set is too small and selected to establish that target; no accuracy report with confidence intervals exists. |
| Unknown-movie rejection | PARTIAL | One matcher-level unknown clip was correctly rejected, and verifier tests reject visual mismatches. Proposed target: zero false verified matches in a representative release set; the current single unknown clip is insufficient evidence. |
| Supported input coverage | PARTIAL | API tests cover video validation and screenshot routing; screen/back-camera flows now create video clips. Screenshot Lens recognition and camera capture have not been manually exercised end to end. Audio capture has no recognition service and must not be presented as working recognition. |
| Regression testing | PASS | Full backend suite passed 29/29 on 2026-10-16, including the Supabase-backed fingerprint tests. Three dependency deprecation warnings remain; they did not fail tests. |
| Failure handling | PARTIAL | Empty, malformed, and oversized uploads have endpoint tests. Still needed: deterministic tests for TMDB/Lens timeouts, malformed provider responses, Supabase failures during matching and persistence, request cancellation, and rate limiting. |
| Security and privacy | PARTIAL | Credentials remain server-side; upload size and CORS are configured. Supabase schema, RLS policies, service-role scope, secret rotation, retention, and cross-user isolation are not verified. |
| Mobile/desktop UX | BLOCKED | Upload and capture flows were aligned in code and syntax-checked. Responsive/manual device checks, screen-reader/keyboard checks, loading/retry states, and real browser capture tests remain. |
| Production readiness | PARTIAL | GitHub Pages and the existing Render API are configured; Render `/health` and GitHub Pages CORS preflight responded successfully. Monitoring, rate limits, backups, deployment/rollback procedures, cold-start impact, and a production upload smoke test remain. |

## Initial Metrics

These are proposed goals, not measured results:

- Known-movie accuracy: at least 95% on a representative held-out test set.
- False verified matches on unknown clips: zero in the release test set.
- Supported-input completion: at least 99% under defined valid test conditions.
- Requests returning a usable success or failure outcome: at least 99%, excluding caller cancellation.
- Repeatable regression suite: 100% passing.

Report known-title accuracy and unknown-title false-positive rate separately. Include diverse scenes, trailers, alternate edits, languages, low-quality clips, similar-looking titles, and multiple clip lengths. Record sample sizes, confidence intervals, latency percentiles, and test-set provenance before treating a target as satisfied.

## Evidence From This Work

- Full backend suite: 29 passed, 3 dependency deprecation warnings.
- JavaScript syntax and whitespace checks passed after the picker changes.
- The first full-suite run timed out on Supabase; retrying the fingerprint test and then the complete suite succeeded. Treat intermittent upstream latency as an open reliability item until it is characterized under sustained runs.
- The live Render API health endpoint and GitHub Pages CORS preflight were checked on 2026-10-16. This does not validate the current uncommitted code on Render.

## Scope Decisions

The current product flow is video matching, screenshot discovery, and visually corroborated fallback. Audio recognition, account-backed identity, persistent personal libraries, TMDB Discover, and streaming availability links are not implemented end to end. They are excluded from the initial recognition MVP gate until explicitly included in a launch scope; audio must remain clearly marked unsupported meanwhile.
