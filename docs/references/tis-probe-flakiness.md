# TIS probe flakiness (always retry on empty)


~1-in-4 probes return `total=0` + empty categories even when TIS is up
(CAS-side rate limit). Never trust a single probe result. Validated
pattern: 5 retries with 2–3s sleep between, only confirm a probe when
`total > 0` OR `categories` is non-empty. The same code can return 0
once and 74 the next.
