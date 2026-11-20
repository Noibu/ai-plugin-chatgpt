"""Build consistent audit summary, native action board and optional real PDF.

Inputs are completed axe findings or the separate browser-review contract.
ReportLab is optional and must be available in the host for --pdf. No scans,
network requests, repository changes or tickets are executed by this helper.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


HERE = Path(__file__).resolve().parent
axe = module('audit_results', HERE / 'build_report.py')
review = module('audit_review', HERE / 'build_review.py')


def normalize(data, annotations=None):
    axe.require(isinstance(data, dict), 'Expected an audit or browser-review object')
    if 'scan_index' in data and 'scans' in data:
        axe.require(not annotations, 'Imported bundles retain original evidence; annotations are not supported for this mode')
        importer_path = HERE / 'import_axe_bundle.py'
        axe.require(importer_path.exists(), 'Multi-state imports require the accessibility recovery/import update (import_axe_bundle.py)')
        importer = module('audit_import', importer_path)
        importer.validate_bundle(data)
        return module('imported_pdf', HERE / 'imported_presentation.py').normalize(data, importer)
    if data.get('schema') == 'noibu.accessibility-review/1':
        axe.require(not annotations, 'Browser review already contains recommendations; do not attach axe annotations')
        source = review.summarize(data)
        findings = []
        for page in source['pages']:
            for check in page['checks']:
                if check['status'] != 'issue-observed':
                    continue
                identity = 'review-' + hashlib.sha256((page['url'] + '\n' + check['id']).encode()).hexdigest()[:16]
                findings.append({'id': identity, 'rule': check['id'], 'help': check['title'], 'impact': check.get('impact'), 'selector': check['target'], 'knownPageviews': page['pageviews'] or 0, 'trafficComplete': page['pageviews'] is not None, 'pages': {page['url']: page['pageviews']}, 'instances': [{'url': page['url'], 'target': [check['target']], 'html': '', 'failureSummary': check['evidence']}], 'suggestedFix': check['recommendation'], 'verification': 'Verify this manual observation in the same rendered state; axe was not run.', 'ownership': 'unknown'})
        return {'mode': 'browser-review', 'domain': source['domain'], 'generatedAt': source['generatedAt'], 'standard': 'Limited browser review; not a WCAG pass', 'trafficWindow': source['trafficWindow'], 'pages': source['pages'], 'states': source['coverage'], 'rawInstances': None, 'uniqueFixes': None, 'severityCounts': source['automatedSeverityCounts'], 'manualIssueCounts': source['manualIssueSeverityCounts'], 'findings': findings, 'notes': [source['limitation'], source['automationBlocker']], 'reviewChecks': source['observations']}
    summary = axe.pool(data)
    annotations = annotations or {}
    axe.require(isinstance(annotations, dict) and set(annotations) <= {f['id'] for f in summary['findings']}, 'Annotations need actual pooled finding IDs')
    for finding in summary['findings']:
        annotation = annotations.get(finding['id'], {})
        axe.require(isinstance(annotation, dict) and set(annotation) <= {'title', 'explanation', 'userImpact', 'evidenceStatus', 'verificationEvidence', 'suggestedFix', 'verification', 'criterion', 'criterionUrl', 'ownership'}, 'Invalid annotation fields')
        axe.require(all(isinstance(v, str) and v.strip() and len(v) <= 10000 for v in annotation.values()), 'Invalid annotation text')
        axe.require(annotation.get('ownership') in {None, 'merchant-code', 'merchant-content', 'vendor', 'unknown'}, 'Invalid owner')
        axe.require(annotation.get('evidenceStatus') in {None, 'scanner-detected', 'manually-verified'}, 'Invalid evidence status')
        axe.require(annotation.get('evidenceStatus') != 'manually-verified' or annotation.get('verificationEvidence'), 'Manually verified findings need recorded verification evidence')
        if 'criterionUrl' in annotation:
            axe.require(axe.safe_url(annotation['criterionUrl']), 'Invalid criterion link')
        finding.update(annotation)
    return summary


def chat_summary(summary):
    if summary['mode'] == 'axe-import':
        return summary['importSummary'] + '\n\nImported original results, not fresh scans. Severity totals count unpooled rule/scan records: ' + '; '.join(f'{key}: {value}' for key,value in summary['severityCounts'].items()) + '. Unique affected elements and pooled fixes are unknown; incomplete checks remain separate.\n\nAutomated checks are not a compliance certification.'
    manual = summary['mode'] == 'browser-review'
    completed = sum(p['status'] == ('REVIEWED' if manual else 'COMPLETED') for p in summary['pages'])
    eligible = [p for p in summary['pages'] if p['status'] == ('REVIEWED' if manual else 'COMPLETED')]
    known = sum(p.get('pageviews') or 0 for p in eligible)
    partial = any(p.get('pageviews') is None for p in eligible)
    heading = 'Browser-based accessibility review - axe not run' if manual else 'Automated accessibility audit'
    lines = [heading, f'{summary["domain"]}: {completed} of {len(summary["pages"])} selected pages {"reviewed" if manual else "have completed automated results"}.', f'Traffic window: {summary["trafficWindow"]}. Known pageviews across those pages: {known:,}' + (' (partial traffic coverage).' if partial else '.')]
    if manual:
        lines += [f'Automated scans completed: 0. All automated severity counts: unknown. Confirmed manual observations: {len(summary["findings"])}; these are not pooled axe fixes.']
    else:
        if axe.reference_copy_applies(summary):
            lines += [axe.CLAUDE_STANDARD_STATEMENT]
        instances = 'instance' if summary['rawInstances'] == 1 else 'instances'
        fixes = 'fix' if summary['uniqueFixes'] == 1 else 'fixes'
        lines += [f'{summary["rawInstances"]} violation {instances} pooled into {summary["uniqueFixes"]} unique {fixes}.', '; '.join(f'{key}: {value}' for key, value in summary['severityCounts'].items()) + '.']
        lines += [f'{summary["violatedRuleCount"]} distinct violated rules / {summary["affectedElementCount"]} affected elements (unique page/target pairs). Severity totals above count pooled fixes.', f'{summary["incompleteCheckCount"]} known incomplete check records across completed pages' + (' (partial: some completed pages did not supply incomplete results)' if not summary['incompleteCountComplete'] else '') + '; these are not confirmed violations.']
    if summary['findings']:
        top = summary['findings'][0]
        lines += [f'Top finding: {top["help"]}. Observed on {len(top["pages"])} page(s); {top["knownPageviews"]:,} known pageviews in that page set' + (' (partial traffic coverage).' if not top['trafficComplete'] else '.') + ' Pageviews are exposure context, not affected people.']
    lines += [axe.CLAUDE_DISCLAIMER if axe.reference_copy_applies(summary) else 'Automated checks and limited reviews are not a compliance certification. Manual keyboard and assistive-technology testing remain necessary.']
    return '\n\n'.join(lines)


def board(summary, window, domain_id=None):
    axe.require(summary['mode'] != 'axe-import', 'Imported scan states are not verified pooled fixes; use their report before selecting remediation actions')
    ui = module('audit_board', HERE.parent.parent / 'querying-noibu-data/scripts/build_presentation.py')
    identity = 'audit-' + hashlib.sha256(json.dumps([summary['domain'], window, summary['generatedAt']], sort_keys=True).encode()).hexdigest()[:16]
    panel_summary = ('Browser-based accessibility review - axe not run. Automated severity counts remain unknown. ' if summary['mode'] == 'browser-review' else '') + 'Choose a scoped next step for the confirmed findings in the audit report.'
    if not summary['findings']:
        panel_summary = ('Browser-based accessibility review - axe not run. Automated severity counts remain unknown. ' if summary['mode'] == 'browser-review' else '') + 'No confirmed findings are available for PR/ticket creation. See the report coverage and limitations.'
    data = {'schema': 'noibu.presentation/1', 'auditLayout': 'summary-actions', 'reportId': identity, 'workflow': 'accessibility-audit', 'domain': {'name': summary['domain']}, 'window': window, 'generatedAt': summary['generatedAt'], 'summary': panel_summary, 'findings': [], 'caveats': summary.get('notes', [])[:10] + ['A Page/file/board does not create a PR or ticket. Use the selected remediation action and resolve its destination first.']}
    if domain_id:
        data['domain']['id'] = domain_id
    for finding in summary['findings'][:12]:
        data['findings'].append({'id': finding['id'], 'title': finding['help'], 'category': 'vendor' if finding.get('ownership') == 'vendor' else 'accessibility', 'ownership': finding.get('ownership', 'unknown'), 'tag': ('Manual observation' if summary['mode'] == 'browser-review' else finding['impact'] or 'Needs review'), 'evidence': finding.get('explanation') or finding['instances'][0]['failureSummary'] or finding['help'], 'impact': f'{len(finding["pages"])} pages; {finding["knownPageviews"]:,} known pageviews' + (' (partial)' if not finding['trafficComplete'] else ''), 'fix': finding.get('suggestedFix', 'Source and ownership verification are needed before proposing a code change.')})
    return data, ui.render(data)


def create_pdf(summary, output, technical_appendix=False):
    pdf = module('audit_pdf', HERE / 'pdf_report.py')
    pdf.create_pdf(summary, output, technical_appendix=technical_appendix,
                   reference_copy=axe.reference_copy_applies(summary),
                   disclaimer=axe.CLAUDE_DISCLAIMER,
                   standard_statement=axe.CLAUDE_STANDARD_STATEMENT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--pdf', action='store_true')
    parser.add_argument('--technical-appendix', action='store_true', help='Append scan metadata and incomplete-rule references to the PDF')
    parser.add_argument('--board', action='store_true')
    parser.add_argument('--window-start')
    parser.add_argument('--window-end')
    parser.add_argument('--domain-id')
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text())
        summary = normalize(data, json.loads(args.annotations.read_text()) if args.annotations else None)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / 'accessibility-summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        (args.output_dir / 'accessibility-evidence.json').write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        (args.output_dir / 'accessibility-chat-summary.md').write_text(chat_summary(summary) + '\n')
        if summary['mode'] == 'axe-import':
            html_report = module('audit_import_html', HERE / 'import_axe_bundle.py').render(summary['importedSummary'])
        else:
            html_report = review.render(review.summarize(data)) if summary['mode'] == 'browser-review' else axe.render(summary)
        (args.output_dir / 'accessibility-report.html').write_text(html_report)
        if args.board:
            axe.require(args.window_start and args.window_end, 'Action board needs actual measured window-start/window-end, not guessed dates')
            presentation, fragment = board(summary, {'start':args.window_start, 'end':args.window_end, 'label':summary['trafficWindow']}, args.domain_id)
            (args.output_dir / 'accessibility-board.json').write_text(json.dumps(presentation, indent=2, ensure_ascii=False) + '\n')
            (args.output_dir / 'accessibility-board.html').write_text(fragment)
        if args.pdf:
            filename = 'accessibility-browser-review.pdf' if summary['mode'] == 'browser-review' else 'accessibility-audit.pdf'
            create_pdf(summary, args.output_dir / filename, args.technical_appendix)
            print('Created PDF: ' + str(args.output_dir / filename) + '. Render and inspect every page before delivery; link existence is not verified by this helper.')
        print('Created evidence, summary' + (' and native board source' if args.board else '') + '; no scan, PR or ticket executed.')
    except (ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f'Could not complete deliverables: {exc}\n')


if __name__ == '__main__':
    main()
