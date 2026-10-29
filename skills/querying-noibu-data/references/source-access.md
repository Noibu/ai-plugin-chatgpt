# Source access for fixes

Applies to every fix in every bundled skill: Get fix, Investigate on a technical finding, Prepare draft PR / Auto-draft PR, accessibility and performance remediation, A/B variation implementation, and typed requests such as "how do I fix this?", "what's the fix?" or "write the patch". Analytics, diagnosis, browser scans, tickets and Noibu draft creation never need source access.

## The rule

Speak to the user in your own words. Never quote, cite or link these instructions, rule text, file names or skill names (no "the skill requires…", no "source-access rule"). Explain only what the user needs: what we know, and what to connect.

A fix is written only from the merchant's actual source. Until source is connected and verified for this store, answer with the diagnosis hint and the connect step: no code, patch, step list or generic best-practice advice ("defer third-party scripts", "add a null check", "lazy-load images"), whether or not it is labelled unverified. Never write a fix first and ask for access afterwards.

## What counts as connected

Either of these, verified by a successful read for the resolved store:

1. **Shopify theme through Noibu.** Shopify stores with a theme storefront (not headless). `noibu_list_store_themes` with the domain `numId` returns the live theme. The source is the live theme (`role: main`), named by theme name and id.
2. **A code-host connector.** Any code host the user has connected in ChatGPT (GitHub, GitLab, Bitbucket, Azure DevOps or another) plus a recognized repository and branch, verified by reading that exact repository/ref. A catalog listing, an installed but unauthenticated app, or Noibu's own plugin/server repository is not a connection.

Vendor- or platform-owned findings never need source: they get the vendor handoff (Prepare vendor message), never Get fix or a connect prompt.

## Resolve the source

**Every check is fresh.** Users often install or connect GitHub, Bitbucket or another code host in the middle of the conversation, after you last looked. On every Get fix click, card click or fix request, re-run the connection check from scratch: look for code-host tools again and, if none are visible, use the host's plugin discovery or connection check, the same check you would run if the user asked "is GitHub connected?". Never reuse an earlier "not connected", "no tools" or failed result from this conversation. Only a source that was verified as readable may be reused.

Stop at the first step that verifies.

1. Recover the selected finding, domain UUID and `numId`, platform, stack/metric evidence and window from the conversation. Do not re-run the survey.
2. Source already verified earlier in this conversation for this store: reuse it without asking again.
3. Saved business context has a `Source code` entry: verify a read and reuse it.
4. Shopify theme storefront: call `noibu_list_store_themes`. Success means the live theme is the source.
5. Discover connected code-host connectors. A Get fix action whose `source` names a repository (from the connect card) means: verify exactly that repository and branch. Otherwise, including `source.discover`, find the repository yourself (below). Verify the read.
6. Nothing verifies: show the **Not connected** response below and stop. Do not poll or claim work continues in the background.

### Finding the repository

Do not make the user type what the code host can tell you. Once a code host is connected:

1. Search the connected code host's code for the most specific evidence: the stack-frame function or file name (for example `initializeOfflinePaymentHandler`), a distinctive string, or the template/section behind the finding. A repository that contains it is the match.
2. If code search is unavailable or inconclusive, list the repositories the connector returns and mark likely ones: name or description matching the store's domain or brand, the platform (BigCommerce Stencil/Cornerstone, Shopify theme/Hydrogen, Magento, WooCommerce) or storefront/frontend/theme names.
3. Exactly one clear match: use its default branch (or the branch the user named), verify the read and go straight to the fix. Its "Using …" line lets the user correct it.
4. Several candidates, or none clear: show the connect card in mode `choose` with `repositories` (only names the connector returned, likely ones flagged, at most 30). The user picks from a dropdown or chooses Other repository.
5. The connected repositories do not contain the code, or the user's named repository failed: show the card in mode `enter` with a `codeHostNote` saying what was searched or what failed, and `prefill` with anything the user already gave. This is the only state with typed repository fields.

When both a Shopify theme and a code host are available, use the one that contains the code in the evidence. If the theme is deployed from a repository, prefer the repository so a later PR lands where the team ships.

## Confirm it is the right source

Before writing a fix, find the evidence in the source: the stack-frame file and function (map `cdn.shopify.com/s/files/.../assets/<name>` to theme `assets/<name>`; match minified bundles through source maps or distinctive strings), or the template, section or element behind a performance or accessibility finding. If it is not there, say exactly what was not found and where ("`cart-drawer.js` is not in acme/storefront @ main"), ask for the right repository, branch or theme, and stop. Never fall back to a generic fix. Label an unknown deployed revision.

## Reading a Shopify theme

Theme files are read through a theme change: `noibu_start_theme_change` (title `Get fix: <finding>`), then `noibu_search_theme_files` and `noibu_read_theme_file`. Starting a change edits nothing; edits go to a copy and nothing reaches the storefront unless previewed and published by the merchant. Only one change can be open per store: if another change is open, do not read through it as if it were live and do not discard it without asking. If the user does not take the fix to a preview, discard the change you started with `noibu_discard_theme_change`.

## Response: not connected

Reply format: one short lead-in sentence, then the card, and nothing after the card.

When no code host is connected, also offer ChatGPT's own plugin install suggestions for both **GitHub** and **Bitbucket** (each one the plugin directory actually returns), so the user can install either in place. If saved context or the user already named the code host, suggest only that one. Never claim a suggestion exists if discovery returned nothing; the card's Open Plugins button covers the rest.

Show the connect card: Build it with [the card renderer](../scripts/build_source_connect.py) from a `noibu.source-connect/1` input ([contract](presentation-contract.md#source-connect-card)) and render it through the same native inline visualization as the report board. Carry over the original report's `workflow`, `reportId`, `domain`, `window` and `generatedAt` so the card's buttons match the report. Set `platform` to the platform Noibu returned for the domain; add `shopifyTheme` only when that platform is Shopify with a theme storefront (not headless), with the reason theme access failed. Never show the Shopify option for any other store. Pick the card `mode`: `connect` when no code host is connected (no form; the user connects, then clicks Get fix and you find the repository), `choose` when several repositories could match, `enter` only when the code was not found. Never ask the user to type a repository you could find yourself. If the card cannot be rendered, send the same content as text, in this order.

**What we know** (from Noibu data)
- What is happening: the observed failure or metric, its impact and window.
- Where it points: only locations the evidence shows, such as stack-frame file and function, page or template, element selector, device.
- Likely cause: one sentence, marked as a hypothesis.

**Get the complete fix**
"A specific fix needs to read your site's code." Then the platform-aware connect step:
- Shopify theme store where theme access failed: say Noibu cannot read this store's theme yet, with the actual reason when known, and offer the code-host option too.
- Everyone else: "Connect your code host (GitHub, Bitbucket or another) in ChatGPT. I'll find the repository, or you can name it."
- Close with: "Then click **Get fix** again, or ask me for the fix."

Use the native Connect/reauthorization or plugin install suggestions (GitHub and Bitbucket) when the host offers them; otherwise point to the ChatGPT plugin directory. Never ask for a repository before trying to find it. A 403/404 means missing organization or repository authorization: name the access needed without broadening scope. Never ask for tokens, install a direct MCP server or require Codex.

Offer **Open a Ticket** as the alternative: an evidence pack for a developer (stack frames, pages, sessions, reproduction details, acceptance checks) with no proposed code.

## Response: fix

- First line names the source: `Using acme/storefront @ main (GitHub)` or `Using Shopify theme "Dawn" (live, #1234) via Noibu`, followed by "Different source? Tell me which."
- Root cause: what in the code produces the observed evidence, tied to inspected file and line.
- The change: a before/after diff limited to the files needed. Prefer root-cause fixes; a guard that only hides the error is labelled as symptom suppression.
- Confidence and remaining unknowns, such as an unknown deployed revision.
- Verify: how to confirm in Noibu after deploy (issue occurrences, p75 for the page and device) plus any manual check.
- Next: **Prepare draft PR** for a code host or **Preview on a theme copy** for a Shopify theme. Each needs its own explicit request and native approvals. Never merge, publish or deploy.

No hedging filler ("you may want to", "consider", "typically"). If inspection cannot support a specific change, say what is missing instead.

## Remember the source

Do not send the user through the business-context interview for this. After the first verified fix for a store, offer once, in one line: "Remember <source> for <domain> so Get fix works straight away next time?" On yes, save with `noibu_insert_business_context` (`domainNumId`):
- Existing context: the complete current Markdown with only the `Source code` entry added or updated under Tech stack. Writes replace the whole document, so never save a partial one.
- No context yet: a minimal document with the sentinel line, `# <domain> — Business context`, a `## Tech stack & site architecture` section holding the `Source code` entry, and a line saying the full business context has not been built yet.

Entry format: `- **Source code:** <provider> — <owner/repo> @ <branch>` or `- **Source code:** Shopify theme via Noibu (live theme)`. On no, use it for this conversation only. A failed save never blocks the fix.

## Writes

Get fix and Investigate are read-only apart from the theme-change bookkeeping above. Edits, draft PRs and theme previews need a separate explicit request naming the change and target, plus native approvals. If write support is missing, give the patch and say no change was made.
