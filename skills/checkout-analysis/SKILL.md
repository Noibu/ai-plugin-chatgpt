---
name: checkout-analysis
description: Analyze Noibu checkout performance, funnel drop-off, payment and delivery mix, abandonment, and technical issues with an interactive investigation board, dashboard, export, and scheduling actions.
---

# Checkout performance

- Read [shared query guidance](../querying-noibu-data/SKILL.md) and [runtime/actions](../querying-noibu-data/references/chatgpt-runtime.md). Use skill `checkout-analysis`; resolve the store and saved business context.
- Default to the last 30 days versus the immediately preceding equal window; honor requested dates.
- Focused questions use only relevant [queries](references/queries.md). For a full review:
  - Fetch Q1–Q7, Q1b when row-level fields exist, and prior counterparts; independent aggregates can run together.
  - Use distinct sessions reaching at least each stage. Express checkout may skip intermediate events.
  - Compare each segment with its own prior window. Candidate regressions are ≥3 pp absolute or ≥10% relative with sufficient traffic; rank up to three supported findings.
  - Run targeted follow-ups. Route merchant technical causes to tech-diagnosis; give UX/operations findings a concrete next check and verification plan.

## Report

Use the packaged [inline presentation](../querying-noibu-data/references/presentation.md); focused answers may remain prose.

- Lead with one or two measured conclusions.
- Overview: compact population/cart reach, count-scaled cart → checkout → payment → completion funnel, completion/device/value highlights, supported abandonment rows and populated payment/delivery bars.
- Show exact windows, timezone, denominators, currency and express-checkout/coverage limits. Avoid duplicating KPIs as highlights.
- Put abandonment tables at `placement: "overview"`; supporting data is expandable. Label bounded samples and never extrapolate sample cart values to all abandoned sessions.
- Classify abandonment as observed behavior, not proven motives. Check continued product/category browsing before generic no-action. Payment/delivery mix measured only on purchases cannot establish gateway failure rates.
- Each numbered opportunity needs its cohort, current/prior denominators, signed pp/relative delta and `fix` containing **Next check** plus verification. Do not pad findings or treat tiny order movements as major opportunities.
- Missing slices stay omitted. With healthy completions but missing intermediate events, headline cart-to-completion rather than invented drops. An empty window warrants another date/store choice.
- Estimates need a formula/baseline and are not guaranteed recovery. Lower discount use alone does not prove coupon failure.

## Follow-ups

- Preserve the tested light dashboard, **Save as Live Site** beneath dashboard content, investigation cards, and separate final Pages/download/scheduling controls.
- Investigate reuses the selected evidence; technical findings use [source access](../querying-noibu-data/references/source-access.md) for any fix, not ordinary UX/operations analysis.
- Site saves follow [persistent dashboards](../querying-noibu-data/references/connected-dashboard.md) and [permission preflight](../querying-noibu-data/references/site-permissions.md), including the confirmed weekly-refresh offer.
- Scheduling follows [connected delivery](../querying-noibu-data/references/scheduling-delivery.md), with fresh rolling comparisons; exports reuse evidence unless refresh is requested.
- Issue/status changes require an explicit request, exact issue and supported status. Analysis/rendering authorizes no writes.
