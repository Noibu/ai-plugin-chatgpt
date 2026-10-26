"""Build consistent audit summary, native action board and optional real PDF.

Inputs are completed axe findings or the separate browser-review contract.
ReportLab is optional and must be available in the host for --pdf. No scans,
network requests, repository changes or tickets are executed by this helper.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape

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
        axe.require(isinstance(annotation, dict) and set(annotation) <= {'explanation', 'suggestedFix', 'verification', 'criterion', 'criterionUrl', 'ownership'}, 'Invalid annotation fields')
        axe.require(all(isinstance(v, str) and v.strip() and len(v) <= 10000 for v in annotation.values()), 'Invalid annotation text')
        axe.require(annotation.get('ownership') in {None, 'merchant-code', 'merchant-content', 'vendor', 'unknown'}, 'Invalid owner')
        if 'criterionUrl' in annotation:
            axe.require(axe.safe_url(annotation['criterionUrl']), 'Invalid criterion link')
        finding.update(annotation)
    return summary


def chat_summary(summary):
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


def create_pdf(summary, output):
    try:
        import reportlab
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    except ImportError as exc:
        raise ValueError('PDF not created: ReportLab is unavailable. Use the host PDF tools or provide the HTML fallback explicitly.') from exc
    font_dir = Path(reportlab.__file__).parent / 'fonts'
    for name, file in [('Audit', 'Vera.ttf'), ('AuditBold', 'VeraBd.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(font_dir / file)))
    pdfmetrics.registerFontFamily('Audit', normal='Audit', bold='AuditBold', italic='Audit', boldItalic='AuditBold')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('AuditBody', fontName='Audit', fontSize=9, leading=13, spaceAfter=7, splitLongWords=True))
    styles.add(ParagraphStyle('AuditTitle', parent=styles['AuditBody'], fontSize=21, leading=26, spaceAfter=12))
    styles.add(ParagraphStyle('AuditH2', parent=styles['AuditBody'], fontSize=14, leading=19, spaceBefore=10, spaceAfter=10, keepWithNext=True))
    styles.add(ParagraphStyle('AuditH3', parent=styles['AuditBody'], fontName='AuditBold', fontSize=10, leading=14, spaceBefore=8, keepWithNext=True))
    styles.add(ParagraphStyle('AuditSmall', parent=styles['AuditBody'], fontSize=7.8, leading=11))
    styles.add(ParagraphStyle('AuditCode', parent=styles['AuditSmall'], backColor=colors.HexColor('#f3f4f6'), borderPadding=6, spaceBefore=5, spaceAfter=10, wordWrap='CJK'))
    styles.add(ParagraphStyle('AuditCount', parent=styles['AuditBody'], fontSize=22, leading=30, alignment=TA_CENTER))
    styles.add(ParagraphStyle('AuditCountLabel', parent=styles['AuditSmall'], alignment=TA_CENTER))
    def clean(value):
        return str(value).replace('\u2011', '-').replace('\u2013', '-').replace('\u2014', '-')
    def p(value, style='AuditBody', verbatim=False):
        return Paragraph(escape(str(value) if verbatim else clean(value)).replace('\n', '<br/>'), styles[style])
    def url(value, label):
        if axe.safe_url(value) and not re.search(r'[\x00-\x20]', value):
            return Paragraph('<link href="' + escape(value, {'"': '&quot;'}) + '" color="#2454ad">' + escape(clean(label)) + '</link>', styles['AuditSmall'])
        return p(label, 'AuditSmall')
    def table(rows, widths):
        result = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
        result.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e9edf2')), ('VALIGN',(0,0),(-1,-1),'TOP'), ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f7f8fa')]), ('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#9aa3ae')), ('TOPPADDING',(0,0),(-1,-1),7), ('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        return result
    def affected_pages(values):
        parts = []
        for value in values:
            label = urlsplit(value).path or '/'
            if axe.safe_url(value) and not re.search(r'[\x00-\x20]', value):
                parts.append('<link href="' + escape(value, {'"':'&quot;'}) + '" color="#2454ad">' + escape(clean(label)) + '</link>')
            else:
                parts.append(escape(clean(label)))
        return Paragraph('; '.join(parts), styles['AuditSmall'])
    manual = summary['mode'] == 'browser-review'
    title = 'Browser-based accessibility review - axe not run' if manual else 'Accessibility Audit'
    story = [p(title, 'AuditTitle'), p(summary['domain'] + ' | ' + str(summary['standard'])), p('Report generated: ' + summary['generatedAt'], 'AuditSmall')]
    reference_copy = axe.reference_copy_applies(summary)
    executive = chat_summary(summary)
    if reference_copy:
        story.append(p(axe.CLAUDE_DISCLAIMER, 'AuditSmall', verbatim=True))
        executive = executive.removesuffix('\n\n' + axe.CLAUDE_DISCLAIMER)
    story += [p('Executive summary', 'AuditH2'), p(executive.replace('\n\n','\n'), verbatim=reference_copy)]
    if not manual:
        palette = ['#fae8e8', '#fff1dc', '#fcf5da', '#eef1f5']
        cells = [[p(str(summary['severityCounts'][key]), 'AuditCount'), p(key.title(), 'AuditCountLabel')] for key in axe.WEIGHTS]
        totals = Table([cells], colWidths=[126]*4)
        totals.setStyle(TableStyle([('BACKGROUND',(i,0),(i,0),colors.HexColor(color)) for i,color in enumerate(palette)] + [('VALIGN',(0,0),(-1,-1),'TOP'), ('BOX',(0,0),(-1,-1),.5,colors.HexColor('#d3d8df'))]))
        story += [p('Pooled unique fixes by severity', 'AuditH3'), totals, Spacer(1,12)]
    story += [p('Page coverage', 'AuditH2')]
    rows = [[p(x, 'AuditSmall') for x in ['Page', 'Status', 'Pageviews', 'Instances']]]
    for page in summary['pages']:
        label = urlsplit(page['url']).path or '/'
        count = page.get('violationInstances')
        rows.append([url(page['url'], label), p(page['status'], 'AuditSmall'), p(f'{page["pageviews"]:,}' if page.get('pageviews') is not None else 'Unknown', 'AuditSmall'), p(str(count) if count is not None else 'Unknown / not axe', 'AuditSmall')])
    story += [table(rows,[250,86,80,88])]
    if not manual:
        rows = [[p(x, 'AuditSmall') for x in ['Page', 'Violated rules', 'Affected elements', 'Incomplete checks']]]
        for page in summary['pages']:
            rows.append([url(page['url'], urlsplit(page['url']).path or '/')] + [p(page.get(key) if page.get(key) is not None else 'Unknown', 'AuditSmall') for key in ['violatedRuleCount', 'affectedElementCount', 'incompleteCount']])
        story += [p('Per-page scanner counts', 'AuditH3'), table(rows,[250,80,87,87])]
    for note in summary.get('notes', []):
        story.append(p(note, 'AuditSmall'))
    ranking_note = 'Manual observations are listed separately; no automated ranking or shared-component pooling was performed.' if manual else 'Priority uses observed severity, known page traffic and verified shared-component breadth. Traffic is not a count of affected people.'
    story += [PageBreak(), p('Key manual observations' if manual else 'Key findings', 'AuditH2'), p(ranking_note, 'AuditSmall')]
    rows = [[p(x, 'AuditSmall') for x in ['#', 'Finding', 'Severity', 'Pages / pageviews']]]
    for number, finding in enumerate(summary['findings'],1):
        rows.append([p(number, 'AuditSmall'), p(finding['help'], 'AuditSmall'), p(finding['impact'] or 'Unknown', 'AuditSmall'), p(str(len(finding['pages'])) + ' / ' + str(finding['knownPageviews']) + ('' if finding['trafficComplete'] else ' known; partial'), 'AuditSmall')])
    story += [table(rows,[25,275,80,124]), p('Finding details', 'AuditH2')]
    for number, finding in enumerate(summary['findings'],1):
        story += [KeepTogether([p(f'{number}. {finding["help"]}', 'AuditH3'), p(f'ID: {finding["id"]} | Severity: {finding["impact"] or "Unknown"} | Pages: {len(finding["pages"])} | Known pageviews: {finding["knownPageviews"]:,}' + ('' if finding['trafficComplete'] else ' (partial)'), 'AuditSmall')])]
        if finding.get('criterion'):
            story.append(p('Criterion: ' + finding['criterion']))
        if finding.get('criterionUrl') or finding.get('helpUrl'):
            story.append(url(finding.get('criterionUrl') or finding.get('helpUrl'), 'Rule / criterion reference'))
        story += [p(finding.get('explanation') or finding['instances'][0]['failureSummary'] or finding['help']), p('Selector / target', 'AuditH3'), p(finding['selector'], 'AuditCode')]
        example = finding['instances'][0]
        if example.get('html'):
            story += [p('Example HTML (escaped evidence)', 'AuditH3'), p(example['html'], 'AuditCode')]
        story += [p('Suggested fix', 'AuditH3'), p(finding.get('suggestedFix', 'No verified remediation supplied. Inspect the component and owner before changing source.')), p('Verification', 'AuditH3'), p(finding.get('verification', 'Rerun the relevant check and manually verify the affected control and assistive-technology behavior.'))]
        story += [p('Scanned / reviewed pages affected', 'AuditH3'), affected_pages(finding['pages'])]
        story.append(Spacer(1,14))
    story += [p('Manual-review checks and limitations', 'AuditH2'), p('Incomplete checks are not confirmed violations. Unscanned pages are not clean; frame, hidden-state, keyboard and assistive-technology coverage require explicit verification.')]
    for page in summary['pages']:
        if page.get('incomplete') or page.get('error') or page.get('limitations'):
            story += [url(page['url'], page['url']), p(json.dumps({key:page[key] for key in ['incomplete','error','limitations','scanner','scanOptions','completedAt'] if page.get(key)}, ensure_ascii=False), 'AuditSmall')]
    for check in summary.get('reviewChecks', []):
        if check['status'] != 'issue-observed':
            story.append(p(f'{check["url"]} | {check["title"]} | {check["status"]}: {check.get("evidence", "Not tested")}', 'AuditSmall'))
    story += [p('The accompanying JSON preserves complete node instances and scanner/review provenance. This PDF is an informational report, not a compliance certification.', 'AuditSmall')]
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#d3d8df'))
        canvas.line(54,42,558,42)
        canvas.setFont('Audit',7)
        canvas.drawString(54,29,clean(summary['domain'])[:55] + ' | ' + ('Limited review - axe not run' if manual else 'Automated accessibility report'))
        canvas.drawRightString(558,29,'Page ' + str(doc.page))
        canvas.restoreState()
    doc = SimpleDocTemplate(str(output), pagesize=letter, leftMargin=54, rightMargin=54, topMargin=50, bottomMargin=58, title=title + ' - ' + summary['domain'], author='Noibu')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--annotations', type=Path)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--pdf', action='store_true')
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
        html_report = review.render(review.summarize(data)) if summary['mode'] == 'browser-review' else axe.render(summary)
        (args.output_dir / 'accessibility-report.html').write_text(html_report)
        if args.board:
            axe.require(args.window_start and args.window_end, 'Action board needs actual measured window-start/window-end, not guessed dates')
            presentation, fragment = board(summary, {'start':args.window_start, 'end':args.window_end, 'label':summary['trafficWindow']}, args.domain_id)
            (args.output_dir / 'accessibility-board.json').write_text(json.dumps(presentation, indent=2, ensure_ascii=False) + '\n')
            (args.output_dir / 'accessibility-board.html').write_text(fragment)
        if args.pdf:
            filename = 'accessibility-browser-review.pdf' if summary['mode'] == 'browser-review' else 'accessibility-audit.pdf'
            create_pdf(summary, args.output_dir / filename)
            print('Created PDF: ' + str(args.output_dir / filename) + '. Render and inspect every page before delivery; link existence is not verified by this helper.')
        print('Created evidence, summary' + (' and native board source' if args.board else '') + '; no scan, PR or ticket executed.')
    except (ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f'Could not complete deliverables: {exc}\n')


if __name__ == '__main__':
    main()
