---
name: tech-diagnosis
description: Diagnose Noibu errors and Core Web Vital performance issues, explain likely causes, and recommend or draft a requested fix.
---

# Technical diagnosis

- Read [shared query guidance](../querying-noibu-data/SKILL.md) and [runtime/actions](../querying-noibu-data/references/chatgpt-runtime.md). Use skill `tech-diagnosis`; resolve store/platform and saved context.
- Specific issue/error/page/metric requests are focused diagnoses; general “what is broken” requests are surveys. Default performance window is 30 days; label the active-error survey's separate seven-day window.

## Survey

- Read the matching `references/platforms/` file, or generic fallback. Search active errors by occurrences, up to three pages of 30; stop when sufficient distinct candidates exist.
- Active fix candidates need last occurrence within 48 hours, >10 seven-day occurrences, usable stack and merchant-owned frames. Deduplicate primary file/signature; distinguish infrastructure/telemetry/vendors.
- Rank by occurrences × page criticality: checkout 5, cart 4, product 3, collection 2, home 1, other 0.5. Vendor code receives an owner handoff.
- Fetch p75 LCP/INP/CLS by page/group/device using [performance guidance](references/performance.md); rank by traffic/severity without mixing unlike score scales.
- Present separate merchant/performance/vendor sections, at most two findings each, with windows, occurrences/traffic, last seen and next actions.

## Focused diagnosis

- Read [error guidance](references/errors.md) or [performance guidance](references/performance.md); fetch matching details, diagnosis, trends and segment evidence.
- Separate observations, Noibu AI explanations and causal hypotheses. Exact source lines/element claims need inspection.
- Return impact, evidence, likely cause/uncertainty, proposed fix and verification together; do not hide essential guidance behind a button.
- Initial Noibu diagnosis does not require browser/GitHub. For Investigate/Get fix or natural-language source diagnosis/fix/PR requests, follow [GitHub handoff](references/github-handoff.md): verify/reuse connection, otherwise prompt to connect; resolve repository/ref and inspect merchant source. Keep useful unverified guidance while access is pending.

## Presentation and actions

- Use [inline presentation](../querying-noibu-data/references/presentation.md). Performance findings need structured p75 cards: value/units, threshold bands/marker, page/device/traffic/window and observed status only. Missing values remain unknown.
- Include [verified Noibu links](../querying-noibu-data/references/console-urls.md); metric overview URLs do not imply preserved filters.
- Show Investigate/Get fix and **Open a Ticket**, even before an integration is connected. Ticket clicks use the [destination-first chooser](../querying-noibu-data/references/ticket-handoff.md); wait for selection before provider discovery/creation. Ignore requires an actual issue and supported status tool.
- Investigate/Get fix permit read-only source inspection and a proposal, not edits/PRs. Repository writes, draft PRs, tickets, status changes and vendor messages require their requested scope and approvals; never merge/deploy. Missing integrations yield an explicitly unsaved draft/specification.
- Data does not prove every session was blocked. Revenue-loss projections are only for requested money impact; redact sensitive HTTP fields.
- Requested schedules use [connected delivery](../querying-noibu-data/references/scheduling-delivery.md), retaining focused/survey scope and fresh error/performance windows. Reporting does not require GitHub or authorize automatic remediation/status writes.
