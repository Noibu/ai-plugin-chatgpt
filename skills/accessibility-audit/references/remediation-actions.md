# Audit remediation actions

After the PDF and concise chat summary, render a native action panel with **Auto-draft PR** and **Auto-create tickets** when there are confirmed findings. The shared renderer shows the exact selected titles and sends at most three actual finding IDs per action. Use the normalized report's stable IDs; retain its evidence JSON and report identity so follow-ups can verify the selected scope. Do not use severity totals or candidate ranks as IDs.

Show only the available meaningful actions: no empty batch for zero confirmed findings, no PR batch for known content-only/vendor-owned fixes, and no buttons that imply an unreviewed/incomplete check is a confirmed issue. Unknown ownership may be a source-review candidate but is not a promise that a code fix or PR can be made. Browser-review observations must remain explicitly manual; automated counts remain unknown.

## Auto-draft PR

The click is an explicit request for scoped draft PRs for the visibly selected findings, subject to repository/ref resolution and native approvals. First follow [GitHub handoff](../../tech-diagnosis/references/github-handoff.md): reuse a usable connection or prompt to connect, resolve the exact merchant repository and deployed/ref context, inspect relevant source and verify component ownership. Do not require GitHub for the audit itself or assume Noibu's plugin repository is the storefront source.

Before editing, map each selected finding's real selector/HTML to the component and proposed fix. Merchant content uses a content/editor handoff; managed checkout/vendor code uses its owner handoff. If scope or deployment ownership is unclear, ask or return a proposal instead of editing unrelated code. Keep the original audit available while the user connects or selects a repository.

Prepare narrow changes, run relevant available checks and describe the manual accessibility verification still needed. Create draft PRs only within the resolved user-requested scope and allowed tool permissions; combine related fixes only when the component/change is coherent, otherwise keep separate. Inspect existing PRs to avoid duplicate work, particularly after an ambiguous write. Return actual draft PR links and the finding IDs each addresses, or an explicitly uncreated patch/proposal and precise blocker. Never merge, deploy or claim the accessibility issue is fixed merely because a PR was opened.

## Auto-create tickets

Follow [destination-first ticket handoff](../../querying-noibu-data/references/ticket-handoff.md). Ask the native composer question once for the visible selected batch, using Linear/Jira/GitHub Issues/Notion plus free text/Skip where supported, or the all-choice text fallback. Wait for a submitted answer; no initial-click/default/Skip write. Resolve the provider's exact project/repository/database and required fields, then create at most one ticket per selected finding with required approvals and duplicate checks. Do not require GitHub when another provider is chosen.

Include each finding's observed severity (manual when applicable), verified criterion/help link, selectors/snippets, affected page set and known pageview window, proposed fix with uncertainty, acceptance checks and report reference when its URL/file is actually shareable. Do not upload the PDF or broaden access merely because a ticket is requested; attach/link only through supported access-preserving tools and needed authorization. Preserve partial traffic/scan limits and omit secrets/customer data.

Return each actual ticket ID/link after success. If some succeed and others fail, list outcomes individually; do not recreate successful tickets or label an entire batch successful. A failure yields a precise blocker and offered **Ticket draft - not created**. No incidental Noibu status update, external message, schedule or source change.
