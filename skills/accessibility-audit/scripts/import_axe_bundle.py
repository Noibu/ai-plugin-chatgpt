"""Validate and report a multi-state bundle of original axe.run() results."""
import argparse
import html
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def required(condition, message):
    if not condition:
        raise ValueError(message)


def valid_url(value):
    p = urlparse(value) if isinstance(value, str) else None
    return bool(p and p.scheme in {'http', 'https'} and p.hostname and not p.username and not p.password)


def load_bundle(path):
    data = json.loads(path.read_text())
    required(isinstance(data, dict) and valid_url(data.get('page')), 'Missing page URL')
    scans = data.get('scans')
    index = data.get('scan_index')
    required(isinstance(scans, dict) and scans, 'Missing scans')
    required(isinstance(index, list) and len(index) == len(scans), 'Scan index does not match results')
    labels = [item.get('label') for item in index if isinstance(item, dict)]
    required(len(labels) == len(index) and len(set(labels)) == len(labels) and set(labels) == set(scans), 'Invalid scan labels')
    for label, scan in scans.items():
        required(isinstance(scan, dict) and valid_url(scan.get('url')), f'{label}: missing result URL')
        required(isinstance(scan.get('testEngine'), dict) and scan['testEngine'].get('name') == 'axe-core' and scan['testEngine'].get('version'), f'{label}: missing axe engine/version')
        required(isinstance(scan.get('toolOptions'), dict), f'{label}: missing axe options')
        required(isinstance(scan.get('timestamp'), str), f'{label}: missing timestamp')
        try:
            parsed_time = datetime.fromisoformat(scan['timestamp'].replace('Z', '+00:00'))
            required(parsed_time.tzinfo is not None and parsed_time.utcoffset() is not None, f'{label}: timestamp needs timezone')
        except ValueError as exc:
            raise ValueError(f'{label}: invalid timestamp') from exc
        for key in ('violations', 'incomplete', 'passes', 'inapplicable'):
            required(isinstance(scan.get(key), list), f'{label}: missing {key} array')
        for kind in ('violations', 'incomplete'):
            for rule in scan[kind]:
                required(isinstance(rule, dict) and isinstance(rule.get('id'), str) and isinstance(rule.get('nodes'), list), f'{label}: invalid {kind} rule')
                for node in rule['nodes']:
                    required(isinstance(node, dict) and isinstance(node.get('target'), list), f'{label}: invalid node target')
    return data


def summarize(data):
    rules = defaultdict(lambda: {'scans': set(), 'nodes': 0, 'impacts': set(), 'tags': set(), 'help': '', 'helpUrl': '', 'examples': []})
    incomplete = defaultdict(lambda: {'scans': set(), 'nodes': 0})
    rows = []
    for item in data['scan_index']:
        label = item['label']
        scan = data['scans'][label]
        rows.append({'label': label, 'url': scan['url'], 'timestamp': scan['timestamp'], 'viewport': item.get('viewport'), 'state': item.get('state'), 'scope': item.get('scope'), 'engine': scan['testEngine'], 'options': scan['toolOptions'], 'violatedRules': len(scan['violations']), 'violationNodes': sum(len(x['nodes']) for x in scan['violations']), 'incompleteRules': len(scan['incomplete']), 'incompleteNodes': sum(len(x['nodes']) for x in scan['incomplete']), 'passedRules': len(scan['passes']), 'inapplicableRules': len(scan['inapplicable'])})
        for kind, dest in (('violations', rules), ('incomplete', incomplete)):
            for rule in scan[kind]:
                entry = dest[rule['id']]
                entry['scans'].add(label)
                entry['nodes'] += len(rule['nodes'])
                if kind == 'violations':
                    entry['impacts'].add(rule.get('impact'))
                    entry['tags'].update(rule.get('tags', []))
                    entry['help'] = rule.get('help', rule['id'])
                    entry['helpUrl'] = rule.get('helpUrl', '')
                    for node in rule['nodes']:
                        entry['examples'].append({'scan': label, 'target': node['target'], 'html': node.get('html', ''), 'failureSummary': node.get('failureSummary', '')})
    def clean_rules(source, violations=False):
        result = []
        for rule_id, entry in source.items():
            row = {'id': rule_id, 'scans': sorted(entry['scans']), 'nodes': entry['nodes']}
            if violations:
                row.update({'impacts': sorted(x for x in entry['impacts'] if x), 'tags': sorted(entry['tags']), 'help': entry['help'], 'helpUrl': entry['helpUrl'], 'examples': entry['examples']})
                row['category'] = 'best-practice only' if 'best-practice' in entry['tags'] and not any(t.startswith('wcag') for t in entry['tags']) else ('WCAG tagged' if any(t.startswith('wcag') for t in entry['tags']) else 'Unclassified')
            result.append(row)
        return sorted(result, key=lambda x: (-x['nodes'], x['id']))
    return {'mode': 'imported axe bundle', 'sourcePage': data['page'], 'sourceGenerated': data.get('generated'), 'engine': data.get('engine'), 'ruleTagsRun': data.get('rule_tags_run'), 'scanCount': len(rows), 'scans': rows, 'distinctPages': len({s['url'] for s in rows}), 'distinctViolatedRules': len(rules), 'violationRuleScanInstances': sum(r['violatedRules'] for r in rows), 'violationNodeScanInstances': sum(r['violationNodes'] for r in rows), 'incompleteRuleScanInstances': sum(r['incompleteRules'] for r in rows), 'incompleteNodeScanInstances': sum(r['incompleteNodes'] for r in rows), 'violations': clean_rules(rules, True), 'incomplete': clean_rules(incomplete), 'manualChecks': data.get('manual_checks', []), 'videoCaptions': data.get('video_captions', []), 'notes': data.get('notes', [])}


def render(summary):
    esc = lambda value: html.escape(str(value))
    scan_rows = ''.join(f'<tr><td>{esc(s["label"])}</td><td>{esc(s["state"])}</td><td>{esc(s["scope"])}</td><td>{esc(s["viewport"])}</td><td>{s["violatedRules"]}</td><td>{s["incompleteRules"]}</td></tr>' for s in summary['scans'])
    findings = []
    for rule in summary['violations']:
        nodes = ''.join(f'<details><summary>{esc(x["scan"])} · {esc(x["target"])}</summary><pre>{esc(x["html"])}</pre><pre>{esc(x["failureSummary"])}</pre></details>' for x in rule['examples'])
        help_link = f'<a href="{esc(rule["helpUrl"])}">axe rule help</a>' if valid_url(rule['helpUrl']) else ''
        findings.append(f'<section><h3>{esc(rule["id"])} · {esc(rule["category"])} · {esc(", ".join(rule["impacts"]))}</h3><p>{esc(rule["help"])}. {rule["nodes"]} node instances in {len(rule["scans"])} scans. {help_link}</p>{nodes}</section>')
    incomplete_rows = ''.join(f'<tr><td>{esc(x["id"])}</td><td>{len(x["scans"])}</td><td>{x["nodes"]}</td></tr>' for x in summary['incomplete'])
    notes = ''.join(f'<li>{esc(x)}</li>' for x in summary['notes'])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Imported axe results</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#20212b}}table{{border-collapse:collapse;width:100%}}th,td{{padding:.5rem;text-align:left;border-bottom:1px solid #ddd;vertical-align:top}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f5f7;padding:.5rem}}section{{margin:2rem 0}}details{{margin:.5rem 0}}</style>
<h1>Imported axe results</h1><p>Source page: <a href="{esc(summary['sourcePage'])}">{esc(summary['sourcePage'])}</a></p><p>Original scans: {summary['scanCount']} across {summary['distinctPages']} distinct page(s); engine {esc(summary['engine'])}. These are imported completed results with their original timestamps and options, not fresh ChatGPT browser scans. Scan counts describe states and scoped elements, not separate pages.</p>
<p>{summary['distinctViolatedRules']} distinct violated rules; {summary['violationRuleScanInstances']} rule/scan instances; {summary['violationNodeScanInstances']} node/scan instances. {summary['incompleteRuleScanInstances']} incomplete rule/scan records and {summary['incompleteNodeScanInstances']} incomplete node/scan records require review. Repeated elements across states are counted each time scanned.</p>
<h2>Coverage</h2><table><tr><th>Scan</th><th>State</th><th>Scope</th><th>Viewport</th><th>Violation rules</th><th>Incomplete rules</th></tr>{scan_rows}</table>
<h2>Confirmed axe violations</h2>{''.join(findings)}<h2>Incomplete checks</h2><table><tr><th>Rule</th><th>Scans</th><th>Node instances</th></tr>{incomplete_rows}</table>
<h2>Source notes</h2><ul>{notes}</ul><p>Automated checks and imported manual notes do not establish complete accessibility coverage. The source JSON retains passes, inapplicable rules, options, all nodes, and original timestamps.</p></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        data = load_bundle(args.input)
        summary = summarize(data)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(1, f'Invalid axe bundle: {exc}\n')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'imported-axe-evidence.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    (args.output_dir / 'imported-axe-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    (args.output_dir / 'imported-axe-report.html').write_text(render(summary))
    print(f'Imported {summary["scanCount"]} scans; {summary["distinctViolatedRules"]} violated rules; {summary["violationNodeScanInstances"]} node/scan instances')


if __name__ == '__main__':
    main()
