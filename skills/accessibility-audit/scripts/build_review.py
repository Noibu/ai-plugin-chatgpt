"""Export a limited browser review, never an automated axe findings report."""
import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

IMPACTS = ('critical', 'serious', 'moderate', 'minor')
STATUSES = {'issue-observed', 'needs-verification', 'not-observed', 'not-tested'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, limit=5000):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def safe_url(value):
    if not text(value, 4096):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {'https', 'http'} and bool(parsed.hostname) and not parsed.username and not parsed.password


def timestamp(value):
    require(text(value, 100), 'Reviewed page needs inspectedAt')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, 'Inspection time needs timezone')


def summarize(data):
    require(isinstance(data, dict) and data.get('schema') == 'noibu.accessibility-review/1', 'Expected browser review schema')
    require(set(data) <= {'schema', 'domain', 'trafficWindow', 'pages', 'automationBlocker'}, 'Unknown review fields')
    require(text(data.get('domain'), 300), 'Expected domain')
    require('trafficWindow' not in data or text(data['trafficWindow']), 'Invalid traffic window')
    require('automationBlocker' not in data or text(data['automationBlocker']), 'Invalid automation blocker')
    require(isinstance(data.get('pages'), list) and 0 < len(data['pages']) <= 100, 'Expected 1–100 selected pages')
    pages, seen, findings = [], set(), []
    coverage = {'reviewed': 0, 'unreviewed': 0, 'failed': 0}
    counts = {key: 0 for key in STATUSES}
    manual_severity = {impact: 0 for impact in IMPACTS}
    manual_severity['unknown'] = 0
    for page in data['pages']:
        require(isinstance(page, dict) and set(page) <= {'url', 'status', 'pageviews', 'inspectedAt', 'checks', 'limitations', 'error', 'state'}, 'Invalid review page fields')
        require(safe_url(page.get('url')) and page['url'] not in seen, 'Invalid or duplicate page URL')
        seen.add(page['url'])
        require(page.get('status') in {'REVIEWED', 'UNREVIEWED', 'FAILED'}, 'Invalid review status; axe results use build_report.py')
        traffic = page.get('pageviews')
        require(traffic is None or type(traffic) is int and traffic >= 0, 'Invalid pageviews')
        checks = page.get('checks', [])
        require(isinstance(checks, list) and len(checks) <= 100, 'Invalid checks')
        limitations = page.get('limitations', [])
        require(isinstance(limitations, list) and all(text(x) for x in limitations), 'Invalid limitations')
        require('state' not in page or text(page['state']), 'Invalid rendered state')
        if page['status'] == 'REVIEWED':
            timestamp(page.get('inspectedAt'))
            require(checks, 'Reviewed page needs actual checks')
        else:
            require(not checks, 'Unreviewed/failed page cannot claim checked findings')
        if page['status'] == 'FAILED':
            require(text(page.get('error')), 'Failed review needs error')
        coverage[page['status'].lower()] += 1
        ids = set()
        for check in checks:
            require(isinstance(check, dict) and set(check) <= {'id', 'title', 'status', 'evidence', 'source', 'target', 'impact', 'recommendation'}, 'Invalid check fields')
            require(text(check.get('id'), 100) and check['id'] not in ids and text(check.get('title'), 300), 'Invalid or duplicate check identity')
            ids.add(check['id'])
            require(check.get('status') in STATUSES, 'Invalid check status')
            require(check.get('impact') is None or check['impact'] in IMPACTS, 'Invalid manual impact')
            require(all(key not in check or text(check[key]) for key in ['evidence', 'source', 'target', 'recommendation']), 'Invalid check evidence')
            if check['status'] in {'issue-observed', 'needs-verification', 'not-observed'}:
                require(text(check.get('evidence')) and text(check.get('source')), 'An observation needs evidence and source')
            if check['status'] == 'issue-observed':
                require(text(check.get('target')) and text(check.get('recommendation')), 'Confirmed issue needs target and recommendation')
                manual_severity[check.get('impact') or 'unknown'] += 1
            else:
                require(check.get('impact') is None, 'Only confirmed manual issues have a manual severity')
            counts[check['status']] += 1
            findings.append({'url': page['url'], **check})
        pages.append({**page, 'pageviews': traffic, 'checks': checks, 'limitations': limitations})
    return {
        'schema': 'noibu.accessibility-review-summary/1', 'mode': 'browser-review',
        'domain': data['domain'], 'generatedAt': datetime.now(timezone.utc).isoformat(),
        'trafficWindow': data.get('trafficWindow', 'Not supplied'),
        'automationBlocker': data.get('automationBlocker', 'No axe scan supplied'),
        'automatedScansCompleted': 0, 'automatedSeverityCounts': {impact: None for impact in IMPACTS},
        'coverage': coverage, 'checkCounts': counts, 'manualIssueSeverityCounts': manual_severity,
        'pages': pages, 'observations': findings,
        'limitation': 'Limited browser-based review; axe not run. Not a compliance certification or a complete accessibility assessment.'
    }


def render(summary):
    esc = lambda value: html.escape(str(value), quote=True)
    page_rows = ''.join(f'<tr><td><a href="{esc(p["url"])}">{esc(p["url"])}</a></td><td>{esc(p["status"])}</td><td>{esc(p["pageviews"] if p["pageviews"] is not None else "unknown")}</td><td>{esc(p.get("inspectedAt", "Not inspected"))}</td></tr>' for p in summary['pages'])
    observations = []
    for item in summary['observations']:
        observations.append(f'<section><h3>{esc(item["title"])}</h3><p>{esc(item["status"])} · {esc(item["url"])}</p><p>Evidence: {esc(item.get("evidence", "Not tested"))}</p><p>Source: {esc(item.get("source", "Not supplied"))}</p><pre>{esc(item.get("target", ""))}</pre><p>Manual severity: {esc(item.get("impact") or "unknown/not assigned")}</p><p>{esc(item.get("recommendation", ""))}</p></section>')
    limitations = ''.join(f'<li>{esc(p["url"])}: {esc(note)}</li>' for p in summary['pages'] for note in p['limitations'])
    failures = ''.join(f'<li>{esc(p["url"])}: {esc(p["error"])}</li>' for p in summary['pages'] if p['status'] == 'FAILED')
    coverage = ' · '.join(f'{key}: {value}' for key, value in summary['coverage'].items())
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(summary['domain'])} browser accessibility review</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:1000px;margin:40px auto;padding:0 24px}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ddd}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}section{{margin:28px 0}}</style>
<h1>Browser-based accessibility review — axe not run</h1><p>{esc(summary['domain'])} · {esc(summary['generatedAt'])}</p>
<p>{esc(summary['limitation'])}</p><p>Automation prerequisite: {esc(summary['automationBlocker'])}</p>
<p>Automated scans completed: 0. Automated critical, serious, moderate and minor counts: unknown.</p>
<p>{esc(coverage)}. Traffic window: {esc(summary['trafficWindow'])}</p>
<h2>Reviewed and unreviewed scope</h2><table><tr><th>Page</th><th>Review status</th><th>Pageviews</th><th>Inspected</th></tr>{page_rows}</table>
<h2>Manual observations and checks</h2>{''.join(observations) or '<p>No reviewed observations supplied.</p>'}
<h2>Coverage limits and review failures</h2><ul>{limitations}{failures}</ul></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = summarize(json.loads(args.input.read_text()))
    except (ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f'Invalid browser review: {exc}\n')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = args.output_dir / 'accessibility-browser-review.html'
    report.write_text(render(summary))
    (args.output_dir / 'accessibility-browser-review.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(f'Created limited browser review (not axe): {report}')


if __name__ == '__main__':
    main()
