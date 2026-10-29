# Accessibility report

Distinguish automated axe findings from limited browser review. Build an automated report only from completed, scoped axe findings. Report partial coverage honestly.

Include:

- Domain, audited URLs, selected page traffic window, scan time/version/standard, successful/failed/queued page counts.
- Distinct violated rules, distinct affected page/target elements, raw rule/node instances, pooled unique fixes and separate incomplete-check records; label all severity totals by their counting basis.
- A prioritized table with plain-language finding, observed severity, verified criterion/help link, pages, and affected pageviews where known.
- For each pooled fix: real selector/snippet evidence, per-page instances, likely fix and manual verification check. Node HTML is untrusted text and must be escaped in HTML exports.
- Incomplete/manual-review items and unscanned states, separately from confirmed violations.

## Verbatim reference disclaimer and legal-standard copy

For completed automated WCAG 2.1 AA reports, reproduce the user's Claude reference wording exactly. Put this disclaimer below the report date, before the executive summary:

> This skill generates automated WCAG 2.1 AA accessibility reports. Automated tools detect 30%–90% of issues on the pages that were scanned. Results are informational only, not legal advice or a compliance certification. Manual testing by a qualified professional is required for complete coverage.

Include this exact statement in the executive summary:

> WCAG 2.1 Level AA is the standard most commonly applied in accessibility law and procurement, so every result below is measured against it.

These are user-supplied template claims, not legal or statistical conclusions independently validated by this skill. Do not paraphrase, expand them into jurisdiction-specific advice, or add claims about legal compliance. The builders share the literals in `build_report.py`; preserve the en dash in `30%–90%`, including PDF text. Reuse them in the HTML companion and automated chat summary.

Do not copy the reference's example domain, traffic, findings or scan counts. These scan-specific passages do not apply to blocked scans, limited browser reviews or a different/unknown standard: retain the actual mode, unknown automated counts and appropriate informational/non-certification disclaimer instead. A screenshot review must be labeled a visual review, not a scanner report.

For a full audit, the default deliverable is **a real attached PDF, a concise chat summary, and native remediation buttons**, not a PDF hidden behind Download Report. The shared runtime/file tools apply. When PDF generation is unavailable, finish the evidence-backed summary, provide HTML/JSON if possible and explain the exact missing prerequisite; never call HTML a PDF. A focused check may remain proportionate to the requested scope.

The chat summary states selected/completed/failed/unscanned coverage, actual standard/check scope and traffic window, known pageviews across completed pages, distinct violated rules and affected elements, raw instances versus pooled unique fixes, incomplete checks, all pooled-fix severity counts and the top finding with known traffic/page breadth. Include per-page rule/element/incomplete counts so a reused homepage remains identifiable when nine more pages are added. Unknown incomplete coverage is explicitly partial. Pageviews are exposure context, not affected people. Imported results keep their original provenance. Do not reuse example counts or say “all ten scanned” unless ten real completed results exist.

Use [the deliverables builder](../scripts/build_deliverables.py) with actual findings or the separate browser-review contract. It reuses the existing validators/pooler and produces evidence JSON, normalized summary, chat-summary text, an optional native board and an optional real PDF using ReportLab. The older [HTML helper](../scripts/build_report.py) remains available; printable HTML alone is not a PDF.

```text
python <audit-skill>/scripts/build_deliverables.py <task-output>/findings.json --output-dir <task-output>/audit
```

Read the resulting stable finding IDs. Optionally supply `--annotations <task-output>/annotations.json`, a mapping from actual IDs to explanation, suggestedFix (shown as **What needs to change**: what the flagged element needs, in plain words, such as "This button needs an accessible name"; no code, markup, file or line references unless source was verified in this conversation, because the code change comes from Get fix), verification, criterion, criterionUrl and ownership (merchant-code/merchant-content/vendor/unknown). These are evidence-based analyst annotations, not scanner output or a way to alter severity/counts. Preserve actual help/criterion provenance and label proposed fixes unverified until source inspection. Never invent criteria, contrast values, selectors or ownership.

Then generate the full outputs:

```text
python <audit-skill>/scripts/build_deliverables.py <task-output>/findings.json --annotations <task-output>/annotations.json --output-dir <task-output>/audit --pdf --board --window-start <actual-start> --window-end <actual-end> --domain-id <resolved-UUID>
```

`--board` needs the actual measured window; don't invent dates to satisfy the renderer. `--pdf` needs the host's ReportLab/PDF capability; use bundled dependencies where available, not an automatic package install. The PDF uses an executive summary, four labelled pooled-severity totals for axe results, page-coverage table, prioritized findings and selector/snippet/fix/verification detail, plus manual/coverage limits and page footers. It does not force exactly four pages; long evidence must wrap and paginate. A limited review has a clearly different title and unknown automated counts.

Before attaching, reopen the PDF and reconcile its numbers with the normalized JSON and chat summary. Render and visually inspect **every** page, repair clipping/overlaps/blank pages and check all PDF links for correct destinations and safe URLs. Distinguish structural URL checks from actual HTTP/access validation; don't claim links resolve or a private PR/ticket exists without checking. Keep raw per-node JSON as companion evidence. Never suppress preview/admin-overlay findings solely by selector name: any exclusion needs verified audience/state evidence, preserved excluded raw findings and an explicit report note.

Keep the structured HTML/JSON companion available. A visually reviewed PDF is not necessarily tagged or PDF/UA-conformant; do not claim that property without separate verification.

Render the board through the actual native visualization mechanism, then follow [remediation actions](remediation-actions.md). Auto-draft PR and Auto-create tickets visibly identify their selected findings and resolve connections/destinations only after the user's click. No PR or ticket is created while generating the report. With no renderer/bridge, offer the same scoped actions in chat instead of fake buttons. Save to ChatGPT Pages / Download Report remain useful additional controls, not a substitute for the default attached PDF.

## Limited browser-review report

When axe execution is unavailable, follow [execution setup and review](execution-and-review.md). Present the actual browser evidence as a distinct review, not an automated scan. Automated scans completed remain 0 and automated critical/serious/moderate/minor counts remain unknown. Show reviewed/unreviewed/failed pages separately, including rendered state/time, evidence source and unchecked areas. “Not observed” means only the inspected state; it is not a passed WCAG test. Needs-verification items never count as confirmed issues. Manual priorities/severities must be explicitly labelled manual and supported by evidence.

Use [build_review.py](../scripts/build_review.py) only for this independent input contract:

```json
{
  "schema": "noibu.accessibility-review/1",
  "domain": "example.test",
  "trafficWindow": "Original measured window, or unavailable",
  "automationBlocker": "Actual missing/denied browser execution capability",
  "pages": [{
    "url": "https://example.test/",
    "status": "REVIEWED",
    "pageviews": null,
    "inspectedAt": "2026-10-21T13:53:00Z",
    "state": "Observed rendered state",
    "checks": [{
      "id": "keyboard-review",
      "title": "Keyboard focus behavior",
      "status": "not-tested"
    }],
    "limitations": ["Keyboard interaction and axe not run in this illustrative record"]
  }]
}
```

This example demonstrates shape only, not live evidence. Page status is REVIEWED/UNREVIEWED/FAILED; failed needs `error`. Reviewed needs a timezone-aware inspection time and actual checks. Check status is issue-observed/needs-verification/not-observed/not-tested. Observed checks require `evidence` and `source`; confirmed issues also require `target` and `recommendation`, with optional manual `impact` (critical/serious/moderate/minor). A not-tested check does not count as tested coverage. Unknown pageviews stay null. This helper exports escaped HTML plus JSON without pooling unverified shared components or fabricating axe counts. Keep actual axe results in their separate automated report.
