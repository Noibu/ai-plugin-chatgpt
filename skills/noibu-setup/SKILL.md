---
name: noibu-setup
description: Connect and verify the Noibu plugin in ChatGPT, choose an authorized store, and explain optional browser capabilities.
---

# Set up Noibu

- Discover Noibu tools through this plugin's connection. If tools are missing or authentication is required, direct the user to its native **Connect** action and Noibu sign-in; stop until completed. Do not create a second direct-URL connection, loop/poll indefinitely, or request pasted credentials/local configuration.
- Read [shared query guidance](../querying-noibu-data/SKILL.md). Use skill `noibu-setup` and call `noibu_get_current_user` to verify access without exposing unnecessary identity fields.
- List authorized stores with `noibu_list_domains`, `pagination: {limit: 50, offset: 0}` and continued pagination as needed. Use a sole store or ask which one. Empty results may mean missing company/domain scope, not disconnected authentication.
- Resolve the chosen domain, retain UUID/integer `numId`, and load saved business context.
- Offer the relevant workflow; onboarding does not run analytics, scans, drafts or schedules.

## Optional capabilities

Use [runtime guidance](../querying-noibu-data/references/chatgpt-runtime.md) for available outputs/integrations; confirm only verified capabilities.

- Browser access is optional for analytics. Discover the supported browser/interface; installation alone is not usable control.
- Accessibility: follow [execution prerequisites](../accessibility-audit/references/execution-and-review.md). Connected Chrome needs the official extension, organization-permitted full CDP and website/debugging approval; verify readiness/execution. Terminal/Custom permissions do not grant browser execution. If unavailable, offer a clearly labelled limited review with unknown automated counts.
- A/B recommendations and requested DRAFT creation use Noibu; browser previews are optional.
- [Inline presentation](../querying-noibu-data/references/presentation.md) supports reports/action requests when available, not proof that actions completed.
- **Save as Live Site** uses [persistent dashboards](../querying-noibu-data/references/connected-dashboard.md) and [permission preflight](../querying-noibu-data/references/site-permissions.md). Saved private data is not automatically a live feed/schedule; offer weekly refresh with confirmed timing/notification and verified unattended writer. Visitor-connected reads are optional.
- Technical/source actions verify or prompt GitHub connection and repository/ref. Do not change security settings or require Codex/local configuration as ordinary connector setup.
