"""Build an escaped, static accessibility report from completed axe-style findings."""
import argparse
import html
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

WEIGHTS = {'critical': 5, 'serious': 3, 'moderate': 1.5, 'minor': 0.5}

# User-supplied report copy, reproduced verbatim from the Claude reference PDF.
# These statements are template copy, not claims independently validated here.
CLAUDE_DISCLAIMER = 'This skill generates automated WCAG 2.1 AA accessibility reports. Automated tools detect 30%–90% of issues on the pages that were scanned. Results are informational only, not legal advice or a compliance certification. Manual testing by a qualified professional is required for complete coverage.'
CLAUDE_STANDARD_STATEMENT = 'WCAG 2.1 Level AA is the standard most commonly applied in accessibility law and procurement, so every result below is measured against it.'

def reference_copy_applies(summary):
    standard = ' '.join(str(summary.get('standard', '')).upper().split())
    return (summary.get('mode') == 'axe'
            and standard in {'WCAG 2.1 AA', 'WCAG 2.1 A/AA', 'WCAG 2.1 LEVEL AA', 'WCAG 2.1 A/AA AUTOMATED CHECKS'}
            and any(p.get('status') == 'COMPLETED' for p in summary.get('pages', [])))

def require(condition, message):
    if not condition:
        raise ValueError(message)

def safe_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        return None
    return value

def link(url, label):
    escaped = html.escape(str(label))
    return f'<a href="{html.escape(url, quote=True)}">{escaped}</a>' if safe_url(url) else escaped

def pool(data):
    require(isinstance(data, dict) and isinstance(data.get('pages'), list), 'Expected pages list')
    require(isinstance(data.get('domain'), str) and data['domain'].strip(), 'Expected domain')
    grouped, seen, states, raw, completed = {}, set(), Counter(), 0, 0
    violated_rules, affected_elements = set(), set()
    pages = []
    for page in data['pages']:
        require(isinstance(page, dict) and safe_url(page.get('url')), 'Invalid page URL')
        require(page['url'] not in seen, 'Choose one scan per URL before generating a report')
        seen.add(page['url'])
        status = page.get('status')
        require(status in {'COMPLETED', 'QUEUED', 'RUNNING', 'FAILED'}, 'Unsupported scan status')
        states[status] += 1
        traffic = page.get('pageviews')
        require(traffic is None or (type(traffic) is int and traffic >= 0), 'Invalid pageview count')
        incomplete = page.get('incomplete', [])
        require(isinstance(incomplete, list), 'Invalid manual-review checks')
        pages.append({'url': page['url'], 'status': status, 'pageviews': traffic, 'error': page.get('error'), 'incompleteCount': len(incomplete) if status == 'COMPLETED' and 'incomplete' in page else None, 'incomplete': incomplete, 'scanner': page.get('scanner'), 'scanOptions': page.get('scanOptions'), 'startedAt': page.get('startedAt'), 'completedAt': page.get('completedAt'), 'viewport': page.get('viewport'), 'title': page.get('title'), 'state': page.get('state'), 'testEnvironment': page.get('testEnvironment'), 'testRunner': page.get('testRunner')})
        if status != 'COMPLETED':
            continue
        completed += 1
        require(isinstance(page.get('violations'), list), 'Completed pages must include violations, including [] for none')
        page_rules, page_elements = set(), set()
        for violation in page['violations']:
            require(isinstance(violation, dict) and isinstance(violation.get('id'), str), 'Invalid violation')
            require(violation['id'].strip(), 'Empty rule ID')
            violated_rules.add(violation['id'])
            page_rules.add(violation['id'])
            impact = violation.get('impact')
            require(impact is None or impact in WEIGHTS, 'Invalid impact')
            require(isinstance(violation.get('nodes'), list) and violation['nodes'], 'Violation needs node evidence')
            for node in violation['nodes']:
                require(isinstance(node, dict) and isinstance(node.get('target'), list) and node['target'], 'Node needs target')
                selector = json.dumps(node['target'], ensure_ascii=False)
                page_elements.add(selector)
                affected_elements.add((page['url'], selector))
                # Exact rule+target is the conservative default. The caller can normalize
                # verified shared selectors before input; unrelated nodes stay distinct.
                # Optional groupingKey keeps identical selectors on unrelated
                # templates apart or joins a manually verified shared component.
                identity = node.get('groupingKey', selector)
                require(isinstance(identity, str) and identity.strip(), 'Invalid grouping key')
                key = (violation['id'], identity)
                raw += 1
                if key not in grouped:
                    grouped[key] = {'id': 'a11y-' + hashlib.sha256(json.dumps([violation['id'], identity], ensure_ascii=False).encode()).hexdigest()[:16], 'rule': violation['id'], 'selector': selector, 'impact': impact, 'help': violation.get('help', violation['id']), 'helpUrl': safe_url(violation.get('helpUrl')), 'tags': violation.get('tags', []), 'pages': {}, 'instances': []}
                item = grouped[key]
                if WEIGHTS.get(impact, 0) > WEIGHTS.get(item['impact'], 0):
                    item['impact'] = impact
                item['pages'][page['url']] = traffic
                item['instances'].append({'url': page['url'], 'target': node['target'], 'html': node.get('html', ''), 'failureSummary': node.get('failureSummary', '')})
        pages[-1]['violatedRuleCount'] = len(page_rules)
        pages[-1]['affectedElementCount'] = len(page_elements)
    require(completed > 0, 'No completed findings supplied; queued scans cannot generate a findings report')
    findings = list(grouped.values())
    for item in findings:
        values = list(item['pages'].values())
        known = sum(x for x in values if x is not None)
        item['knownPageviews'] = known
        item['trafficComplete'] = all(x is not None for x in values)
        item['priority'] = WEIGHTS.get(item['impact'], 0) * math.log10(max(1, known)) * min(2, 1 + 0.2 * len(values))
    findings.sort(key=lambda x: (x['priority'], WEIGHTS.get(x['impact'], 0), len(x['instances'])), reverse=True)
    counts = {severity: sum(x['impact'] == severity for x in findings) for severity in WEIGHTS}
    counts['needs_review'] = sum(x['impact'] is None for x in findings)
    for item, original in zip(pages, data['pages']):
        item['violationInstances'] = sum(len(v['nodes']) for v in original['violations']) if item['status'] == 'COMPLETED' else None
    notes = data.get('notes', [])
    require(isinstance(notes, list) and all(isinstance(x, str) and x.strip() for x in notes), 'Invalid scope notes')
    completed_pages = [p for p in pages if p['status'] == 'COMPLETED']
    return {'mode': 'axe', 'domain': data['domain'], 'generatedAt': datetime.now(timezone.utc).isoformat(), 'standard': data.get('standard', 'Not supplied'), 'trafficWindow': data.get('trafficWindow', 'Not supplied'), 'pages': pages, 'states': dict(states), 'violatedRuleCount': len(violated_rules), 'affectedElementCount': len(affected_elements), 'rawInstances': raw, 'uniqueFixes': len(findings), 'severityCounts': counts, 'severityCountBasis': 'pooled-fixes', 'incompleteCheckCount': sum(p['incompleteCount'] or 0 for p in completed_pages), 'incompleteCountComplete': all(p['incompleteCount'] is not None for p in completed_pages), 'findings': findings, 'notes': notes}

def render(summary):
    reference_copy = reference_copy_applies(summary)
    disclaimer = CLAUDE_DISCLAIMER if reference_copy else 'This report summarizes automated accessibility checks on the listed pages. It is not a compliance certification. Manual keyboard and assistive-technology testing is needed for a complete assessment.'
    standard_statement = f'<p>{html.escape(CLAUDE_STANDARD_STATEMENT)}</p>' if reference_copy else ''
    rows, details = [], []
    for n, item in enumerate(summary['findings'], 1):
        severity = item['impact'] or 'needs manual review'
        traffic = str(item['knownPageviews']) + ('' if item['trafficComplete'] else ' known; partial coverage')
        rows.append(f'<tr><td><a href="#finding-{n}">{n}. {html.escape(str(item["help"]))}</a></td><td>{html.escape(severity)}</td><td>{len(item["pages"])}</td><td>{html.escape(traffic)}</td></tr>')
        nodes = ''.join(f'<p>{link(node["url"], node["url"])}</p><pre>{html.escape(str(node["html"]))}</pre><p>{html.escape(str(node["failureSummary"]))}</p>' for node in item['instances'])
        details.append(f'<section id="finding-{n}"><h2>{n}. {html.escape(str(item["help"]))}</h2><p>Severity: {html.escape(severity)} · {len(item["pages"])} pages · {html.escape(traffic)} pageviews</p><p>{link(item["helpUrl"], "Rule help and criterion reference")}</p><pre>{html.escape(item["selector"])}</pre>{nodes}</section>')
    page_rows = ''.join(f'<tr><td>{link(page["url"], page["url"])}</td><td>{page["status"]}</td><td>{page["pageviews"] if page["pageviews"] is not None else "unknown"}</td><td>{page.get("violatedRuleCount", "unknown")}</td><td>{page.get("affectedElementCount", "unknown")}</td><td>{page["incompleteCount"] if page["incompleteCount"] is not None else "unknown"}</td></tr>' for page in summary['pages'])
    manual = ''.join(f'<section><h3>{link(page["url"], page["url"])}</h3><pre>{html.escape(json.dumps(page["incomplete"], ensure_ascii=False, indent=2))}</pre></section>' for page in summary['pages'] if page['incomplete'])
    counts = ' · '.join(f'{key.replace("_", " ")}: {value}' for key, value in summary['severityCounts'].items())
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(summary['domain'])} accessibility report</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:1000px;margin:40px auto;padding:0 24px;color:#20212b}}table{{border-collapse:collapse;width:100%;margin:24px 0}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ddd}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f5f7;padding:16px}}section{{margin:36px 0;break-inside:avoid}}a{{color:#5125ae}}@media print{{body{{margin:0}}}}</style>
<h1>{html.escape(summary['domain'])} accessibility report</h1><p>Generated {html.escape(summary['generatedAt'])}. Standard: {html.escape(str(summary['standard']))}. Traffic window: {html.escape(str(summary['trafficWindow']))}.</p>
<p>{html.escape(disclaimer)}</p>
{standard_statement}
<p>{summary['rawInstances']} observed instances pooled into {summary['uniqueFixes']} unique rule/selector fixes. {html.escape(counts)}.</p>
<p>{summary['violatedRuleCount']} distinct violated rules / {summary['affectedElementCount']} affected elements (unique page/target pairs). Severity totals above count pooled fixes. {summary['incompleteCheckCount']} known incomplete check records across completed pages{' (partial: some completed pages did not supply incomplete results)' if not summary['incompleteCountComplete'] else ''}; these are not confirmed violations.</p>
<h2>Page coverage</h2><table><tr><th>Page</th><th>Scan status</th><th>Pageviews</th><th>Violated rules</th><th>Affected elements</th><th>Incomplete checks</th></tr>{page_rows}</table>
<h2>Prioritized findings</h2><p>Priority uses severity, known page traffic, and affected-page breadth. Missing traffic can limit the ranking.</p><table><tr><th>Finding</th><th>Severity</th><th>Pages</th><th>Pageviews</th></tr>{''.join(rows)}</table>{''.join(details)}<h2>Manual-review checks</h2><p>These are not confirmed violations.</p>{manual}</html>'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        summary = pool(json.loads(args.input.read_text()))
    except (ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f'Invalid findings: {exc}\n')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = args.output_dir / 'accessibility-report.html'
    report.write_text(render(summary))
    (args.output_dir / 'accessibility-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(f'Created static HTML report: {report}')

if __name__ == '__main__':
    main()
