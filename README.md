# Noibu AI Plugin for ChatGPT

Official Noibu plugin for ChatGPT. Access Noibu products directly from ChatGPT.

## Description

Built for ecommerce, the Noibu plugin bridges the gap between customer experience and revenue by connecting ChatGPT
directly to your store's session, error, and conversion data through Noibu — and to the code hosts and storefront
platforms that put insight into motion. Go beyond analysis: surface what's costing you revenue, get fixes written from
your store's real code, and save reports as private Live Sites with scheduled updates.

## Installation

### ChatGPT

1. On this repo, click **Code → Download ZIP**. Don't extract or modify the file.
2. In ChatGPT, switch to your organization's workspace and open **Workspace settings → Plugins** (requires an admin).
3. Select **Add → Upload plugin**, choose the ZIP, then select **Add plugin** and wait for processing to finish.
4. Click **Connect** and sign in with your Noibu account
5. Pick the store you want to work with — the `noibu-setup` skill walks you through this on first run

No API keys, CLI, or local configuration are needed; authentication is handled by Noibu's OAuth sign-in.

**Tip:** so Noibu links open in the browser where you're already signed in to the Noibu console, go to ChatGPT
**Settings → Browser** and set **Web URL and link open destination** and **Local URL open destination** to
**Default browser**.

### Optional capabilities

- **Fixes from your real code** — connect your Shopify theme through Noibu, or a code host (GitHub, GitLab, Bitbucket and others) with a recognized repository and branch. Without one, you still get the diagnosis plus a connect step.
  Source writes, PRs, and theme previews each need separate authorization.
- **Accessibility audits** — run in the browser using bundled axe-core. Requires ChatGPT desktop with the official
  Chrome extension and approved debugging access.
- **Save as Live Site** — publishes a verified report into a private Site with snapshot history. Weekly refreshes are offered separately.

## What's included

| Skill | What it does |
|---|---|
| `noibu-setup` | Connect Noibu, verify access, and choose an authorized store |
| `store-pulse` | At-a-glance read on store health from the last 24 hours |
| `checkout-analysis` | Checkout funnel drop-off, payment/delivery methods, and checkout errors |
| `product-analysis` | Product and collection performance, views without sales |
| `segment-analysis` | Channel, device, and country performance |
| `tech-diagnosis` | Errors and Core Web Vitals, with root cause and fixes |
| `accessibility-audit` | WCAG 2.1 AA audit with optional fix drafts |
| `accessibility-audit-browser-workaround` | Recover blocked scans or import completed multi-state axe evidence |
| `ab-test-opportunity-finder` | Evidence-backed A/B test ideas and draft tests in Noibu |
| `build-business-context` | Builds the business context file Noibu uses to reason about your store |
| `querying-noibu-data` | Shared query guidance, presentation templates, and ChatGPT runtime rules |

## Repository layout

```
plugin.json   # Plugin manifest (ChatGPT interface metadata under extensions.com.openai)
mcp.json      # Noibu MCP server (https://mcp.noibu.com/mcp, OAuth)
skills/       # One folder per skill: SKILL.md, agents/openai.yaml, references/, scripts/, assets/
assets/       # Logos
```

## How to develop

1. Fork this repo and install the plugin in ChatGPT
2. Connect and authenticate with Noibu
3. Edit skills under `skills/`; ChatGPT-specific behaviour lives in
   `skills/querying-noibu-data/references/chatgpt-runtime.md`

## Documentation
https://help.noibu.com/articles/4186054264-noibu-plugin-installation-for-chatgpt

## Example Use Cases

### Example 1:

**Check on your store in seconds**: How is my store doing in the last 24 hours?

### Example 2:

**Optimize your checkout**: Find where shoppers are dropping off, the payment and delivery methods they're using, and
the technical issues hurting conversion, then tackle the top fixes.

### Example 3:

**Resolve technical issues at the source**: What errors and performance issues are costing my store the most revenue,
and help me fix them in my theme or repo.

### Example 4:

**Turn product views into sales**: Find which products and collections are getting views but no sales, diagnose
why they aren't converting, and execute on the biggest opportunities.

### Example 5:

**Find what to test next**: Find evidence-backed A/B tests to improve add-to-cart rate, and draft the best one in Noibu.

### Example 6:

**Shift marketing spend with site behaviour**: Surface which channels are sending high-quality traffic, identify
how to lift upper-funnel conversion, and reallocate budget accordingly.

## License

MIT
