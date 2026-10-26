---
name: product-analysis
description: Analyze Noibu product and collection performance, add-to-cart opportunities, and purchase friction; present an interactive priority board with investigation, dashboard, export, and scheduling actions.
---

# Product and collection performance

- Read [shared query guidance](../querying-noibu-data/SKILL.md) and [runtime/actions](../querying-noibu-data/references/chatgpt-runtime.md). Use skill `product-analysis`; resolve the store and saved context. Default to 30 days.
- Focused questions use only necessary queries. For a full review, follow [queries](references/queries.md): products by views, product-page cart opportunities, collections and product types; compare suitable cohorts and run targeted follow-ups for supported signals.

## Dashboard and opportunities

Use the packaged [inline presentation](../querying-noibu-data/references/presentation.md), not a custom redesign.

- Lead with one or two measured conclusions.
- Keep session count, session conversion and measured median completed cart value/currency in `overviewContext`.
- Prefer a complete product-viewer cohort funnel: viewed product → cart → purchase. Name a focused cohort in `funnelContext`; never derive a store-wide funnel from top-N products. Any-cart purchase after viewing is not purchase of that product.
- Declare viewers/cart/all-session denominators and use counts for geometry. Missing stages stay omitted.
- Use two primary `placement: "overview"` tables, normally products and collections by sessions; other tables use `supporting`. Retain Show more/Show less, five-row previews and all source rows/full names. Numeric session counts may use `barColumn`.
- Label URL-based collection cohorts when events are sparse; omit unmeasured ATC, prices and revenue/session.
- Show the strongest two or three opportunities, fewer if warranted. Use a factual tag, specific product/collection, actual traffic unit and concise evidence with material limitations.
- Put the investigation/verification plan in `fix`, under **Investigation & verification**. Additional real signals retain their IDs/count; do not invent fillers.
- Keep **Save as Live Site** directly after dashboard content, then opportunities, then separate **Download & schedule** controls. Shared styling supplies light panels and orange measured declines.

## Interpretation

- Whole-cart values are not product revenue; distinguish AOV from median value.
- Compare price tiers only with measured prices/confirmed context, not title guesses. Without credible peers, use measured cart-opportunity scores and funnel behavior.
- Title variants/localized URLs may split a product; disclose suspected duplicates rather than silently merging.
- Low scroll does not prove a control was unseen; country differences do not establish shipping restrictions; errors correlated with low conversion do not prove causation.
- Exposure is not proven blocked users or recoverable sales. Preserve attribution/identity limitations.

## Follow-ups

- Reuse evidence for Investigate and exports. Route technical causes to tech-diagnosis and its [GitHub handoff](../tech-diagnosis/references/github-handoff.md); normal analysis does not require a repository.
- Site saves use [persistent dashboards](../querying-noibu-data/references/connected-dashboard.md) and [permission preflight](../querying-noibu-data/references/site-permissions.md), including the confirmed weekly-refresh offer.
- **Schedule Insights** uses [shared connected delivery](../querying-noibu-data/references/scheduling-delivery.md) with fresh product scope, rolling windows and comparison rules. Daily is not offered here.
