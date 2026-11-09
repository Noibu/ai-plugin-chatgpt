---
name: accessibility-audit-browser-workaround
description: "Resume an accessibility audit blocked by browser readiness or approval UI, import completed axe exports, or provide a clearly limited review."
---

# Accessibility audit recovery

Use [the canonical accessibility audit](../accessibility-audit/SKILL.md) and its
[execution and recovery procedure](../accessibility-audit/references/execution-and-review.md).
This entry point shares the main skill's engine, importers, report builders and
safety boundaries; do not copy or maintain a separate scanner or support tree.

- Preserve any selected URLs, original traffic window and completed evidence.
- Discover the actual browser interface. Handle an unavailable approval control
  as a host UI blocker; do not repeat an approval the user cannot answer.
- For a paused-document error, make at most one retry after observable readiness
  recovery. Do not bypass a denial or change security settings.
- Offer completed axe exports or a separately chosen hosted crawl when supported.
  A queued crawl is not completed evidence and may render a different state.
- Use the canonical multi-state importer for matching `scan_index`/`scans` exports.
  Retain actual URL, timestamp, state, scope, viewport, engine and options. Scan
  states are not distinct pages; imported findings are not fresh scans.
- Without completed axe evidence, use the separate limited-review contract and
  keep automated severity counts unknown. Report coverage and remaining blockers.
