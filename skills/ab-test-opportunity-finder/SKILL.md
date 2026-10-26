---
name: ab-test-opportunity-finder
description: Find evidence-backed A/B test opportunities using Noibu analytics, optionally validate the live storefront and preview variations, and create requested Noibu test drafts.
---

# A/B test opportunities

- Read [shared query guidance](../querying-noibu-data/SKILL.md) and [runtime/actions](../querying-noibu-data/references/chatgpt-runtime.md). Use skill `ab-test-opportunity-finder`.
- Resolve the store and goal: cart adds, checkout starts/completions, product/collection/specific page views or all goals. Ask for a URL only for a specific-page goal; unattended runs use the confirmed goal or disclose all goals.
- Follow the [query battery](references/noibu-query-battery.md): sessions, goal events, sibling domains, business context and existing tests. SDK connection status does not prove historical data is absent.
- Under ~1,000 sessions, discuss insufficient evidence; under ~15,000 in 30 days, offer 90 days and disclose widening. Never silently replace an unmeasured success metric.
- Query baseline/targeted batches; require measured gaps, plausible mechanisms and relevant traffic. Technical defects are fix-first, not experiments masking bugs.

## Validate and present

- Read [site validation](references/site-validation.md). Inspect analytics-selected pages/policies with supported browser controls; record country, currency, viewport and time. Drop already implemented/policy-contradicted ideas. Without browser evidence, label hypotheses unvalidated; do not invent selectors.
- Rank a short goal-linked list: proposed change, evidence, hypothesis, control/variation, metric/guardrails, device/UTM targets, weekly eligible traffic/events, experiment overlap, developer notes and verification.
- Use Noibu's returned verdict-time estimate only; projections/correlations are not causal loss.
- [Before/after previews](references/preview.md) are optional real captures. Temporary DOM/CSS changes require approved execution, never a read-only evaluator; previews are not deployment.
- Follow [candidate handoff](references/handoffs/candidates.md), generate/validate `candidates.json` when files are supported, and use [inline presentation](../querying-noibu-data/references/presentation.md). Each **Create A/B draft in Noibu** action retains the exact candidate/hash. Use useful chat recommendations if rendering/files are unavailable.

## Requested actions

- Draft creation only: read [draft creation](references/create-drafts.md), validate the selected payload and check existing titles before `noibu_create_ab_test`. Return actual ID/key/status plus **Open draft in Noibu** using [verified console links](../querying-noibu-data/references/console-urls.md). Resolve missing numeric IDs from the roster, never rank/slug; do not recreate to obtain a link.
- Recommendation creates nothing; implementation, deployment and test lifecycle changes are separate requests. Never start a test during draft creation.
- Source implementation/fix-first actions use [GitHub handoff](../tech-diagnosis/references/github-handoff.md), then the [SDK](references/shared/noibu-feature-flag-sdk.md) and [platform notes](references/shared/platforms.md). Analytics/draft creation remain available without GitHub; connection does not authorize writes/PRs/deployment/start.
- Requested recurring reports use [connected delivery](../querying-noibu-data/references/scheduling-delivery.md): preserve goal/targeting, fresh evidence and roster/overlap checks, and confirmed browser-validation versus analytics-only coverage. Scheduling recommendations never authorizes automatic drafts, storefront mutations, implementation or activation.
