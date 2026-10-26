// Reusable server-only Sites adapter. All config and action selection are trusted
// source; instantiate per request with the official Sites connector binding.
const READS = new Set(['noibu_search_sessions', 'noibu_get_page_visits', 'noibu_search_errors', 'noibu_list_priority_errors', 'noibu_list_ab_tests']);
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const privateHeaders = {'content-type': 'application/json', 'cache-control': 'private, no-store', 'vary': 'Cookie'};
function response(value, status = 200) {return new Response(JSON.stringify(value), {status, headers: privateHeaders});}
function assert(condition, message) {if (!condition) throw new Error(message);}
export function validateReadPlan(config) {
  assert(config && uuid.test(config.domainId), 'Invalid configured domain');
  assert(typeof config.connectorId === 'string' && config.connectorId, 'Missing discovered connector');
  assert(Number.isInteger(config.windowHours) && config.windowHours > 0 && config.windowHours <= 24 * 366, 'Invalid relative window');
  assert(Array.isArray(config.queries) && config.queries.length > 0 && config.queries.length <= 20, 'Read plan needs 1–20 queries');
  const ids = new Set();
  for (const query of config.queries) {
    assert(query && typeof query.id === 'string' && !ids.has(query.id), 'Duplicate query identity');
    ids.add(query.id);
    assert(READS.has(query.tool) && typeof query.actionName === 'string' && query.actionName, 'Unapproved read action');
    assert(['current', 'prior'].includes(query.period), 'Invalid period');
    assert(query.args && query.args.domainId === config.domainId, 'Query domain mismatch');
    assert(!('headers' in query.args) && !('token' in query.args), 'Credentials do not belong in a read plan');
    if (query.tool === 'noibu_search_sessions') {
      const q = query.args.input?.queryInput;
      assert(q && q.orderBy && Number.isInteger(q.limit) && q.limit > 0 && q.limit <= 100, 'Session query needs orderBy and bounded limit');
      assert(query.rangePath === 'input.periodOptions.dateTimeRange', 'Session period path mismatch');
    } else {
      // Non-session tools vary by schema. The author must bind the actual schema
      // and its bounded arguments; only these fixed time-path forms are supported.
      assert(['input.periodOptions.dateTimeRange', 'input.dateTimeRange', 'dateTimeRange', null].includes(query.rangePath), 'Unsupported time path');
      assert(Number.isInteger(query.rowCap) && query.rowCap > 0 && query.rowCap <= 100, 'Read query needs a verified row cap');
    }
  }
  return config;
}
function setRange(args, path, range) {
  if (path === null) return;
  const parts = path.split('.');
  let item = args;
  for (const part of parts.slice(0, -1)) {
    assert(item[part] && typeof item[part] === 'object', 'Missing configured period envelope');
    item = item[part];
  }
  item[parts.at(-1)] = range;
}
export function createReportHandler({config, visitor, invoke, buildReport, now = () => new Date()}) {
  validateReadPlan(config);
  assert(typeof invoke === 'function' && typeof buildReport === 'function', 'Missing request-scoped adapter/normalizer');
  return async request => {
    if (request.method !== 'POST') return response({status: 'invalid_request', message: 'Use POST'}, 405);
    const origin = new URL(request.url).origin;
    if (request.headers.get('origin') !== origin) return response({status: 'forbidden', message: 'Same-origin request required'}, 403);
    if (!visitor?.id) return response({status: 'unauthenticated', message: 'Sign in with ChatGPT through the Sites platform'}, 401);
    // No browser-provided domains, actions, credentials, or arguments accepted.
    const body = await request.text();
    if (body.length > 1024) return response({status: 'invalid_request', message: 'Request body too large'}, 400);
    if (body.trim() && body.trim() !== '{}') return response({status: 'invalid_request', message: 'Request overrides are not supported'}, 400);
    const end = now();
    const start = new Date(end.getTime() - config.windowHours * 3600000);
    const previous = new Date(start.getTime() - config.windowHours * 3600000);
    const ranges = {current: {start: start.toISOString(), end: end.toISOString()}, prior: {start: previous.toISOString(), end: start.toISOString()}};
    const results = {};
    for (const query of config.queries) {
      const args = structuredClone(query.args);
      setRange(args, query.rangePath, {startTime: ranges[query.period].start, endTime: ranges[query.period].end});
      args.rationale = 'Viewer requested fresh Noibu dashboard data for the configured store';
      args.skill = config.workflow;
      args.skillStep = 'site-refresh';
      args.skillVersion = '0.3.1';
      let value;
      try {value = await invoke(config.connectorId, query.actionName, args);}
      catch {return response({status: 'error', message: 'Connector request failed; previously displayed values are stale'}, 502);}
      if (!value || value.status !== 'success') {
        // Preserve diagnostics, retry timing, and provider result without
        // converting auth/policy failures or HTTP 200 to successful analytics.
        return response(value || {status: 'error', message: 'Empty connector response'}, 502);
      }
      if (value.result?.isError) return response({status: 'error', message: 'Noibu returned a tool error; data was not refreshed'}, 502);
      results[query.id] = value.result;
    }
    try {
      const report = await buildReport(results, {ranges, generatedAt: end.toISOString(), domainId: config.domainId, workflow: config.workflow});
      assert(report?.schema === 'noibu.presentation/1' && report.domain?.id === config.domainId && report.workflow === config.workflow && report.generatedAt === end.toISOString(), 'Normalizer returned invalid or stale report');
      assert(report.window?.start === ranges.current.start && report.window?.end === ranges.current.end, 'Report period mismatch');
      return response({status: 'success', report});
    } catch {return response({status: 'error', message: 'New data could not be normalized; previously displayed values are stale'}, 502);}
  };
}
