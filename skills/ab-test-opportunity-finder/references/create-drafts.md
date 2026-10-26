# Create requested Noibu drafts

Recommendations create no account objects. A user request identifying one or more selected recommendations authorizes their DRAFT creation; review the configuration in the conversation and use the actual MCP write tool.

1. Match the requested candidate(s), domain, title, hypothesis, metric, targeting, and variations. Clarify only ambiguous choices. Read existing tests to avoid title duplicates.
2. Use `scripts/validate_candidates.py` when available, or apply its contract inline. Required success metric is ADD_TO_CART_RATE, CHECKOUT_CONVERSION_RATE, or PAGE_VIEW_TO_URL_RATE. For the page-view metric specify exactly one of pageUrl/pageGroup, using a real observed URL or configured group.
3. Up to three guardrails; they additionally support AVERAGE_ORDER_VALUE. Device targeting values are `mobile` and `other`, not `desktop`. UTM conditions use the actual utm_* parameter names and nonempty values. Leave unverified location targeting unset rather than guess its opaque schema.
4. At least two variations, exactly one current-experience control, unique names, numeric finite nonnegative splits summing to 100. Keep variations' names identical in the handoff and tool input.
5. Call `noibu_create_ab_test` with the reviewed createInput and resolved domainId plus rationale/skill metadata.
6. Return the actual created key/id and DRAFT status as returned, plus **Open draft in Noibu** following [console link guidance](../../querying-noibu-data/references/console-urls.md). Prefer the returned canonical URL; otherwise use the resolved domain UUID and actual numeric id in the documented `/ab-tests/<id>` route. When only a key is available, look up that exact key in the domain roster. Never substitute a candidate rank or create a duplicate to get a URL. If lifecycle is unconfirmed, verify it in the roster. For a timeout, reconcile existing titles before retrying or returning a creation confirmation/link.

Never call lifecycle advancement or update as part of draft creation. State that variation code must be implemented and deployed before a separate explicit start request. A stopped test is irreversible and cannot be resumed.

The current schema includes an opaque optional location field; this package does not invent its shape. Use it only after a documented schema and the chosen targeting have been verified.
