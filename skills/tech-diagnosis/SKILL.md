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
- Return impact, evidence, where the evidence points (stack frame, page, element) and the likely cause marked as a hypothesis. Do not write a fix, patch or generic remediation steps unless source is already verified for this store.
- Diagnosis never needs source. Every fix (Get fix, Investigate, a typed "how do I fix this", a PR) follows [source access](../querying-noibu-data/references/source-access.md): use the Shopify theme through Noibu or a connected code host with a recognized repository/branch; otherwise return the diagnosis hint and the connect step. Never give an unverified fix.

## Presentation and actions

- Use [inline presentation](../querying-noibu-data/references/presentation.md). On merchant and performance board cards, `fix` holds only the next diagnostic check unless source is already verified; never a code fix or generic remediation. Performance findings need structured p75 cards: value/units, threshold bands/marker, page/device/traffic/window and observed status only. Missing values remain unknown.
- Include [verified Noibu links](../querying-noibu-data/references/console-urls.md); metric overview URLs do not imply preserved filters.
- Show Investigate/Get fix and **Open a Ticket** on merchant and performance findings, even before source or a ticket tool is connected. Vendor findings show **Prepare vendor message** (and Ignore when supported), never Investigate/Get fix. Ticket clicks use the [destination-first chooser](../querying-noibu-data/references/ticket-handoff.md); wait for selection before provider discovery/creation. Ignore requires an actual issue and supported status tool.
- Investigate/Get fix permit read-only source inspection and a proposal, not edits/PRs. Repository writes, draft PRs, tickets, status changes and vendor messages require their requested scope and approvals; never merge/deploy. Missing ticket or vendor integrations yield an explicitly unsaved draft; missing source yields the connect step, not a fix.
- Data does not prove every session was blocked. Revenue-loss projections are only for requested money impact; redact sensitive HTTP fields.
- Requested schedules use [connected delivery](../querying-noibu-data/references/scheduling-delivery.md), retaining focused/survey scope and fresh error/performance windows. Reporting does not require GitHub or authorize automatic remediation/status writes.
