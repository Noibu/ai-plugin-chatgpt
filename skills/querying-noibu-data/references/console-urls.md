# Console URLs

Read this reference when parsing pasted console links or including Noibu destinations in reports/action confirmations. Preserve links in saved Pages, downloads and scheduled reports when relevant to the reported evidence.

The Noibu console lives at `https://console.noibu.com`. When the user pastes a console URL, parse it to extract the resource and IDs, then route to the relevant tool.

**Path shape:** `/<domainId>/<route>/<sub>?<query>` — `<domainId>` is always a UUID.

## Routes you'll see most

| URL | Resource | Notes |
|---|---|---|
| `/<domainId>/issues/<issueId>` | Single issue (default tab: `overview`) | `<issueId>` is a UUID, NOT the humanId. To call `noibu_get_error`, first call `noibu_search_errors` filtered by id to look up the matching `humanId`. |
| `/<domainId>/issues/<issueId>/<tab>` | Issue with tab — one of `overview`, `developer`, `issue-sessions`, `pinned-sessions` | |
| `/<domainId>/issues` | Issues list | Route to `noibu_list_priority_errors` or `noibu_search_errors`. |
| `/<domainId>/sessions/player?wspath=<wsPath>` | Single session replay | `wsPath` is URL-encoded (forward slashes → `%2F`). Decode before passing to `noibu_show_session_replay`. |
| `/<domainId>/sessions` | Sessions list | Route to `noibu_search_sessions`. |
| `/<domainId>/performance/<webVitalMetric>` | Per-vital performance | `<webVitalMetric>` ∈ LCP / CLS / INP / FCP / TTFB / FID. Route to `noibu_get_page_visits` with the matching field. |
| `/<domainId>/pages/<tab>` | Pages section — `<tab>` ∈ `heat-maps`, `performance`, `issues`, `journeys` | |
| `/<domainId>/ab-tests/<testId>` | Single AB test | `<testId>` is the numeric `id`, NOT the test's `key`. Pass it as `testId` to `noibu_get_ab_test_results` for the verdict/results, or match it in `noibu_list_ab_tests` for config only. |
| `/<domainId>/ab-tests` | AB tests list | Route to `noibu_list_ab_tests`. |

**Read the query params.** When the URL has a query string (e.g. `?view=priority`, `?utm_source=...`, `?url=/checkout`, `?manuallyVerified=IMPACT`), translate each param to the equivalent filter on whichever tool you route to. The console's URL params name the filters the user is currently looking at — matching them in your tool call gives the user data on the same scope they were viewing.

## Console link policy

- **Issue links** — always use `issueUrl` from `noibu_list_priority_errors`, `noibu_search_errors`, or `noibu_get_error`. Never construct manually. If `issueUrl` is absent, do not link — surface the data without one.
- **Session replay** — always use `jazzUrl` from `noibu_show_session_replay`. Never construct manually. If `jazzUrl` is absent, do not link.
- **A/B drafts and existing tests** — after successful creation/lookup, include “Open draft in Noibu” or “View test in Noibu.” Prefer a canonical URL returned for that exact test. Otherwise use the documented `https://console.noibu.com/<domain UUID>/ab-tests/<numeric test id>` route with the resolved domain UUID and actual returned test id. Never use the key, candidate rank, domain numId or an invented id. If only a key was returned, read the roster and match that exact key/domain to get its numeric id. Never repeat creation to obtain a link. If unresolved, return confirmed key/status and explain that the direct link is unavailable.
- **Performance metrics** — prefer a returned exact link; otherwise use `https://console.noibu.com/<domain UUID>/performance/<metric>` for a verified domain and LCP/INP/CLS/FCP/TTFB. Label it “View INP in Noibu,” for example. This is a metric overview, not a page- or time-filtered deep link. Do not invent query parameters, element ids or claim preserved filters.
- **Other destinations** — include relevant canonical URLs returned by Noibu or verified same-resource URLs from the user's context. Do not invent undocumented site-health/context/page/scan/report routes. A storefront URL is not a Noibu console link.

The [link helper](../scripts/console_links.py) validates HTTPS console destinations against the selected domain and builds only the documented A/B/performance routes above: `python <shared-skill>/scripts/console_links.py --domain-id <resolved UUID> --kind ab-test --resource <actual numeric test id>`. It makes no request and cannot verify existence/account access; preserve provenance from the actual result. Issue and replay links retain their returned-URL-only rules above; replay jazzUrl values on another supported host do not use this console-only helper.

Links are navigation, not actions. Validate HTTPS, expected host, matching domain/resource and absence of credentials; do not expose token/secret-bearing URLs. Do not claim a link was opened or verified unless it was. A timeout is not confirmed creation: reconcile existing objects before returning a draft confirmation/link.
