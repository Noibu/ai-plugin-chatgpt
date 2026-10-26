---
name: segment-analysis
description: Compare devices, countries, channels, and campaigns using Noibu, identify conversion regressions, and provide an interactive report with investigation, dashboard, export, and scheduling actions.
---

# Segment conversion analysis

- Read [shared query guidance](../querying-noibu-data/SKILL.md) and [runtime/actions](../querying-noibu-data/references/chatgpt-runtime.md). Use skill `segment-analysis`; resolve the store and saved context. Default to 30 days.
- Focused questions need only relevant queries. For a full review, follow [queries](references/queries.md):
  - Fetch device, country and UTM source/medium aggregates plus a direct whole-domain baseline.
  - Compare channels with peers of similar intent/objective; compare devices with their own history. Use equal halves with exact dates for within-window device ratios.
  - Assess traffic quality and sparse purchases; zero conversion or geography alone does not identify bots.
  - Select up to three supported signals and run campaign, landing-page or funnel follow-ups.

## Dashboard and opportunities

Use the packaged [inline presentation](../querying-noibu-data/references/presentation.md).

- Lead with one or two measured conclusions.
- Overview: site-wide/mobile/desktop conversion, purchasing/session denominators, exact window/timezone and a few nonduplicative country/channel highlights. No mandatory funnel.
- Under Show more/Show less, use three `placement: "overview"` tables when supported: Countries, Best converting channels, Most visited channels. Include Sessions/CVR/Revenue per session with measured currency components kept separate.
- State each ranking's volume filter, population and top-N bounds. A capped result cannot establish a global winner. Retain five-row previews/all rows; history/campaign/landing tables use `supporting`.
- Use up to three visible `overviewNotes` for material attribution, reconciliation or currency caveats; retain detailed evidence too.
- Each top opportunity has a factual tag, specific cohort, actual traffic unit and concise evidence; `fix` holds expandable investigation/verification.
- Keep **Save as Live Site** directly after dashboard content, then opportunities, then separate **Download & schedule** controls. Shared styling supplies light panels and orange measured declines.

## Interpretation

- A stable device gap is not a regression. A worsening ratio driven by faster desktop improvement or traffic mix does not prove mobile deteriorated.
- Separate country opportunity, channel intent and campaign objective; exposure is not proven blocked users or lost orders.
- Do not merge source/medium aliases or call all unattributed sessions Direct without evidence.
- Missing UTM share needs a complete unattributed aggregate and whole-domain denominator, not overlapping cohort sums. Missing tags do not prove a tracking defect.
- For absent paid-traffic UTM rows, use the shared guide's referrer-parameter recovery and label results a lower bound.
- Preserve low-volume uncertainty, count discrepancies and currency boundaries; do not invent signals to fill cards.

## Follow-ups

- Investigate retains the selected evidence. Route genuine technical findings to tech-diagnosis and its [GitHub handoff](../tech-diagnosis/references/github-handoff.md), not ordinary marketing findings.
- Site saves use [persistent dashboards](../querying-noibu-data/references/connected-dashboard.md) and [permission preflight](../querying-noibu-data/references/site-permissions.md), including the confirmed weekly-refresh offer.
- **Schedule Insights** uses [shared connected delivery](../querying-noibu-data/references/scheduling-delivery.md), fresh rolling scope and the confirmed equal-half/other baselines. Daily is not offered here.
