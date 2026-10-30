// SERVER ONLY. Host adapters must enforce Site identity and durable isolation.
// See references/direct-oauth.md before wiring routes or storage.
const READS = new Set(['noibu_search_sessions', 'noibu_get_page_visits', 'noibu_search_errors', 'noibu_list_priority_errors', 'noibu_list_ab_tests']);
const b64 = bytes => btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
const un64 = value => Uint8Array.from(atob(value.replaceAll('-', '+').replaceAll('_', '/')), c => c.charCodeAt(0));
const random = () => b64(crypto.getRandomValues(new Uint8Array(32)));
const fail = code => {throw new Error(code);};

export function selectConnection({native, directSupported, restriction}) {
  // Absence must be positively observed; unknown/denied are not absence.
  if (restriction || native === 'denied') return 'blocked';
  if (native === 'available') return 'native-sites';
  if (native === 'missing' && directSupported === true) return 'direct-oauth';
  return 'blocked';
}

export function createTokenCipher(keyBytes) {
  if (!(keyBytes instanceof Uint8Array) || keyBytes.length !== 32) fail('INVALID_TOKEN_KEY');
  const key = crypto.subtle.importKey('raw', keyBytes, 'AES-GCM', false, ['encrypt', 'decrypt']);
  return {
    async seal(value, binding) {
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const data = await crypto.subtle.encrypt({name: 'AES-GCM', iv, additionalData: new TextEncoder().encode(binding)}, await key, new TextEncoder().encode(JSON.stringify(value)));
      return b64(iv) + '.' + b64(new Uint8Array(data));
    },
    async open(value, binding) {
      const [iv, data] = value.split('.');
      return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({name: 'AES-GCM', iv: un64(iv), additionalData: new TextEncoder().encode(binding)}, await key, un64(data))));
    },
  };
}

export function createDirectOAuth({config, store, cipher, fetchImpl = fetch, now = Date.now}) {
  // All config is trusted server config discovered/verified against Noibu metadata.
  const {siteId, origin, clientId, authorizationEndpoint, tokenEndpoint, resource, mcpEndpoint, redirectUri, allowedTools, scopes = []} = config;
  for (const address of [origin, authorizationEndpoint, tokenEndpoint, resource, mcpEndpoint, redirectUri]) {
    const url = new URL(address);
    if (url.protocol !== 'https:' || url.username || url.password || url.hash || url.search) fail('INVALID_OAUTH_ENDPOINT');
  }
  if (!siteId || !clientId || new URL(redirectUri).origin !== origin || !Array.isArray(allowedTools) || !allowedTools.length || allowedTools.some(tool => !READS.has(tool))) fail('INVALID_OAUTH_CONFIG');
  if (!Array.isArray(scopes) || scopes.some(scope => typeof scope !== 'string' || !scope || /\s/.test(scope))) fail('INVALID_OAUTH_SCOPES');
  const binding = viewer => {
    if (typeof viewer !== 'string' || !viewer.trim()) fail('SIGN_IN_REQUIRED');
    return JSON.stringify([siteId, viewer]);
  };
  const postToken = async params => {
    const response = await fetchImpl(tokenEndpoint, {method: 'POST', redirect: 'error', signal: AbortSignal.timeout(15000), headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: new URLSearchParams({...params, client_id: clientId, resource})});
    if (!response.ok) {
      if (response.status === 400 || response.status === 401) fail('NOIBU_RECONNECT_REQUIRED');
      fail('NOIBU_TOKEN_SERVICE_UNAVAILABLE');
    }
    const value = await response.json();
    if (!value.access_token || String(value.token_type).toLowerCase() !== 'bearer' || !Number.isFinite(Number(value.expires_in)) || Number(value.expires_in) <= 0) fail('INVALID_TOKEN_RESPONSE');
    return {...value, expires_at: now() + Number(value.expires_in) * 1000};
  };
  const save = async (key, value) => store.putTokens(key, await cipher.seal(value, key));
  return {
    async begin(viewer) {
      const key = binding(viewer), state = random(), cookie = random(), verifier = random();
      await store.putState(state, {key, cookie, verifier, expiresAt: now() + 600000});
      const url = new URL(authorizationEndpoint);
      url.search = new URLSearchParams({...(scopes.length ? {scope: scopes.join(' ')} : {}), response_type: 'code', client_id: clientId, redirect_uri: redirectUri, resource, state, code_challenge: b64(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)))), code_challenge_method: 'S256'}).toString();
      // Host sets cookie as Secure, HttpOnly, SameSite=Lax with a 10 minute TTL.
      return {authorizationUrl: url.href, cookie};
    },
    async complete(viewer, {state, cookie, code}) {
      const key = binding(viewer);
      if (!state || !cookie || !code) fail('INVALID_OAUTH_CALLBACK');
      const pending = await store.consumeState(state); // atomic single-use removal
      if (!pending || pending.key !== key || pending.cookie !== cookie || pending.expiresAt <= now()) fail('INVALID_OAUTH_STATE');
      const tokens = await postToken({grant_type: 'authorization_code', code, code_verifier: pending.verifier, redirect_uri: redirectUri});
      if (!tokens.refresh_token) fail('NOIBU_REFRESH_TOKEN_REQUIRED');
      await store.withLock(key, () => save(key, tokens));
      // Never return tokens to an HTTP route/browser.
      return {connected: true};
    },
    async disconnect(viewer) {
      const key = binding(viewer);
      await store.withLock(key, () => store.deleteTokens(key));
    },
    async call(viewer, tool, args) {
      const key = binding(viewer);
      if (!allowedTools.includes(tool)) fail('ACTION_NOT_ALLOWED');
      // Serialize refresh and calls per Site/viewer, including across workers.
      return store.withLock(key, async () => {
        const stored = await store.getTokens(key);
        if (!stored) fail('NOIBU_CONNECT_REQUIRED');
        let tokens = await cipher.open(stored, key);
        if (tokens.expires_at <= now() + 60000) {
          if (!tokens.refresh_token) fail('NOIBU_RECONNECT_REQUIRED');
          try {
            const next = await postToken({grant_type: 'refresh_token', refresh_token: tokens.refresh_token});
            tokens = {...next, refresh_token: next.refresh_token || tokens.refresh_token};
            await save(key, tokens);
          } catch (error) {
            if (error.message === 'NOIBU_RECONNECT_REQUIRED') await store.deleteTokens(key);
            throw error;
          }
        }
        let session, id = 0;
        const rpc = async (method, params, notification = false) => {
          const headers = {'Content-Type': 'application/json', Accept: 'application/json, text/event-stream', Authorization: 'Bearer ' + tokens.access_token};
          if (session) {headers['Mcp-Session-Id'] = session; headers['MCP-Protocol-Version'] = '2025-03-26';}
          const response = await fetchImpl(mcpEndpoint, {method: 'POST', redirect: 'error', signal: AbortSignal.timeout(45000), headers, body: JSON.stringify({jsonrpc: '2.0', ...(notification ? {} : {id: ++id}), method, params})});
          if (response.status === 401) fail('NOIBU_RECONNECT_REQUIRED');
          if (response.status === 403) fail('NOIBU_PERMISSION_DENIED');
          if (!response.ok) fail('NOIBU_MCP_UNAVAILABLE');
          session = response.headers.get('mcp-session-id') || session;
          if (notification) return;
          const text = await response.text();
          let messages;
          try {messages = [JSON.parse(text)];} catch {
            messages = text.split(/\r?\n\r?\n/).map(block => block.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')).filter(Boolean).map(data => JSON.parse(data));
          }
          const result = messages.find(value => value.id === id);
          if (!result || result.error || result.result?.isError) fail('NOIBU_MCP_ERROR');
          return result.result;
        };
        await rpc('initialize', {protocolVersion: '2025-03-26', capabilities: {}, clientInfo: {name: 'Noibu Site dashboard', version: '1.0.0'}});
        await rpc('notifications/initialized', {}, true);
        return rpc('tools/call', {name: tool, arguments: args});
      });
    },
  };
}
