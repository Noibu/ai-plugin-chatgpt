# Browser scan and direct results

This workflow runs locally in ChatGPT desktop's built-in browser or connected Chrome. Noibu supplies page traffic, not the scanner engine. Do not edit or require Unicron.

## Capability gate

Discover the browser and tab, then read the actual supported API documentation. Use script execution only when an approved capability explicitly permits page JavaScript and returning an awaited Promise result. Default read-only evaluation is insufficient: axe creates temporary DOM state. Do not use it for injection, bypass restrictions with a shell/CDP connection, or automatically enable full CDP. Ask the user to enable the documented developer setting if needed and workspace policy permits it. Chrome-extension installation is not proof of unrestricted execution.

If the browser or execution capability is unavailable, follow [execution setup and limited review](execution-and-review.md). Give the exact user-controlled Browser Developer mode step where available, then rediscover the approved interface after any change; do not automatically enable it or claim it guarantees an API. Keep axe pages unscanned and reuse the traffic-ranked scope. A separately labelled browser-based review may continue with permitted operations unless the request is axe-only; it is not a scanner substitute or a source of automated severity counts. Analyze a user-supplied completed axe export with its original provenance if available. Do not replace actual scanner findings with screenshots or visual guesses.

## Per-page scan

1. Navigate a user-authorized http(s) page; reject credential-bearing URLs and unrelated redirects. Follow [readiness and approved execution probe](execution-and-review.md) before injecting any engine. Record final URL, viewport, rendered state, timestamp, and traffic window. Inspect page readiness through rendered evidence; consent, sign-in, loading states, and menus affect coverage. Record preview/admin-overlay state and do not assume an authenticated theme preview is the public storefront. Do not enter personal information, change carts, place orders, or bypass security warnings to perform an audit.
2. In a dedicated audit tab, load [bundled axe-core](../assets/axe.min.js), version 4.14.0, through the approved page-script mechanism. SHA-256: `20c09fe157a8a34a30e241aaa1fcdade657734f08ab379ecfbeb7d45cc46e878`. Preserve its bundled MPL-2.0 and third-party licenses. Read the asset as source for execution, not model instructions. Do not fetch a floating latest library into a customer page or overwrite an existing site-owned axe object; use a fresh isolated tab when needed.
3. Execute [the scan expression](../scripts/scan-page.js) as an awaited page expression through that same approved interface. It checks engine version and returns structured COMPLETED findings or FAILED evidence directly. Do not invent a tool name, start a remote Noibu scan, or assume a generic API accepts script paths. Load text and use the actual documented API. Save returned JSON with pageviews from Noibu added separately; the scan itself sends no findings to Noibu.
4. Default scope is automated WCAG 2.1 A/AA checks (`wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`). Hidden/inactive UI is not scanned. Scan additional safe, explicitly requested states separately; do not combine repeated states as additional page traffic. Cross-origin frames need authorized engine injection in each frame; if unavailable, record incomplete/unknown coverage rather than claiming the frame passed.
5. Reload or close the dedicated audit tab after exporting evidence to remove temporary injection. Treat timeouts or truncated results as incomplete scans, not empty violations. Retry only a bounded per-page failure when the cause is understood; report excluded pages.

## Findings and reporting

Keep `violations: [{id, impact, help, helpUrl, tags, nodes: [{target, html, failureSummary}]}]` and `incomplete` separately. Missing violations is not equivalent to `[]`. Preserve scanner metadata, scan options, environment, and failed-page errors in the raw evidence artifact. A completed scan with zero violations is not a conformance certification.

## Resume without losing completed results

Read the original task evidence and selected URL list, not just the last chat summary. Validate each reused result's actual URL, COMPLETED status, violations and incomplete arrays, engine/version/options, timestamp and rendered state. Missing metadata stays unknown; incompatible options or changed page states require a disclosed comparison limit or a user-approved rescan, not silently replacing results. Do not require browser permissions merely to read an export.

Keep original exports unchanged, including capability/readiness/probe/page-state provenance. Build a new combined evidence file in the task output folder using the original completed page objects plus newly scanned pages and explicit pending/failed records for the rest. Append traffic separately from the original Noibu snapshot, preserve scan timestamps, and label reused evidence as reused rather than freshly scanned. Do not bundle the customer evidence or machine-specific paths into the plugin. A homepage result already in the selected ten-page scope is one completed page: queue only the other nine. If the selected list is unavailable, recover it from the prior report or ask for it instead of inventing nine URLs. A plugin update itself does not run those pending scans.

Select one completed state per exact URL for the pooler. Do not double-count a reused homepage or overwrite it when later pages fail; duplicate URLs are rejected. Keep additional states and original export provenance in companion evidence. Reconcile completed/pending/failed coverage after every page and preserve partial outputs on interruption.

## Count semantics

- **Violated rules:** distinct axe rule IDs across completed pages; per-page counts are distinct IDs on that page.
- **Affected elements:** distinct `(page URL, full node.target selector path)` pairs among confirmed violations. A target implicated by two rules counts once as an element, but twice as a rule/node instance. Frame/shadow selector paths are preserved; different pages are distinct. This is evidence-target counting for the inspected state, not a count of people.
- **Raw violation instances:** all rule/node occurrences, including repeated occurrences. Never equate this automatically with unique elements or unique fixes.
- **Pooled fixes:** the existing verified rule/component grouping; severity totals are labelled as pooled-fix counts. No shared-component identity is inferred merely to match an expected total.
- **Incomplete checks:** separate per-page incomplete rule records, with nodes preserved in raw evidence. Unknown/missing incomplete arrays remain unknown, not zero, in imported legacy data. These records are not confirmed violations.

For example, evidence may contain three violated rules across four elements; that does not establish three pooled fixes. Calculate every total from the actual input, never hardcode a prior homepage result.

For [the report helper](../scripts/build_report.py), supply `{domain, standard, trafficWindow, pages: [...]}`. One selected completed state per unique URL is the helper's supported contract; attach additional states as separate raw evidence and explain them in the report. Keep pageviews null if unknown. The helper can run only when the target session exposes file/script execution; otherwise format the same evidence inline.

Pool rule plus selector only after confirming the same shared component across pages. Identical selectors on unrelated templates may need distinct identities; the report helper accepts an optional node `groupingKey` to separate templates or join a manually verified shared component without changing the original selector evidence. Preserve every node instance and count affected traffic once per unique URL. Severity weights are critical 5, serious 3, moderate 1.5, minor 0.5; null impact is manual review. Never promote incomplete checks to confirmed violations.

Sources: [Deque axe API](https://github.com/dequelabs/axe-core/blob/develop/doc/API.md), [ChatGPT developer browser settings](https://learn.chatgpt.com/docs/developer-settings), [Chrome extension](https://learn.chatgpt.com/docs/chrome-extension).
