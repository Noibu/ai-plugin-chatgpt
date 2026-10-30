# Direct Noibu OAuth for visitor-connected Sites

Use only after completed native connector discovery shows Noibu is missing and the runtime permits this connection. Prefer the native integration whenever available. Unknown eligibility, a denied integration, managed restrictions and rejected approvals are blockers, not fallback triggers. Use `selectConnection` in [the server helper](../assets/sites/direct-oauth.mjs) with observed capability evidence; it defaults to blocked.

## Host wiring

The helper is server-only source, not a deployed service. Use a supported dynamic Sites runtime and its current trusted viewer identity, storage, migrations and secret APIs. Keep Site access private unless the user separately requests an audience change. OAuth permission to read Noibu and permission to visit the Site remain separate.

- Verify Noibu's current OAuth/protected-resource metadata at the official `https://mcp.noibu.com` service. Resolve authorization/token endpoints, MCP resource, supported scopes, client registration and exact callback from actual metadata; do not guess endpoints or reuse the example dashboard's client ID. Register a separate public authorization-code client with S256 PKCE where supported. Noibu metadata must support refresh tokens; if registration, callbacks or refresh grants are unavailable, report that capability blocker.
- Instantiate `createDirectOAuth` with trusted `siteId`, HTTPS `origin`, `clientId`, `authorizationEndpoint`, `tokenEndpoint`, `resource`, `mcpEndpoint`, `redirectUri`, metadata-supported `scopes` (if required), and an explicit subset of allowed analytics read tools. The helper rejects arbitrary write tools and redirects. Do not let browser values choose endpoints, tool names, domains or credentials. Respect provider rate limits; no automatic retry loops or permission fallbacks on 403.
- Implement the `store` adapter with `putState(state, record)`, atomic single-use `consumeState(state)`, `getTokens(key)`, `putTokens(key, ciphertext)`, `deleteTokens(key)` and `withLock(key, operation)`. State records include PKCE verifiers: protect this server-side table and expire records after ten minutes. Tokens are scoped to both Site and authenticated viewer. `withLock` must serialize the entire operation across worker instances, using a supported durable coordination mechanism; an in-memory mutex is insufficient for production refresh-token rotation. Provision tables through migrations, never inside requests.
- Use `createTokenCipher` with 32 random bytes from a managed server secret. It uses AES-GCM with a fresh IV and Site/viewer binding as authenticated data. Store ciphertext only. Keep keys, tokens, authorization codes, PKCE verifiers and cookies out of source, archives, logs, error bodies, report JSON, prompts and browser storage. Manage encryption-key rotation with the host's secret/storage lifecycle; disconnect/reconnect rather than silently discarding unreadable records.
- A connect route gets the viewer from trusted Sites identity, calls `begin(viewerId)`, sets the returned cookie as Secure, HttpOnly, SameSite=Lax with a ten-minute lifetime scoped to the callback path, and redirects to `authorizationUrl`. The OAuth callback resolves the same viewer, checks provider denial/error, reads the cookie, and calls `complete(viewerId, {state, cookie, code})`. Clear the cookie, redirect to a clean dashboard URL, send `Cache-Control: private, no-store` and `Referrer-Policy: no-referrer`, and redact callback query strings in access logs. Fail on missing identity, wrong viewer/cookie, expired or reused state. Never return tokens to the browser. The host must verify its reverse proxy permits the callback and preserves trusted identity.
- Protect report/refresh/disconnect routes with trusted identity, same-origin/CSRF checks and no-store responses. `disconnect` removes this viewer's local authorization; separately use provider revocation when supported. A provider 401 requires reconnect, a 403 explains permission denial, and transient service errors retain stale data without deleting valid authorization. Do not log raw provider bodies or errors containing credentials.

## Report adapter

Reuse `validateReadPlan` and `createReportHandler` from `site-report.mjs` with `connectionMethod: "direct-oauth"`. Native mode remains the default and still requires the discovered `connectorId` and action names. In direct mode `query.tool` selects a validated read tool; no native connector ID is required.

Construct the adapter per request using the trusted viewer:

```js
const invoke = async (_connectorId, tool, args) => {
  const result = await oauth.call(viewer.id, tool, args);
  return {status: 'success', result};
};
const handler = createReportHandler({config, visitor: viewer, invoke, buildReport});
return handler(request);
```

`buildReport` must normalize and validate actual Noibu structured/text result envelopes and provider-level errors, totals, currency, domain and date windows. HTTP success is not analytics success. The shared handler rejects browser overrides; additional dashboard filters need a host adapter that validates a fixed schema, applies permitted filters to the actual queries, and tests every exposed filter. Do not show controls that merely relabel unchanged results. Include viewer/Site/domain/filter/window in any server cache key; prefer private no-store responses and never share results across viewers.

The shared client recognizes `noibuSignInPath` for same-origin reconnect links. Reconnect links are generated by server code on actual authentication failure; a policy denial must not start a sign-in loop. When the viewer signs out or switches accounts, clear old rendered data before loading the new viewer. Refresh failure can preserve stale values only within the same authenticated viewer.

## Required verification

Run `node --test tests/*.test.mjs` and `python3 -m unittest discover -s tests -p 'test_*.py'` from the repository root for package checks. These use simulated providers and do not prove hosted runtime readiness.

Before claiming a Site is live-connected, record hosted evidence for initial provider reads, manual Refresh, forced access-token expiry followed by refresh and an authenticated read (including rotation/preservation), and every filter's effect on provider queries and returned cohorts. Use two authorized test viewers with different Noibu permissions: verify separate token records and results, forbidden-domain rejection, sign-out/account switching and no cross-viewer cache reuse. Test expired/replayed/wrong-viewer state, absent connection, revoked refresh token, provider 401/403 and transient failures. Verify reconnect/stale states and that no token reaches browser responses or logs. If a second test account or another prerequisite is unavailable, explicitly leave that verification pending; do not mark readiness from one account's success.

An OAuth viewer connection does not authorize unattended background reads. Follow the separate linked-schedule/writer workflow for scheduled updates. Snapshots always retain their snapshot label and capture time.
