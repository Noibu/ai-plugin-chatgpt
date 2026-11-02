import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createDirectOAuth, createTokenCipher, selectConnection} from '../skills/querying-noibu-data/assets/sites/direct-oauth.mjs';
import {createReportHandler, validateReadPlan} from '../skills/querying-noibu-data/assets/sites/site-report.mjs';
const tool = 'noibu_search_sessions';
function fixture() {
  let time = 0, refreshError = false, mcpStatus = 200, omitRefresh = false;
  const states = new Map(), tokens = new Map(), locks = new Map(), requests = [];
  const config = {siteId: 'site', origin: 'https://site.example', clientId: 'client', authorizationEndpoint: 'https://noibu.example/authorize', tokenEndpoint: 'https://noibu.example/token', resource: 'https://noibu.example', mcpEndpoint: 'https://noibu.example/mcp', redirectUri: 'https://site.example/api/noibu/callback', allowedTools: [tool]};
  const store = {putState: async (k,v) => states.set(k,v), consumeState: async k => {const v=states.get(k); states.delete(k); return v;}, getTokens: async k => tokens.get(k), putTokens: async (k,v) => tokens.set(k,v), deleteTokens: async k => tokens.delete(k), withLock: async (k, op) => {const previous = locks.get(k) || Promise.resolve(); const next = previous.catch(()=>{}).then(op); locks.set(k,next); return next;}};
  const cipher = createTokenCipher(new Uint8Array(32).fill(7));
  const fetchImpl = async (url, options) => {
    requests.push({url, ...options});
    if (url === config.tokenEndpoint) {
      const refresh = options.body.get('grant_type') === 'refresh_token';
      if (refresh && refreshError) return Response.json({error: 'invalid_grant'}, {status: 400});
      return Response.json({access_token: refresh ? 'renewed' : options.body.get('code'), token_type: 'Bearer', expires_in: 3600, ...(refresh && omitRefresh ? {} : {refresh_token: refresh ? 'rotated' : 'initial-refresh'})});
    }
    if (mcpStatus !== 200) return new Response('', {status: mcpStatus});
    const request = JSON.parse(options.body);
    if (!request.id) return new Response(null, {status: 202});
    return Response.json({jsonrpc: '2.0', id: request.id, result: request.method === 'tools/call' ? {structuredContent: {viewerToken: options.headers.Authorization, args: request.params.arguments}} : {capabilities: {}}});
  };
  const oauth = createDirectOAuth({config, store, cipher, fetchImpl, now: () => time});
  const connect = async (viewer, code = viewer) => {const begin = await oauth.begin(viewer); const state = new URL(begin.authorizationUrl).searchParams.get('state'); await oauth.complete(viewer, {state, cookie: begin.cookie, code}); return {state, cookie: begin.cookie, code};};
  return {oauth, connect, requests, tokens, cipher, config, expire:()=>{time+=3600000;}, revoke:()=>{refreshError=true;}, deny:status=>{mcpStatus=status;}, preserveRefresh:()=>{omitRefresh=true;}};
}
test('native first; only observed missing integration permits direct OAuth', () => {
  assert.equal(selectConnection({native:'available',directSupported:true}), 'native-sites');
  assert.equal(selectConnection({native:'missing',directSupported:true}), 'direct-oauth');
  for (const native of ['denied','unknown','missing']) assert.equal(selectConnection({native,directSupported:false}), 'blocked');
  assert.equal(selectConnection({native:'available',restriction:true}), 'blocked');
});
test('PKCE, encrypted tokens and refresh rotation with subsequent provider read', async () => {
  const f=fixture(); const callback = await f.connect('alice');
  const auth = f.requests[0].body;
  assert.ok(auth.get('code_verifier')); assert.equal(auth.get('redirect_uri'),f.config.redirectUri);
  assert.equal([...f.tokens.values()][0].includes('initial-refresh'),false);
  f.expire(); await f.oauth.call('alice',tool,{domainId:'allowed', filters:['device=mobile']});
  const refresh=f.requests.find(r=>r.body instanceof URLSearchParams && r.body.get('grant_type')==='refresh_token');
  assert.equal(refresh.body.get('refresh_token'),'initial-refresh');
  const stored=await f.cipher.open([...f.tokens.values()][0],JSON.stringify(['site','alice']));
  assert.equal(stored.refresh_token,'rotated');
  const call=f.requests.find(r=>typeof r.body==='string' && JSON.parse(r.body).method==='tools/call');
  assert.equal(call.headers.Authorization,'Bearer renewed'); assert.deepEqual(JSON.parse(call.body).params.arguments.filters,['device=mobile']);
  await assert.rejects(()=>f.oauth.complete('alice',callback),/INVALID_OAUTH_STATE/);
});
test('two viewers cannot use each other’s tokens or callback', async () => {
  const f=fixture(); await f.connect('alice'); await f.connect('bob');
  const a=await f.oauth.call('alice',tool,{}), b=await f.oauth.call('bob',tool,{});
  assert.equal(a.structuredContent.viewerToken,'Bearer alice'); assert.equal(b.structuredContent.viewerToken,'Bearer bob');
  await assert.rejects(()=>f.cipher.open([...f.tokens.values()][0],JSON.stringify(['site','bob'])));
  await assert.rejects(()=>f.oauth.call('',tool,{}),/SIGN_IN_REQUIRED/);
  const start=await f.oauth.begin('alice');
  await assert.rejects(()=>f.oauth.complete('bob',{state:new URL(start.authorizationUrl).searchParams.get('state'),cookie:start.cookie,code:'x'}),/INVALID_OAUTH_STATE/);
});
test('expired state, wrong cookie, absent/revoked authorization and permission denial fail closed', async () => {
  const f=fixture(); let start=await f.oauth.begin('alice'); f.expire();
  await assert.rejects(()=>f.oauth.complete('alice',{state:new URL(start.authorizationUrl).searchParams.get('state'),cookie:start.cookie,code:'x'}),/INVALID_OAUTH_STATE/);
  start=await f.oauth.begin('alice');
  await assert.rejects(()=>f.oauth.complete('alice',{state:new URL(start.authorizationUrl).searchParams.get('state'),cookie:'wrong',code:'x'}),/INVALID_OAUTH_STATE/);
  await assert.rejects(()=>f.oauth.call('alice',tool,{}),/NOIBU_CONNECT_REQUIRED/);
  await f.connect('alice'); f.deny(403);
  await assert.rejects(()=>f.oauth.call('alice',tool,{domainId:'forbidden'}),/NOIBU_PERMISSION_DENIED/);
  assert.equal(f.tokens.size,1); f.deny(401);
  await assert.rejects(()=>f.oauth.call('alice',tool,{}),/NOIBU_RECONNECT_REQUIRED/);
  f.expire(); f.revoke(); await assert.rejects(()=>f.oauth.call('alice',tool,{}),/NOIBU_RECONNECT_REQUIRED/);
  assert.equal(f.tokens.size,0);
});
test('preserve refresh token when omitted, serialize concurrent refresh, reject writes and disconnect', async () => {
  const f=fixture(); await f.connect('alice'); f.preserveRefresh(); f.expire();
  await Promise.all([f.oauth.call('alice',tool,{}),f.oauth.call('alice',tool,{})]);
  assert.equal(f.requests.filter(r=>r.body instanceof URLSearchParams && r.body.get('grant_type')==='refresh_token').length,1);
  assert.equal((await f.cipher.open([...f.tokens.values()][0],JSON.stringify(['site','alice']))).refresh_token,'initial-refresh');
  await assert.rejects(()=>f.oauth.call('alice','noibu_write',{}),/ACTION_NOT_ALLOWED/);
  await f.oauth.disconnect('alice'); assert.equal(f.tokens.size,0);
});
const domainId='12345678-1234-1234-1234-123456789012';
const plan = {connectionMethod:'direct-oauth',domainId,workflow:'store-pulse',windowHours:24,queries:[{id:'sessions',tool,period:'current',rangePath:'input.periodOptions.dateTimeRange',args:{domainId,input:{periodOptions:{},queryInput:{orderBy:{},limit:1}}}}]};
test('read plan supports both transports and handler restricts origin and overrides', async () => {
  validateReadPlan(plan);
  assert.throws(()=>validateReadPlan({...plan,connectionMethod:'native-sites'}),/Missing discovered connector/);
  validateReadPlan({...plan,connectionMethod:'native-sites',connectorId:'native',queries:[{...plan.queries[0],actionName:'read'}]});
  const handler=createReportHandler({config:plan,visitor:{id:'alice'},invoke:async()=>{throw new Error('NOIBU_RECONNECT_REQUIRED');},buildReport:()=>{}});
  const request=(body='{}',origin='https://site.example')=>new Request('https://site.example/api/noibu/report',{method:'POST',headers:{origin},body});
  assert.equal((await handler(request('{}','https://attacker.example'))).status,403);
  assert.equal((await handler(request('{"domainId":"override"}'))).status,400);
  const result=await handler(request()); assert.equal(result.status,401); assert.equal((await result.json()).noibuSignInPath,'/api/noibu/connect');
});
test('direct report executes a fresh allowed query and normalizes only its result', async () => {
  const f=fixture(); await f.connect('alice');
  const handler=createReportHandler({config:plan,visitor:{id:'alice'},invoke:async(_,name,args)=>({status:'success',result:await f.oauth.call('alice',name,args)}),buildReport:async(results,meta)=>({schema:'noibu.presentation/1',domain:{id:meta.domainId},workflow:meta.workflow,generatedAt:meta.generatedAt,window:meta.ranges.current})});
  const res=await handler(new Request('https://site.example/api/noibu/report',{method:'POST',headers:{origin:'https://site.example'},body:'{}'}));
  assert.equal(res.status,200); const data=await res.json(); assert.equal(data.status,'success'); assert.equal(JSON.stringify(data).includes('Bearer'),false);
});
test('native handler retains native binding and direct helper rejects write-tool configuration', async () => {
  let seen;
  const config={...plan,connectionMethod:'native-sites',connectorId:'native-id',queries:[{...plan.queries[0],actionName:'sessions-action'}]};
  const handler=createReportHandler({config,visitor:{id:'alice'},invoke:async(...args)=>{seen=args;return {status:'success',result:{}};},buildReport:async(_,meta)=>({schema:'noibu.presentation/1',domain:{id:meta.domainId},workflow:meta.workflow,generatedAt:meta.generatedAt,window:meta.ranges.current})});
  assert.equal((await handler(new Request('https://site.example/api/noibu/report',{method:'POST',headers:{origin:'https://site.example'},body:'{}'}))).status,200);
  assert.equal(seen[0],'native-id'); assert.equal(seen[1],'sessions-action');
  assert.throws(()=>createDirectOAuth({config:{...fixture().config,allowedTools:['noibu_write']}}),/INVALID_OAUTH_CONFIG/);
});
test('transient MCP failure retains authorization', async () => {
  const f=fixture(); await f.connect('alice'); f.deny(503);
  await assert.rejects(()=>f.oauth.call('alice',tool,{}),/NOIBU_MCP_UNAVAILABLE/);
  assert.equal(f.tokens.size,1);
});
