# Auth API surface (current state — 2026-07-13 cleanup)


1. **Surface upstream state in the primary endpoint.** If endpoint A calls upstream and the response already contains fields X/Y/Z that a future endpoint B would re-fetch, add X/Y/Z to A's blueprint response now. TIS did this on its own — `queryKxrw` returns `xkgzszOne` (round config) which the bid-panel endpoint would otherwise need a separate `queryYxkc` call for. Always check the upstream response first; don't invent a new "clean" endpoint when the dirty one already has the data.
2. **Cache semantically-stable upstream responses.** The "current TIS active term" (`p_dqxn`/`p_dqxq`) does not change during a session. Cache it for the session lifetime (5 min is a safe default). Detect the same pattern for any other upstream endpoint that returns session-stable state.

Failing these rules produces a UI that works on a warm session cache but blows the rate limit on cold start.
