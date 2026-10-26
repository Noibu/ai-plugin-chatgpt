---
name: accessibility-audit
description: Audit website accessibility with approved browser axe-core execution or completed axe exports; when execution is unavailable, guide setup and provide a clearly labelled limited browser review, prioritized with Noibu traffic where available.
---

# Accessibility audit

- Read [shared query guidance](../querying-noibu-data/SKILL.md), [runtime/actions](../querying-noibu-data/references/chatgpt-runtime.md) and [execution setup](references/execution-and-review.md). Use skill `accessibility-audit`.
- Discover browser capabilities before unnecessary traffic queries. Completed axe exports need provenance, not a new browser connection.

## Prerequisites and execution

Before a connected-Chrome scan, show/verify this checklist; ask only for missing confirmation:

- Official ChatGPT Chrome extension connected to the intended profile.
- **Settings → Browser → Developer mode → Enable full CDP access**, if the organization permits.
- Native approval for the specific website/debugging request; pending approval is not execution failure.

The built-in browser is a separate option without Chrome-extension requirements. Never change security settings automatically; terminal/Custom permissions do not grant browser scripting.

- Read the current browser API and [scan/findings procedure](references/scan-and-findings.md).
- Use supported document-readiness operations, then a minimal approved awaited-result execution probe; only after success load bundled checksum-pinned axe and run the bundled scan expression.
- Distinguish temporary paused-document CDP errors from missing permissions/interface; follow the bounded readiness/retry procedure rather than declaring advertised CDP unusable after one transient error.
- Results return from the page. Do not bypass denial through shell, raw CDP, console, bookmarklets or another automation channel, or substitute a remote job automatically.
- Completed exports retain original URL/time/state/engine/options and are not fresh scans. A separately requested remote job is outside this browser flow; QUEUED is not findings.

## Scope and resume

- A named-page request covers that page. Full-site audits select up to ten pages by 30-day Noibu pageviews using `noibu_get_page_visits`; explain scope. Traffic ranks priority but is optional for an explicitly supplied URL.
- Reuse selected URLs/window and validate completed evidence on resume; preserve immutable original time/state/options and scan remaining pages only. One completed homepage in ten pages means nine pending, not ten new scans.
- Without approved execution, guide permitted setup and rediscover capabilities. Unless axe-only, perform the distinct **Browser-based accessibility review — axe not run** using supported snapshots/screenshots/read-only observations. Report reviewed/unreviewed pages, manual observations, verification items and unchecked states.
- Limited review uses [the review exporter](scripts/build_review.py): zero completed axe scans, unknown automated severities, no invented axe violations. If inspection is unavailable or axe-only, return the precise prerequisite and selected scope.

## Findings and deliverables

- Pool confirmed shared-component findings by rule/criterion plus stable selector. Keep per-page nodes and count affected pageviews once per unique page.
- Rank severity weight × log10(max(1, affected pageviews)) × min(2, 1 + 0.2 × affected page count). Missing traffic stays unknown; incomplete checks are verification items, not violations.
- Report distinct violated rules, affected page/target elements, raw rule/node instances, pooled fixes and incomplete checks separately, with completed/failed/unscanned pages and rendered states.
- Follow [report format](references/report.md): verified PDF attachment, concise summary from the same normalized evidence, severity/fix table and top finding. Preserve its legal text/disclaimer exactly; automated checks do not certify compliance.
- Keep iframe/shadow-root/hidden-state/manual limits visible; unreviewed pages are not clean. Limited/blocked reports retain unknown axe counts, including in PDFs.
- Use [inline presentation](../querying-noibu-data/references/presentation.md) for **Auto-draft PR** / **Auto-create tickets**, visibly scoped to actual top finding IDs. [Remediation actions](references/remediation-actions.md) resolve connections/destinations after selection; rendering creates nothing.
- Investigate/Get fix/source remediation uses [GitHub handoff](../tech-diagnosis/references/github-handoff.md). Preserve completed audit evidence while connection/ref/ownership verification is pending; vendor/managed components need owner handoff. Scanning/reporting does not require GitHub.

## Recurrence

- Follow [connected delivery](../querying-noibu-data/references/scheduling-delivery.md). Confirm audit mode, standard, rendered states and fixed-URL versus traffic-ranked selection rule.
- Verify approved browser readiness/execution in the scheduled runtime before promising fresh axe scans; interactive success does not prove unattended access.
- Missing execution requires a concrete blocker and consent before an alternative. Never replay exports as fresh or silently downgrade axe-only scope.
- Report scheduling does not authorize remediation, PRs, tickets, remote jobs or setup-time delivery.
