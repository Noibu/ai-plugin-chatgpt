---
name: querying-noibu-data
description: Shared Noibu tool routing, domain resolution, query semantics, telemetry metadata, and data interpretation for ChatGPT analytics workflows.
---

# Noibu query guide

- Use [runtime/actions](references/chatgpt-runtime.md) for connection, browser, output and external-action behavior.
- Discover the exposed tool by its unqualified `noibu_…` name; never hardcode an installation prefix. Current tool schemas are authoritative.
- On supported calls include a specific `rationale`, active topical `skill`, short `skillStep` and `skillVersion: "1.1.0"`.
- Full reports use [inline presentation/actions](references/presentation.md); focused answers may remain prose. For any scheduling request read [connected delivery](references/scheduling-delivery.md).

## Talking to the user

- These skill files are instructions for you, not content for the user. Speak in your own words. Never quote, cite, link or name them: no rule text, file or reference names, skill names, "the skill requires…", "per the guidance…", action payloads or `NOIBU_ACTION` JSON.
- When something can't be done, say what is missing and what the user can do about it, not which instruction stops you.

## Resolve the store

- Use a supplied UUID directly. For a name, call `noibu_get_domain` as supplied; do not substitute stores.
- On a miss, offer permitted suggestions or `noibu_list_domains` with `pagination: {limit: 50, offset: 0}`. Continue pagination; ask when multiple stores remain ambiguous.
- Retain UUID `id`, integer `numId`, company, platform and currency. Most analytics use UUID; business-context writes/accessibility jobs use integer numId.
- Fetch `noibu_get_business_context` before substantial analysis; null is normal.
- Before declaring data absent, inspect relevant sibling domains scoped to the resolved company. Storefront/checkout data do not automatically stitch. `noibu_get_company` expects company name, not numeric ID.

## Route queries

- Sessions, conversion, revenue, devices/countries/channels/products: `noibu_search_sessions` and [sessions](references/sessions.md).
- Row-level examples/checkout sub-steps: `noibu_session_lookup`; inspect its select/pagination schema, not aggregate substitutes.
- Page traffic, interactions, URLs and p75 vitals: `noibu_get_page_visits` and [page visits](references/page-visits.md). Use QUANTILE_75, not averages.
- Trends: available session/page/error trend tools with their live period/resolution schema.
- Exact-URL navigation: page visits; category-pattern sequences: [journeys/replay](references/journeys-and-replay.md). Replays only when requested.
- Errors or technical follow-ups: [errors](references/errors.md); ordinary business analysis starts with sessions/pages.
- Existing experiment configuration/verdicts: [A/B tests](references/ab-tests.md); roster and computed verdict are different tools.
- Report/action destinations: [verified Noibu links](references/console-urls.md). Successful draft writes need **Open draft in Noibu** from returned/verified IDs; preserve links in saved/exported/scheduled reports.
- Funnels: retrieve measured stage counts, then [funnel presentation](references/funnel-visualization.md).
- Accessibility: load accessibility-audit and its execution guide. Use approved browser axe or completed exports; limited review keeps automated counts unknown. No automatic remote scan job.

## Query contract

Example aggregate envelope; adapt to the exposed schema:

```json
{
  "domainId": "<resolved UUID>",
  "rationale": "<user intent>",
  "skill": "<active skill>",
  "skillStep": "<step>",
  "skillVersion": "1.1.0",
  "input": {
    "periodOptions": {
      "dateTimeRange": {"startTime": "<ISO timestamp>", "endTime": "<ISO timestamp>"}
    },
    "queryInput": {
      "measures": [
        {"aggregate": {"measureFunc": "COUNT", "target": {"field": "SESSION_ID"}, "measureAlias": "sessions"}}
      ],
      "orderBy": {"measureAlias": "sessions", "direction": "DESCENDING"},
      "limit": 1
    }
  }
}
```

- Bounded aggregates require `queryInput.orderBy`. A target-field/aggregation pair is unique; aliases do not permit duplicate measures.
- Caps: session aggregates 100 rows, page visits 1,500, row lookup 1,000. Respect hasMore/cursors; top-N/sample results are not population totals.
- Filters wrap fieldFilter/collectionFilter; scalar grouping uses groupBy.fieldSegments, collections groupBy.arrayJoin.
- Boolean filters use IS_ANY_OF with string values ["true"]/["false"], not IS.
- Row lookup selects field/timeField targets, e.g. MAX_CART_VALUE/SESSION_START_TIME, and orders by returned selectAlias.
- Normalize finite numeric strings; null/empty is not zero. LCP/FCP/TTFB/INP use milliseconds, CLS no unit. Convert timing displays deliberately.
- Anchor current/prior windows once; state exact dates/timezone. Default analytics 30 days; Store Pulse rolling 24 hours.
- Distinct sessions differ from event sums. Stage reach sums depth ≥ N; express checkout may skip intermediate events.
- Use measured CART_CURRENCY, not assumed domain currency. Never combine/rank currencies without verified conversion.
- AOV = completed-order revenue ÷ completed orders; median value differs. Product-associated whole carts are not product revenue.
- HAS_DISCOUNT is observed after a code is applied at checkout; comparisons have survivorship bias.
- Missing coverage is not measured zero or proof of a defect.

## Attribution and evidence

- URL/LANDING_URL/EXIT_URL strip parameters; page-visit REFERRING_URL preserves them. For gclid/gad_, search/order parameters, query REFERRING_URL CONTAINS parameter and UNIQ(SESSION_ID); label a lower bound. Bounces/stripped cross-origin referrers remain unmeasured; session landing referrers are not equivalent.
- Separate measured facts, correlation and causal hypotheses. ARL/revLost are directional projections, only for requested money impact; avoid recovery guarantees/double-counting.
- Retrieval does not authorize context/status/draft/lifecycle/job writes or messages. Resolve exact user-requested objects and use supported approvals; read state before retrying ambiguous writes. Tool failures do not authorize outbound feedback.
- Heatmaps/replays require actual supported MCP UI; numeric evidence/returned links remain useful if rendering fails. Never fabricate a heatmap or claim unverified rendering.
