// Server-only D1 persistence. No HTTP endpoint, credentials, connector or scheduler.
// Include this schema in an inspected migration; never run DDL in a request.
export const snapshotSchemaSQL = `CREATE TABLE noibu_report_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scope TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  report_json TEXT NOT NULL,
  verification_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  UNIQUE(scope, content_hash)
);`;

const workflows = new Set(['store-pulse', 'checkout-analysis', 'product-analysis', 'segment-analysis']);
const fields = new Set(['schema','reportId','workflow','domain','window','generatedAt','summary','kpis','funnel','funnelContext','highlights','tables','findings','caveats','timezone','capabilities','contextHash']);
const iso = value => typeof value === 'string' && /(?:Z|[+-]\d\d:\d\d)$/.test(value) && Number.isFinite(Date.parse(value));
const plain = value => value !== null && typeof value === 'object' && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
const check = (value, message) => {if (!value) throw new Error(message);};
function canonical(value) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number') {check(Number.isFinite(value), 'Nonfinite snapshot number'); return JSON.stringify(value);}
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  check(plain(value), 'Snapshot must contain plain JSON data');
  return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
}
function scopeFor(value) {
  check(plain(value) && workflows.has(value.workflow) && plain(value.domain), 'Unsupported snapshot scope');
  check(typeof value.domain.name === 'string' && /^[a-zA-Z0-9.-]{1,253}$/.test(value.domain.name), 'Invalid snapshot domain');
  if (value.domain.id !== undefined) check(typeof value.domain.id === 'string' && /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(value.domain.id), 'Invalid domain UUID');
  return value.workflow + ':' + (value.domain.id || value.domain.name.toLowerCase());
}
export async function prepareSnapshot(report, verification) {
  check(plain(report) && Object.keys(report).every(key => fields.has(key)), 'Unsupported report fields');
  const scope = scopeFor(report);
  check(report.schema === 'noibu.presentation/1' && typeof report.reportId === 'string' && /^[a-z0-9][a-z0-9-]{0,99}$/.test(report.reportId), 'Invalid report identity');
  check(iso(report.generatedAt) && plain(report.window) && iso(report.window.start) && iso(report.window.end) && Date.parse(report.window.start) < Date.parse(report.window.end), 'Invalid report period');
  check(typeof report.summary === 'string' && report.summary.trim(), 'Missing report summary');
  const collections = {kpis:8, funnel:12, highlights:6, tables:8, findings:12, caveats:12};
  for (const [key, cap] of Object.entries(collections)) check(report[key] === undefined || Array.isArray(report[key]) && report[key].length <= cap, 'Invalid report collection');
  const shape = (value, keys) => plain(value) && Object.keys(value).every(key => keys.includes(key));
  for (const x of report.kpis || []) check(shape(x,['label','value','change','tone']) && typeof x.label === 'string' && typeof x.value === 'string', 'Invalid KPI');
  for (const x of report.funnel || []) check(shape(x,['label','count','prior','display','detail','change','tone']) && typeof x.label === 'string' && Object.hasOwn(x,'count') && [x.count,x.prior].every(n => n === undefined || n === null || Number.isSafeInteger(n) && n >= 0) && !(x.count === null && x.display !== undefined), 'Invalid funnel');
  for (const x of report.highlights || []) check(shape(x,['label','value','detail']) && typeof x.label === 'string' && typeof x.value === 'string', 'Invalid highlight');
  for (const x of report.findings || []) check(shape(x,['id','title','evidence','impact','fix','issueId','category','tag']) && ['id','title','evidence'].every(key => typeof x[key] === 'string'), 'Invalid finding');
  for (const x of report.tables || []) check(shape(x,['title','columns','rows','kind','note','numericColumns']) && typeof x.title === 'string' && Array.isArray(x.columns) && x.columns.length > 0 && x.columns.length <= 8 && x.columns.every(c => typeof c === 'string') && Array.isArray(x.rows) && x.rows.length <= 50 && x.rows.every(row => Array.isArray(row) && row.length === x.columns.length && row.every(c => c === null || ['string','number'].includes(typeof c))), 'Invalid table');
  check((report.caveats || []).every(x => typeof x === 'string'), 'Invalid caveats');
  check(Object.keys(report.domain).every(key => ['id','name'].includes(key)) && Object.keys(report.window).every(key => ['start','end','label'].includes(key)), 'Unknown report identity fields');
  if (report.capabilities !== undefined) check(shape(report.capabilities,['createDraft','ignoreIssue','draftPr','createTicket','persistContext']) && Object.values(report.capabilities).every(x => typeof x === 'boolean'), 'Invalid capabilities');
  check(plain(verification) && Object.keys(verification).every(key => ['checkedAt','checks','limitations'].includes(key)) && iso(verification.checkedAt), 'Missing verification evidence');
  check(Array.isArray(verification.checks) && verification.checks.length > 0 && verification.checks.length <= 50 && verification.checks.every(c => plain(c) && Object.keys(c).every(key => ['name','passed','detail'].includes(key)) && typeof c.name === 'string' && c.name.trim() && c.passed === true && (c.detail === undefined || typeof c.detail === 'string')), 'Failed or missing verification check');
  check(verification.limitations === undefined || Array.isArray(verification.limitations) && verification.limitations.every(x => typeof x === 'string'), 'Invalid verification limitations');
  const reportJSON = canonical(report), verificationJSON = canonical(verification);
  check(new TextEncoder().encode(reportJSON + verificationJSON).length <= 750000, 'Snapshot exceeds storage cap');
  // Changed capture/report IDs alone should not generate duplicate data snapshots.
  const {reportId, generatedAt, ...content} = report;
  const {checkedAt, ...checks} = verification;
  const bytes = new TextEncoder().encode(canonical({content, checks}));
  const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
  return {scope, hash, reportJSON, verificationJSON};
}

export function createSnapshotStore({db, scope, authorize}) {
  check(db && typeof db.prepare === 'function' && typeof authorize === 'function', 'Trusted D1 and authorization adapters required');
  const selectedScope = scopeFor(scope);
  async function allowed(operation) {
    check(await authorize({operation, scope: selectedScope}) === true, 'Snapshot access denied');
  }
  const decode = row => row ? {id:row.id, hash:row.content_hash, report:JSON.parse(row.report_json), verification:JSON.parse(row.verification_json), createdAt:row.created_at, lastSeenAt:row.last_seen_at} : null;
  return {
    async save(report, verification) {
      await allowed('write');
      const snapshot = await prepareSnapshot(report, verification);
      check(snapshot.scope === selectedScope && report.domain.name.toLowerCase() === scope.domain.name.toLowerCase(), 'Snapshot scope mismatch');
      const now = new Date().toISOString();
      const result = await db.prepare('INSERT INTO noibu_report_snapshots (scope, content_hash, report_json, verification_json, created_at, last_seen_at) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(scope, content_hash) DO UPDATE SET last_seen_at = excluded.last_seen_at').bind(selectedScope,snapshot.hash,snapshot.reportJSON,snapshot.verificationJSON,now,now).run();
      check(result?.success !== false, 'Snapshot write failed');
      const row = await db.prepare('SELECT * FROM noibu_report_snapshots WHERE scope = ? AND content_hash = ?').bind(selectedScope,snapshot.hash).first();
      check(row && row.content_hash === snapshot.hash, 'Snapshot readback failed');
      const saved = decode(row);
      const recovered = await prepareSnapshot(saved.report, saved.verification);
      check(recovered.scope === selectedScope && recovered.hash === snapshot.hash, 'Snapshot readback content mismatch');
      return {persisted:true, snapshot:saved};
    },
    async latest() {
      await allowed('read');
      return decode(await db.prepare('SELECT * FROM noibu_report_snapshots WHERE scope = ? ORDER BY last_seen_at DESC, id DESC LIMIT 1').bind(selectedScope).first());
    },
    async history(limit = 20) {
      await allowed('read');
      check(Number.isInteger(limit) && limit > 0 && limit <= 50, 'History limit must be 1–50');
      const result = await db.prepare('SELECT * FROM noibu_report_snapshots WHERE scope = ? ORDER BY last_seen_at DESC, id DESC LIMIT ?').bind(selectedScope,limit).all();
      check(result?.success !== false && Array.isArray(result?.results), 'Snapshot history read failed');
      return result.results.map(decode);
    }
  };
}
