---
name: store-pulse
description: Show a Noibu store-health snapshot with KPI cards, a purchase funnel, and actions to save a private dashboard, export, or schedule recurring reports; optionally include products and traffic channels.
---

# Store Pulse

- Read [shared query guidance](../querying-noibu-data/SKILL.md) and [runtime/actions](../querying-noibu-data/references/chatgpt-runtime.md). Use skill `store-pulse`; resolve the store and saved context.
- Fetch fresh data for each invocation. Default to rolling last 24 hours versus preceding 24 hours, using one anchor; honor requested windows.
- Follow [snapshot queries](references/snapshot-queries.md):
  - Fetch sessions, bounce/conversion, completed-order revenue and completed-order count for both windows; keep currencies separate.
  - Derive engagement = 1 − bounce, AOV = completed-order revenue ÷ completed orders, and RPS = completed-order revenue ÷ sessions. Undefined denominators remain unknown.
  - Build cumulative funnel depths from distinct sessions, not event sums; account for express checkout/missing intermediate events.
- Query products/channels/paid traffic only when requested, using [optional blocks](references/optional-blocks.md).

## Report and actions

- Lead with one or two measured conclusions, then use the packaged [inline presentation](../querying-noibu-data/references/presentation.md).
- Show light unfilled Sessions/Engagement/Conversion/AOV/RPS groups and a connected five-stage funnel with rates against total sessions, comparison context and exact counts.
- Rate deltas use pp; volume/value deltas use relative %, undefined when prior is zero. Explicit measured downward changes use orange; captions remain separate.
- Place **Save as Live Site** below all dashboard content, before supported investigation opportunities; keep Pages/download/scheduling in the final section.
- Site saves use [persistent dashboards](../querying-noibu-data/references/connected-dashboard.md) and [permission preflight](../querying-noibu-data/references/site-permissions.md): reuse the private Site, preserve domain/window/optional blocks, verify totals and persisted/hosted reads, and offer weekly updates with confirmed details. Do not require a spreadsheet or visitor connection for saved-data mode.
- **Schedule report** uses [shared connected delivery](../querying-noibu-data/references/scheduling-delivery.md). Store Pulse alone adds **Daily** to Weekly/Every 2 weeks/Monthly; weekly remains initially selected.
- Daily means every calendar day, including weekends, at confirmed local time/IANA timezone; no weekday/first-run/monthday fields. Recurrence does not change source windows: fetch fresh last 24 hours versus preceding 24 hours, or the confirmed alternative, on every run.
