"""Build safe ChatGPT inline boards or standalone snapshots; no network or writes."""
import argparse
import hashlib
import html
import importlib.util
import json
import math
import re
from datetime import datetime
from pathlib import Path
from uuid import UUID

HERE = Path(__file__).resolve().parent.parent
WORKFLOWS = {'store-pulse', 'checkout-analysis', 'product-analysis', 'segment-analysis', 'tech-diagnosis', 'accessibility-audit', 'ab-test-opportunity-finder', 'build-business-context', 'querying-noibu-data', 'noibu-setup'}
ANALYTICS = {'store-pulse', 'checkout-analysis', 'product-analysis', 'segment-analysis'}
SCHEDULABLE = WORKFLOWS - {'noibu-setup', 'build-business-context', 'querying-noibu-data'}
FIELDS = {'schema', 'reportId', 'workflow', 'domain', 'window', 'generatedAt', 'summary', 'overviewContext', 'overviewNotes', 'kpis', 'funnel', 'funnelContext', 'highlights', 'tables', 'findings', 'caveats', 'timezone', 'capabilities', 'contextHash', 'noibuLinks', 'auditLayout'}
TONES = {None, 'favorable', 'unfavorable', 'neutral'}
VITALS = {'INP': (200, 500, 'ms'), 'LCP': (2500, 4000, 'ms'), 'CLS': (0.1, 0.25, 'score')}
link_spec = importlib.util.spec_from_file_location('noibu_console_links', Path(__file__).with_name('console_links.py'))
links = importlib.util.module_from_spec(link_spec)
link_spec.loader.exec_module(links)

def require(condition, message):
    if not condition:
        raise ValueError(message)

def text(value, maximum=12000):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum

def timestamp(value):
    require(text(value), 'Missing timestamp')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'Timestamp needs timezone')
    return result

def safe_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')

def escape(value):
    return html.escape(str(value if value is not None else 'Not measured'), quote=True)

def validate_change(item):
    require(item.get('tone') in TONES and ('change' not in item or text(item['change'])), 'Invalid metric change')
    require('changeDirection' not in item or isinstance(item['changeDirection'], str) and item['changeDirection'] in {'up', 'down', 'flat'} and bool(item.get('change')), 'Direction requires a measured change')

def render_change(item):
    if not item.get('change'):
        return ''
    # Direction is explicit evidence metadata, never inferred from formatted prose.
    tone = 'decline' if item.get('changeDirection') == 'down' else item.get('tone') or 'neutral'
    return f'<span class="noibu-delta noibu-{tone}">{escape(item["change"])}</span>'

def validate_links(items, domain_id):
    require(isinstance(items, list) and len(items) <= 8, 'Invalid Noibu links')
    for item in items:
        require(isinstance(item, dict) and set(item) == {'label', 'url', 'source'} and text(item['label'], 100) and text(item['source'], 500), 'Link needs label, URL and evidence source')
        require(domain_id is not None, 'Console links need a resolved domain UUID')
        links.validate_url(item['url'], domain_id)

def validate_performance(value):
    require(isinstance(value, dict) and set(value) <= {'metric', 'value', 'unit', 'percentile', 'page', 'pageGroup', 'device', 'traffic', 'status'}, 'Invalid performance fields')
    require(value.get('metric') in VITALS, 'Unsupported performance metric')
    require(value.get('unit') == VITALS[value['metric']][2] and value.get('percentile') == 'p75', 'Performance cards require p75 and normalized units')
    measured = value.get('value')
    require(measured is None or type(measured) in {int, float} and math.isfinite(measured) and measured >= 0, 'Invalid performance value')
    require(all(key not in value or text(value[key], 1000) for key in ['page', 'pageGroup', 'device', 'status']), 'Invalid performance context')
    if 'traffic' in value:
        traffic = value['traffic']
        require(isinstance(traffic, dict) and set(traffic) == {'count', 'unit'} and traffic['unit'] in {'pageviews', 'visits', 'sessions', 'samples'}, 'Traffic needs its actual population unit')
        require(traffic['count'] is None or type(traffic['count']) is int and traffic['count'] >= 0, 'Invalid performance traffic')

def validate(data):
    require(isinstance(data, dict) and set(data) <= FIELDS, 'Unsupported presentation fields')
    require(data.get('schema') == 'noibu.presentation/1', 'Unsupported presentation schema')
    require(data.get('workflow') in WORKFLOWS, 'Unsupported workflow')
    require('auditLayout' not in data or data['workflow'] == 'accessibility-audit' and data['auditLayout'] in {'summary-actions', 'detailed'}, 'Invalid audit layout')
    require(text(data.get('reportId'), 100) and re.fullmatch(r'[a-z0-9][a-z0-9-]*', data['reportId']), 'Invalid report identity')
    domain = data.get('domain', {})
    require(isinstance(domain, dict) and set(domain) <= {'name', 'id'}, 'Invalid domain fields')
    require(text(domain.get('name'), 253) and re.fullmatch(r'[a-zA-Z0-9.-]+', domain['name']), 'Invalid domain name')
    if domain.get('id'):
        UUID(domain['id'])
    timestamp(data.get('generatedAt'))
    window = data.get('window', {})
    require(isinstance(window, dict) and set(window) <= {'start', 'end', 'label'}, 'Invalid window')
    require(timestamp(window.get('start')) < timestamp(window.get('end')), 'Invalid time range')
    require(text(data.get('summary')), 'Missing summary')
    require('overviewContext' not in data or text(data['overviewContext'], 1000), 'Invalid overview context')
    require('overviewNotes' not in data or data['workflow'] == 'segment-analysis' and isinstance(data['overviewNotes'], list) and len(data['overviewNotes']) <= 3 and all(text(note, 1000) for note in data['overviewNotes']), 'Invalid overview notes')
    require(isinstance(data.get('capabilities', {}), dict), 'Invalid capabilities')
    allowed_caps = {'createDraft', 'ignoreIssue', 'draftPr', 'createTicket', 'persistContext'}
    require(set(data.get('capabilities', {})) <= allowed_caps and all(type(x) is bool for x in data.get('capabilities', {}).values()), 'Unknown capability')
    for field, maximum in [('kpis', 8), ('funnel', 12), ('highlights', 6), ('tables', 8), ('findings', 12), ('caveats', 12)]:
        require(isinstance(data.get(field, []), list) and len(data.get(field, [])) <= maximum, f'Invalid {field}')
    for kpi in data.get('kpis', []):
        require(isinstance(kpi, dict) and set(kpi) <= {'label', 'value', 'detail', 'change', 'tone', 'changeDirection'} and text(kpi.get('label')) and text(kpi.get('value')), 'Invalid KPI')
        require('detail' not in kpi or text(kpi['detail']), 'Invalid KPI detail')
        validate_change(kpi)
    for item in data.get('highlights', []):
        require(isinstance(item, dict) and set(item) <= {'label', 'value', 'detail', 'change', 'tone', 'changeDirection'} and text(item.get('label')) and text(item.get('value')), 'Invalid highlight')
        require('detail' not in item or text(item['detail']), 'Invalid highlight detail')
        validate_change(item)
    require('funnelContext' not in data or text(data['funnelContext']), 'Invalid funnel context')
    for stage in data.get('funnel', []):
        require(isinstance(stage, dict) and set(stage) <= {'label', 'count', 'prior', 'display', 'detail', 'change', 'tone', 'changeDirection'} and text(stage.get('label')) and 'count' in stage, 'Invalid stage')
        validate_change(stage)
        require('changeDirection' not in stage or stage['count'] is not None, 'Unmeasured stage cannot have a change direction')
        require(all(key not in stage or text(stage[key]) for key in ['display', 'detail', 'change']), 'Invalid stage annotation')
        require(stage['count'] is not None or 'display' not in stage, 'Unmeasured stage cannot have a measured display')
        for key in ['count', 'prior']:
            value = stage.get(key)
            require(value is None or (type(value) is int and value >= 0), 'Stage counts must be nonnegative integers or null')
    for table in data.get('tables', []):
        require(isinstance(table, dict) and {'title', 'columns', 'rows'} <= set(table) <= {'title', 'columns', 'rows', 'kind', 'note', 'numericColumns', 'placement', 'barColumn'} and text(table['title']), 'Invalid table')
        require(table.get('placement') in {None, 'overview', 'supporting'}, 'Invalid table placement')
        require(table.get('kind') in {None, 'table', 'bars'}, 'Invalid table kind')
        require('note' not in table or text(table['note']), 'Invalid table note')
        require(isinstance(table['columns'], list) and 0 < len(table['columns']) <= 8 and all(text(x) for x in table['columns']), 'Invalid columns')
        require(isinstance(table['rows'], list) and len(table['rows']) <= 50, 'Table row cap exceeded')
        for row in table['rows']:
            require(isinstance(row, list) and len(row) == len(table['columns']), 'Table width mismatch')
            require(all(x is None or isinstance(x, (str, int, float)) and not isinstance(x, bool) for x in row), 'Invalid table cell')
        require(isinstance(table.get('numericColumns', []), list) and all(type(i) is int and 0 <= i < len(table['columns']) for i in table.get('numericColumns', [])), 'Invalid numeric columns')
        if 'barColumn' in table:
            col = table['barColumn']
            require(table.get('kind') != 'bars' and type(col) is int and 0 < col < len(table['columns']), 'Invalid table bar column')
            require(all(row[col] is None or type(row[col]) is int and row[col] >= 0 for row in table['rows']), 'Table bars require normalized integer counts or null')
        if table.get('kind') == 'bars':
            require(len(table['columns']) == 2 and all(row[1] is None or type(row[1]) in {int, float} and math.isfinite(row[1]) and row[1] >= 0 for row in table['rows']), 'Bars require label and nonnegative numeric value columns')
    seen = set()
    for finding in data.get('findings', []):
        require(isinstance(finding, dict) and set(finding) <= {'id', 'title', 'evidence', 'impact', 'fix', 'issueId', 'category', 'tag', 'performance', 'noibuLinks', 'ownership'}, 'Invalid finding fields')
        require(finding.get('ownership') in {None, 'merchant-code', 'merchant-content', 'vendor', 'unknown'}, 'Invalid finding ownership')
        require(all(key not in finding or text(finding[key]) for key in ['impact', 'fix', 'tag']), 'Invalid finding annotation')
        require(text(finding.get('id'), 100) and finding['id'] not in seen, 'Invalid/duplicate finding identity')
        seen.add(finding['id'])
        require(text(finding.get('title')) and text(finding.get('evidence')), 'Finding needs evidence')
        require(finding.get('category') in {None, 'merchant', 'performance', 'vendor', 'accessibility'}, 'Invalid finding category')
        if 'performance' in finding:
            require(finding.get('category') == 'performance', 'Performance card needs performance category')
            validate_performance(finding['performance'])
        validate_links(finding.get('noibuLinks', []), domain.get('id'))
    validate_links(data.get('noibuLinks', []), domain.get('id'))
    require(all(text(x) for x in data.get('caveats', [])), 'Invalid caveats')
    if data.get('contextHash'):
        require(re.fullmatch(r'[a-f0-9]{64}', data['contextHash']), 'Invalid context hash')
    # Also rejects nonfinite evidence anywhere in the input.
    safe_json(data)
    return data

def action(data, kind, target=None):
    result = {'schema': 'noibu.presentation-action/1', 'kind': kind, 'workflow': data['workflow'], 'reportId': data['reportId'], 'domain': data['domain'], 'window': data['window'], 'generatedAt': data['generatedAt'], 'target': target or {}}
    finding = next((f for f in data.get('findings', []) if f['id'] == (target or {}).get('findingId')), None)
    technical = finding and (data['workflow'] in {'tech-diagnosis', 'accessibility-audit'} or finding.get('category') in {'merchant', 'performance', 'accessibility'})
    batch_ids = (target or {}).get('findingIds')
    if batch_ids is not None:
        require(data['workflow'] == 'accessibility-audit' and kind in {'draft-pr', 'create-ticket'} and isinstance(batch_ids, list) and 0 < len(batch_ids) <= 3 and len(set(batch_ids)) == len(batch_ids), 'Invalid audit batch action')
        require(all(any(f['id'] == identity for f in data.get('findings', [])) for identity in batch_ids), 'Unknown audit finding in batch')
        if kind == 'draft-pr':
            require(all(f.get('ownership') not in {'merchant-content', 'vendor'} and f.get('category') != 'vendor' for f in data.get('findings', []) if f['id'] in batch_ids), 'Batch PR includes a content/vendor handoff')
    if finding and finding.get('category') != 'vendor' and (kind in {'get-fix', 'draft-pr'} or kind == 'investigate' and technical) or batch_ids and kind == 'draft-pr':
        result['execution'] = {'route': 'source-access', 'sources': ['shopify-theme-via-noibu', 'code-host-connector'], 'connection': 'verify-before-fix-or-prompt', 'repository': 'resolve-or-ask', 'withoutSource': 'diagnosis-hint-and-connect-step', 'mode': 'read-only'}
    elif kind == 'save-dashboard':
        result['execution'] = {'route': 'persistent-site', 'dataMode': 'persistent-snapshot', 'completion': 'published-persisted-or-specific-blocker', 'reuseExisting': True, 'audience': 'private-preserve-existing', 'schedule': 'offer-weekly-confirm-details', 'permissions': 'preflight-native-or-guide'}
    elif kind == 'schedule':
        result['execution'] = {'route': 'native-task-connected-delivery', 'provider': 'discover-send-capability', 'destination': 'resolve-or-ask', 'completion': 'task-saved-or-specific-blocker', 'deliveryVerification': 'separate-from-task-creation'}
    elif kind == 'save-report':
        result['execution'] = {'route': 'native-pages', 'completion': 'page-saved-or-specific-blocker', 'audience': 'private-preserve-existing'}
    elif kind == 'create-ticket':
        result['execution'] = {'route': 'ticket-destination-first', 'chooser': 'native-question-or-text', 'question': 'Where should the ticket go?', 'options': ['Linear', 'Jira', 'GitHub Issues', 'Notion'], 'connection': 'discover-after-selection', 'completion': 'verified-ticket-or-explicit-draft-or-specific-blocker'}
    return result

def candidate_data(data, candidates):
    if candidates is None:
        return []
    require(data['workflow'] == 'ab-test-opportunity-finder', 'Candidates belong to experiment workflow')
    module_path = HERE.parent / 'ab-test-opportunity-finder/scripts/validate_candidates.py'
    spec = importlib.util.spec_from_file_location('noibu_candidates', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_candidates(candidates)
    require(candidates['domain'] == data['domain']['name'] and candidates['domainId'] == data['domain'].get('id'), 'Candidate domain mismatch')
    require(candidates['window']['start'] == data['window']['start'] and candidates['window']['end'] == data['window']['end'], 'Candidate window mismatch')
    result = []
    for item in candidates['tests']:
        digest = hashlib.sha256(json.dumps(item['createInput'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        result.append({'rank': item['rank'], 'title': item['title'], 'what': item['what'], 'hypothesis': item['hypothesis'], 'validation': item['validation']['status'], 'metric': item['createInput']['successMetric']['metric'], 'hash': digest, 'evidence': item['evidence'], 'variations': item['createInput']['variations'], 'guardrails': item['createInput'].get('secondaryMetrics', []), 'devices': item['createInput'].get('deviceTypes', []), 'utm': item['createInput'].get('utmConditions', [])})
    return result

def render_funnel(data):
    """One shared linear count scale; connectors may rise for express checkout."""
    stages = data.get('funnel', [])
    if not stages:
        return ''
    maximum = max([s.get(k) or 0 for s in stages for k in ['count', 'prior']] + [1])
    width, height = 1000, 220
    step = width / len(stages)
    bar = step * .56
    marks, labels, mobile = [], [], []
    prior_present = any(s.get('prior') is not None for s in stages)
    for n, stage in enumerate(stages):
        count, x = stage['count'], n * step
        y = height - height * (count or 0) / maximum
        if n + 1 < len(stages) and count is not None and stages[n + 1]['count'] is not None:
            next_y = height - height * stages[n + 1]['count'] / maximum
            marks.append(f'<path class="noibu-funnel-link" d="M{x + bar:.3f},{y:.3f} L{x + step:.3f},{next_y:.3f} V{height} H{x + bar:.3f} Z"/>')
        if stage.get('prior') is not None:
            h = height * stage['prior'] / maximum
            marks.append(f'<rect class="noibu-prior-mark" x="{x:.3f}" y="{height-h:.3f}" width="{bar:.3f}" height="{h:.3f}" rx="4"/>')
        if count is not None:
            marks.append(f'<rect class="noibu-current-mark" x="{x:.3f}" y="{y:.3f}" width="{bar:.3f}" height="{height-y:.3f}" rx="4"/>')
        value = stage.get('display', f'{count:,}' if count is not None else 'Not measured')
        change = render_change(stage)
        detail = f'<span class="noibu-secondary">{escape(stage["detail"])}</span>' if stage.get('detail') else ''
        labels.append(f'<div class="noibu-stage"><span class="noibu-label">{escape(stage["label"])}</span><div class="noibu-stage-value tabular-nums">{escape(value)} {change}</div>{detail}</div>')
        track = '' if count is None else f'<div class="noibu-mobile-track"><span style="width:{100*count/maximum:.4f}%"></span></div>'
        mobile.append(f'<li><div>{labels[-1]}</div>{track}</li>')
    accessible = '; '.join(f'{s["label"]}: {s["count"]} sessions' if s['count'] is not None else f'{s["label"]}: Not measured' for s in stages)
    legend = '<span><i class="noibu-key-current"></i>Current sessions</span>' + ('<span><i class="noibu-key-prior"></i>Prior sessions</span>' if prior_present else '')
    context = f'<p class="noibu-secondary">{escape(data["funnelContext"])}</p>' if data.get('funnelContext') else ''
    counts = render_table({'title': 'Exact funnel counts', 'columns': ['Stage', 'Current sessions', 'Prior sessions'], 'rows': [[s['label'], s['count'], s.get('prior')] for s in stages]})
    many = ' noibu-funnel-many' if len(stages) > 6 else ''
    return f'<section class="noibu-funnel{many}"><h3>Purchase funnel</h3>{context}<div class="noibu-funnel-desktop"><div class="noibu-stage-labels" style="grid-template-columns:repeat({len(stages)},minmax(0,1fr))">{"".join(labels)}</div><svg class="noibu-funnel-chart" viewBox="0 0 {width} {height}" preserveAspectRatio="none" role="img" aria-label="{escape(accessible)}"><title>Distinct sessions by funnel stage</title>{"".join(marks)}</svg></div><ol class="noibu-funnel-mobile" aria-label="{escape(accessible)}">{"".join(mobile)}</ol><div class="noibu-chart-key">{legend}</div><details class="noibu-counts"><summary>Show exact counts</summary>{counts}</details></section>'

def render_table(table, compact=False):
    title = '<h3>' + escape(table['title']) + '</h3>'
    note = '<p class="noibu-secondary">' + escape(table['note']) + '</p>' if table.get('note') else ''
    if table.get('kind') == 'bars':
        maximum = max([row[1] or 0 for row in table['rows']] + [1])
        rows = []
        for label, value in table['rows']:
            fill = '' if value is None else f'<span class="noibu-bar-fill" style="width:{100*value/maximum:.4f}%"></span>'
            rows.append(f'<div class="noibu-bar-row"><span>{escape(label)}</span><div class="noibu-bar-track">{fill}</div><span class="tabular-nums">{escape(value if value is None else format(value, ","))}</span></div>')
        return '<section class="noibu-table-section">' + title + f'<div role="group" aria-label="{escape(table["title"])}">' + ''.join(rows) + '</div>' + note + '</section>'
    numeric = set(table.get('numericColumns', []))
    # Alignment only: never parse formatted text to compute analytics.
    numeric.update(i for i in range(1, len(table['columns'])) if table['rows'] and all(row[i] is None or isinstance(row[i], (int, float)) or re.fullmatch(r'[\s$€£¥+−↑↓\d.,%()–—-]+(?:\s*pp)?', str(row[i])) for row in table['rows']))
    headings = ''.join(f'<th scope="col" class="{"noibu-numeric" if i in numeric else ""}">{escape(c)}</th>' for i, c in enumerate(table['columns']))
    bar_col = table.get('barColumn') if compact else None
    maximum = max([r[bar_col] or 0 for r in table['rows']] + [1]) if bar_col is not None else 1
    def row_html(row):
        cells = []
        for i, cell in enumerate(row):
            value = format(cell, ',') if compact and type(cell) is int else cell
            display = escape(value)
            if compact and i == 0:
                display = '<span class="noibu-product-name" data-tooltip="' + escape(cell) + '">' + display + '</span>'
            elif bar_col == i and cell is not None:
                display = '<span class="noibu-count-cell"><span class="noibu-count-track" aria-hidden="true"><span style="width:' + f'{100*cell/maximum:.4f}%' + '"></span></span><span>' + display + '</span></span>'
            cells.append(f'<td class="{"noibu-numeric tabular-nums" if i in numeric or i == bar_col else ""}">{display}</td>')
        return '<tr>' + ''.join(cells) + '</tr>'
    def grid(rows):
        return '<div class="table-responsive"><table class="table"><thead><tr>' + headings + '</tr></thead><tbody>' + ''.join(row_html(row) for row in rows) + '</tbody></table></div>'
    content = grid(table['rows'][:5] if compact else table['rows'])
    if compact and len(table['rows']) > 5:
        content += f'<details class="noibu-extra-rows"><summary>Show all {len(table["rows"])} rows</summary>' + grid(table['rows']) + '</details>'
    return '<section class="noibu-table-section">' + title + content + note + '</section>'

def render_links(items):
    return ''.join(f'<a class="btn" href="{escape(item["url"])}" target="_blank" rel="noopener noreferrer">{escape(item["label"])}</a>' for item in items)

def render_performance(value, window):
    metric, measured = value['metric'], value['value']
    good, poor, unit = VITALS[metric]
    fmt = lambda number: f'{number:g}' + (' ms' if unit == 'ms' else '')
    context = [value.get('page'), value.get('pageGroup'), value.get('device'), window.get('label') or window['start'] + ' – ' + window['end']]
    traffic = value.get('traffic')
    if traffic and traffic['count'] is not None:
        context.insert(0, f'{traffic["count"]:,} {traffic["unit"]}')
    if measured is None:
        gauge = '<p>p75 not measured — no threshold marker.</p>'
    else:
        band = 'Good' if measured <= good else 'Needs improvement' if measured <= poor else 'Poor'
        # Shared metric scale across peer cards; values beyond the displayed
        # poor-band extent retain an exact visible value and an overflow notice.
        maximum = poor * 2
        good_at, poor_at = 100 * good / maximum, 100 * poor / maximum
        position = min(100, 100 * measured / maximum)
        description = f'{metric} p75 {fmt(measured)}: {band}. Good at or below {fmt(good)}; poor above {fmt(poor)}.'
        overflow = f'<span class="noibu-secondary">Beyond displayed {escape(fmt(maximum))} scale</span>' if measured > maximum else ''
        gauge = f'''<div class="noibu-vital-reading"><strong class="tabular-nums">{escape(fmt(measured))}</strong><span>p75 · {band}</span></div>
<div class="noibu-vital-gauge" role="img" aria-label="{escape(description)}" data-metric="{metric}" data-value="{measured}" data-band="{band}" data-position="{position:g}">
<div class="noibu-vital-track"><span class="noibu-vital-good" style="width:{good_at:g}%">✓</span><span class="noibu-vital-improve" style="width:{poor_at-good_at:g}%">!</span><span class="noibu-vital-poor" style="width:{100-poor_at:g}%">×</span><i class="noibu-vital-marker" style="left:clamp(2px,{position:g}%,calc(100% - 2px))" aria-hidden="true"></i></div>
<div class="noibu-vital-ticks" aria-hidden="true"><span style="left:{good_at:g}%">{escape(fmt(good))}</span><span style="left:{poor_at:g}%">{escape(fmt(poor))}</span></div></div>{overflow}
<div class="noibu-vital-legend">Good ≤ {escape(fmt(good))} · Needs improvement &gt; {escape(fmt(good))} to {escape(fmt(poor))} · Poor &gt; {escape(fmt(poor))}</div>'''
    return gauge + '<p class="noibu-vital-context">' + escape(' · '.join(x for x in context if x)) + '</p>'

def render(data, candidates=None, standalone=False):
    validate(data)
    checkout = data['workflow'] == 'checkout-analysis'
    product = data['workflow'] == 'product-analysis'
    segment = data['workflow'] == 'segment-analysis'
    compact_report = product or segment
    outlined = data['workflow'] in ANALYTICS
    actions = []
    def button(label, kind, target=None, primary=False):
        index = len(actions)
        actions.append(action(data, kind, target))
        return f'<button type="button" class="btn{ " btn-primary" if primary else ""}" data-noibu-action="{index}">{escape(label)}</button>'
    kpis = ''.join(f'<div class="noibu-stat"><span class="noibu-label">{escape(x["label"])}</span><div class="noibu-stat-value tabular-nums">{escape(x["value"])}</div>{render_change(x)}' + ('<span class="noibu-stat-detail noibu-secondary">' + escape(x['detail']) + '</span>' if x.get('detail') else '') + '</div>' for x in data.get('kpis', []))
    funnel = render_funnel(data)
    tables = ''.join(render_table(t) for t in data.get('tables', []))
    if checkout:
        visible = [t for t in data.get('tables', []) if t.get('placement') == 'overview' and t.get('kind') != 'bars']
        mixes = [t for t in data.get('tables', []) if t.get('kind') == 'bars' and t.get('placement') != 'supporting']
        supporting = [t for t in data.get('tables', []) if t not in visible and t not in mixes]
        tables = ''.join(render_table(t) for t in visible)
        if mixes:
            tables += '<div class="noibu-checkout-mixes">' + ''.join(render_table(t) for t in mixes) + '</div>'
        if supporting:
            tables += '<details class="noibu-supporting"><summary>Supporting data & observed abandonment</summary>' + ''.join(render_table(t) for t in supporting) + '</details>'
    elif compact_report and data.get('tables'):
        limit = 3 if segment else 2
        overview = [t for t in data['tables'] if t.get('placement') == 'overview'][:limit]
        if not overview:
            overview = [t for t in data['tables'] if t.get('placement') != 'supporting'][:limit]
        supporting = [t for t in data['tables'] if t not in overview]
        tables = ''.join(render_table(t, compact=True) for t in overview)
        if supporting:
            tables += '<details class="noibu-supporting"><summary>More supporting data (' + str(len(supporting)) + ')</summary>' + ''.join(render_table(t, compact=True) for t in supporting) + '</details>'
        detail_class = 'noibu-segment-details' if segment else 'noibu-product-details'
        tables = f'<details class="{detail_class}"><summary><span class="noibu-show-more">Show more</span><span class="noibu-show-less">Show less</span></summary>' + tables + '</details>'
    highlights = ''.join(f'<div><span class="noibu-label">{escape(x["label"])}</span><p>{escape(x["value"])}</p>{render_change(x)}<span class="noibu-stat-detail noibu-secondary">{escape(x.get("detail", ""))}</span></div>' for x in data.get('highlights', []))
    findings = []
    caps = data.get('capabilities', {})
    for n, item in enumerate(data.get('findings', []), 1):
        target = {'findingId': item['id']}
        performance = item.get('performance')
        vendor = item.get('category') == 'vendor'
        controls = '' if performance or vendor else button('Investigate ↗', 'investigate', target)
        if (data['workflow'] in {'tech-diagnosis', 'accessibility-audit'} or performance) and not vendor:
            controls += button('Get fix ↗' if performance else 'Get fix', 'get-fix', target)
            if performance:
                controls += button('Investigate ↗', 'investigate', target)
            if caps.get('draftPr'):
                controls += button('Prepare draft PR', 'draft-pr', target)
        if data['workflow'] in {'tech-diagnosis', 'accessibility-audit'} or item.get('category') in {'merchant', 'performance', 'accessibility'}:
            controls += button('Open a Ticket', 'create-ticket', target)
        if item.get('issueId') and caps.get('ignoreIssue'):
            controls += button('Ignore issue', 'ignore-issue', {**target, 'issueId': item['issueId']})
        if item.get('category') == 'vendor':
            controls += button('Prepare vendor message', 'share-vendor', target)
        destinations = item.get('noibuLinks', [])
        metric_overview = bool(performance and not destinations and data['domain'].get('id'))
        if metric_overview:
            destinations = [{'label': 'View ' + performance['metric'] + ' in Noibu', 'url': links.console_link(data['domain']['id'], 'performance', performance['metric']), 'source': 'Resolved report domain UUID and documented performance overview route'}]
        controls += render_links(destinations)
        fix = '<p>' + escape(item['fix']) + '</p>' if item.get('fix') else ''
        impact = f'<span class="noibu-impact">{escape(item["impact"])}</span>' if item.get('impact') else ''
        if performance:
            state = '<span class="noibu-vital-status">' + escape(performance['status']) + '</span>' if performance.get('status') else ''
            navigation_note = '<p class="noibu-vital-legend">Noibu link opens the metric overview; page and date filters are not applied.</p>' if metric_overview else ''
            findings.append(f'<section class="noibu-performance-card"><div class="noibu-performance-header"><span>{performance["metric"]}</span>{state}</div><div class="noibu-performance-body"><h3>{escape(item["title"])}</h3><p>{escape(item["evidence"])}</p>{render_performance(performance, data["window"])}{fix}<div class="viz-row">{controls}</div>{navigation_note}</div></section>')
        elif checkout:
            fix = '<p class="noibu-next-check"><strong>Next check</strong> ' + escape(item['fix']) + '</p>' if item.get('fix') else ''
            tag = ' · ' + escape(item['tag']) if item.get('tag') and item['tag'].lower() != f'priority {n}' else ''
            findings.append(f'<section class="noibu-finding noibu-checkout-opportunity"><div class="noibu-finding-heading"><span class="noibu-label">Priority {n}{tag}</span>{impact}</div><div class="noibu-opportunity-body"><h3>{escape(item["title"])}</h3><p>{escape(item["evidence"])}</p>{fix}<div class="viz-row">{controls}</div></div></section>')
        elif compact_report:
            next_check = '<details class="noibu-next-check"><summary>Investigation & verification</summary><p>' + escape(item['fix']) + '</p></details>' if item.get('fix') else ''
            card_class = 'noibu-segment-opportunity' if segment else 'noibu-product-opportunity'
            findings.append(f'<section class="noibu-finding {card_class}"><div class="noibu-finding-heading"><span class="noibu-label">{escape(item.get("tag", f"Priority {n}"))}</span>{impact}</div><div class="noibu-opportunity-body"><h3>{escape(item["title"])}</h3><p>{escape(item["evidence"])}</p>{next_check}<div class="viz-row">{controls}</div></div></section>')
        else:
            findings.append(f'<section class="noibu-finding"><div class="noibu-finding-heading"><span class="noibu-tag">{escape(item.get("tag", f"Priority {n}"))}</span>{impact}</div><h3>{escape(item["title"])}</h3><p>{escape(item["evidence"])}</p>{fix}<div class="viz-row">{controls}</div></section>')
    if data['workflow'] == 'tech-diagnosis':
        grouped = []
        for category, title in [('merchant', 'Merchant issues'), ('performance', 'Performance'), ('vendor', 'Vendor issues'), (None, 'Other findings'), ('accessibility', 'Accessibility')]:
            sections = [section for item, section in zip(data.get('findings', []), findings) if item.get('category') == category]
            if sections:
                grouped.append('<section class="noibu-finding-group"><h2>' + title + '</h2>' + ''.join(sections) + '</section>')
        findings = grouped
    experiments = []
    for item in candidate_data(data, candidates):
        controls = ''
        if caps.get('createDraft'):
            controls = button('Create A/B draft in Noibu', 'create-draft', {'rank': item['rank'], 'title': item['title'], 'createInputHash': item['hash']}, True)
        evidence = ''.join('<li>' + escape(e['claim']) + ' · ' + escape(json.dumps(e['numbers'], ensure_ascii=False)) + ' · ' + escape(e['source']) + '</li>' for e in item['evidence'])
        variations = ''.join('<tr><td>' + escape(v['name']) + '</td><td>' + ('Control' if v['isControl'] else 'Proposed variation') + '</td><td>' + escape(v['trafficSplit']) + '%</td></tr>' for v in item['variations'])
        setup = '<div class="table-responsive"><table class="table table-sm"><thead><tr><th>Variation</th><th>Role</th><th>Traffic split</th></tr></thead><tbody>' + variations + '</tbody></table></div>'
        guardrails = ', '.join(g['metric'] for g in item['guardrails']) or 'None selected'
        targeting = 'Devices: ' + (', '.join(item['devices']) or 'All') + '; UTM: ' + (json.dumps(item['utm'], ensure_ascii=False) if item['utm'] else 'No selected restrictions')
        experiments.append(f'<section class="noibu-finding"><span class="text-small">Test {item["rank"]} · {escape(item["validation"])}</span><h3>{escape(item["title"])}</h3><p>{escape(item["what"])}</p><p>{escape(item["hypothesis"])}</p><ul>{evidence}</ul><p>Success metric: {escape(item["metric"])} · Guardrails: {escape(guardrails)}</p>{setup}<p>{escape(targeting)}</p>{controls}</section>')
    if data['workflow'] == 'accessibility-audit' and data.get('findings'):
        if data.get('auditLayout') == 'summary-actions':
            findings = []
        ticket_scope = data['findings'][:3]
        pr_scope = [f for f in data['findings'] if f.get('ownership') not in {'merchant-content', 'vendor'} and f.get('category') != 'vendor'][:3]
        audit_actions = button('Auto-draft PR', 'draft-pr', {'findingIds': [f['id'] for f in pr_scope]}, True) if pr_scope else ''
        audit_actions += button('Auto-create tickets', 'create-ticket', {'findingIds': [f['id'] for f in ticket_scope]})
        scope_text = '<p>Tickets: ' + escape('; '.join(f['title'] for f in ticket_scope)) + '.</p>'
        if pr_scope:
            scope_text += '<p>PR review: ' + escape('; '.join(f['title'] for f in pr_scope)) + '. Source/ownership verification and a connected source (code host or Shopify theme via Noibu) connection are required before a draft PR can be created.</p>'
        findings.append('<section class="noibu-finding"><h3>Draft fixes or open tickets for these top findings?</h3>' + scope_text + '<div class="viz-row">' + audit_actions + '</div></section>')
    save = button('Save as Live Site', 'save-dashboard', primary=True) if data['workflow'] in ANALYTICS else ''
    controls = ('' if outlined else save) + button('Save to ChatGPT Pages', 'save-report', primary=data['workflow'] not in ANALYTICS) + button('Download Report', 'export-report')
    controls += render_links(data.get('noibuLinks', []))
    if data['workflow'] in SCHEDULABLE:
        controls += button('Schedule Insights' if compact_report else 'Schedule report', 'schedule', primary=outlined)
    if data.get('contextHash') and caps.get('persistContext'):
        controls += button('Save approved context to Noibu', 'save-context', {'contextHash': data['contextHash']}, True)
    root = 'noibu-' + data['reportId']
    model = {'actions': actions, 'timezone': data.get('timezone', ''), 'workflow': data['workflow']}
    # These assets contain fixed code; model values never become executable source.
    template = (HERE / 'assets/presentation/board.html').read_text()
    controller = (HERE / 'assets/presentation/actions.js').read_text()
    if data['workflow'] in SCHEDULABLE:
        schedule_template = (HERE / 'assets/presentation/checkout-schedule.html').read_text().rstrip()
        schedule_titles = {'checkout-analysis': 'Schedule checkout analysis', 'product-analysis': 'Schedule product analysis', 'segment-analysis': 'Schedule segment analysis', 'store-pulse': 'Schedule Store Pulse', 'tech-diagnosis': 'Schedule technical diagnosis', 'accessibility-audit': 'Schedule accessibility audit', 'ab-test-opportunity-finder': 'Schedule A/B opportunities'}
        schedule_template = schedule_template.replace('Schedule checkout analysis', schedule_titles[data['workflow']], 1)
        scope_notes = {
            'tech-diagnosis': 'Recurring report only: no automatic source edits, PRs, tickets or issue status changes.',
            'accessibility-audit': 'Recurring scans require verified approved browser execution in the scheduled runtime. Setup does not scan or fix anything; audit mode and coverage must be confirmed.',
            'ab-test-opportunity-finder': 'Recurring recommendations only: no automatic Noibu test drafts, browser mutations, implementation or test activation.'
        }
        if data['workflow'] in scope_notes:
            schedule_template = schedule_template.replace('<p class="text-small">Submitting requests', '<p class="text-small">' + escape(scope_notes[data['workflow']]) + '</p>\n    <p class="text-small">Submitting requests', 1)
        if data['workflow'] == 'store-pulse':
            daily = '<label class="noibu-choice"><input type="radio" name="frequency" value="daily"><span>Daily</span></label>\n      '
            schedule_template = schedule_template.replace('<label class="noibu-choice">', daily + '<label class="noibu-choice">', 1)
        template = re.sub(r'  <form data-noibu-schedule hidden>.*?</form>', lambda _: schedule_template, template, count=1, flags=re.S)
        controller += '\n' + (HERE / 'assets/presentation/checkout-schedule.js').read_text()
    if outlined:
        template = template.replace('{{KPIS}}', '{{OVERVIEWCONTEXT}}\n      {{KPIS}}', 1)
        template = template.replace('{{TABLES}}', '{{TABLES}}\n      <div class="noibu-overview-save">' + save + '</div>', 1)
        template = template.replace('<h3>Save & schedule</h3>', '<h3>Download & schedule</h3>', 1)
    if compact_report:
        if len(findings) > 3:
            more_count = len(findings) - 3
            more_label = ' more opportunity' if more_count == 1 else ' more opportunities'
            findings = findings[:3] + ['<details class="noibu-more-findings"><summary>' + str(more_count) + more_label + '</summary>' + ''.join(findings[3:]) + '</details>']
    if data.get('auditLayout') == 'summary-actions':
        template = re.sub(r'  <section class="noibu-overview">.*?  </section>\n', '', template, count=1, flags=re.S)
    values = {'ROOT': root, 'TITLE': escape(data['workflow'].replace('-', ' ').title()), 'DOMAIN': escape(data['domain']['name']), 'WINDOW': escape(data['window'].get('label', data['window']['start'] + ' – ' + data['window']['end'])), 'GENERATED': escape(data['generatedAt']), 'SUMMARY': escape(data['summary']), 'KPIS': '<div class="noibu-kpis">' + kpis + '</div>' if kpis else '', 'HIGHLIGHTS': '<div class="noibu-highlights">' + highlights + '</div>' if highlights else '', 'FUNNEL': funnel, 'TABLES': tables, 'FINDINGS': ''.join(findings), 'EXPERIMENTS': ''.join(experiments), 'CAVEATS': '<details class="noibu-caveats" open><summary>Evidence & coverage</summary><ul>' + ''.join('<li>' + escape(x) + '</li>' for x in data.get('caveats', [])) + '</ul></details>' if data.get('caveats') else '', 'ACTIONS': controls, 'MODEL': safe_json(model), 'CONTROLLER': (HERE / 'assets/presentation/actions.js').read_text(), 'STYLE': (HERE / 'assets/presentation/report.css').read_text().replace('{{ROOT}}', root)}
    values['CONTROLLER'] = controller
    if segment and data.get('overviewNotes'):
        values['HIGHLIGHTS'] += '<div class="noibu-overview-notes" role="note" aria-label="Data notes">' + ''.join('<p><strong>Data note:</strong> ' + escape(note) + '</p>' for note in data['overviewNotes']) + '</div>'
    values['OVERVIEWCONTEXT'] = '<p class="noibu-overview-context">' + escape(data['overviewContext']) + '</p>' if data.get('overviewContext') else ''
    if outlined:
        values['TITLE'] = 'Overview'
    fragment = re.sub(r'\{\{([A-Z]+)\}\}', lambda match: values[match.group(1)], template)
    fragment = fragment.replace('class="noibu-board"', f'class="noibu-board" data-noibu-workflow="{data["workflow"]}"', 1)
    if data['workflow'] in ANALYTICS:
        fragment = fragment.replace('<p class="noibu-generated">', '<p class="noibu-site-note">Save as Live Site publishes this report privately with saved data. Weekly refresh is offered during setup and scheduled only after you confirm the details.</p><p class="noibu-generated">', 1)
    require(len(fragment.encode()) < 1000000, 'Presentation exceeds inline size limit')
    if not standalone:
        return fragment
    style = (HERE / 'assets/presentation/standalone.css').read_text()
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{values["TITLE"]} — {values["DOMAIN"]}</title><style>{style}</style></head><body>{fragment}</body></html>'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidates', type=Path)
    parser.add_argument('--standalone', action='store_true')
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text())
        candidates = json.loads(args.candidates.read_text()) if args.candidates else None
        output = render(data, candidates, args.standalone)
    except (ValueError, TypeError, KeyError) as error:
        parser.exit(1, f'Invalid presentation: {error}\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output)
    print(f'Created {"standalone snapshot" if args.standalone else "inline board"}: {args.output}; no external action executed')

if __name__ == '__main__':
    main()
