"""Compact audit PDF presentation. Counting and evidence stay in the normalizers."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
from xml.sax.saxutils import escape


TITLES = {
    'aria-required-parent': 'An ARIA role lacks its required parent structure',
    'svg-img-alt': 'An SVG image has no text alternative',
    'label-content-name-mismatch': 'Visible link text is missing from its accessible name',
    'link-name': 'A link has no accessible name',
    'link-in-text-block': 'An inline link relies on color alone',
}


def page_name(page):
    """Prefer supplied editorial labels, then a readable URL path, never guessed traffic."""
    if page.get('label'):
        return page['label']
    path = unquote(urlsplit(page['url']).path).strip('/')
    if not path:
        return 'Homepage'
    parts = re.sub(r'\.(html?|aspx?)$', '', path).split('/')
    words = ' '.join(parts).replace('-', ' ').split()
    return ' '.join({'womens': "Women's", 'mens': "Men's", 'women': "Women's Landing",
                     'men': "Men's Landing"}.get(word.lower(), word.capitalize()) for word in words)


def criteria(finding):
    if finding.get('criterion'):
        return finding['criterion']
    values = set()
    for tag in finding.get('tags', []):
        match = re.fullmatch(r'wcag(\d)(\d)(\d+)', tag)
        if match:
            values.add('.'.join(match.groups()))
    return ', '.join(sorted(values)) or ('Best practice (not WCAG)' if 'best-practice' in finding.get('tags', []) else 'Not supplied')


def number(value):
    return f'{value:,}' if isinstance(value, (int, float)) else 'Unknown'


def create_pdf(summary, output, *, technical_appendix=False, reference_copy=False,
               disclaimer='', standard_statement=''):
    try:
        import reportlab
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    except ImportError as exc:
        raise ValueError('PDF not created: ReportLab is unavailable. Use the HTML companion.') from exc

    fonts = Path(reportlab.__file__).parent / 'fonts'
    for name, filename in [('Audit', 'Vera.ttf'), ('AuditBold', 'VeraBd.ttf'), ('AuditMono', 'Vera.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    pdfmetrics.registerFontFamily('Audit', normal='Audit', bold='AuditBold', italic='Audit', boldItalic='AuditBold')
    styles = {
        'body': ParagraphStyle('body', fontName='Audit', fontSize=8.4, leading=11.6, spaceAfter=5),
        'small': ParagraphStyle('small', fontName='Audit', fontSize=7, leading=9.2, spaceAfter=4),
        'title': ParagraphStyle('title', fontName='AuditBold', fontSize=19, leading=23, spaceAfter=7),
        'h2': ParagraphStyle('h2', fontName='AuditBold', fontSize=12, leading=16, spaceBefore=9, spaceAfter=6, keepWithNext=True),
        'h3': ParagraphStyle('h3', fontName='AuditBold', fontSize=9.5, leading=13, spaceBefore=9, spaceAfter=5, keepWithNext=True),
        'code': ParagraphStyle('code', fontName='AuditMono', fontSize=6.8, leading=9, backColor=colors.HexColor('#f3f3f3'), borderPadding=5, spaceBefore=4, spaceAfter=8, wordWrap='CJK'),
        'count': ParagraphStyle('count', fontName='AuditBold', fontSize=22, leading=28, alignment=TA_CENTER),
        'countlabel': ParagraphStyle('countlabel', fontName='Audit', fontSize=7.5, leading=10, alignment=TA_CENTER),
        'thead': ParagraphStyle('thead', fontName='AuditBold', fontSize=7, leading=9, textColor=colors.white),
    }
    def p(value, style='body'):
        # Every supplied string, including node HTML, is untrusted evidence.
        return Paragraph(escape(str(value)).replace('\n', '<br/>'), styles[style])

    def safe_url(value):
        if not isinstance(value, str) or re.search(r'[\x00-\x20]', value): return False
        try:
            parsed = urlsplit(value)
            return parsed.scheme in {'https', 'http'} and bool(parsed.hostname) and not parsed.username and not parsed.password
        except ValueError:
            return False

    def link(value, label, style='small'):
        if not safe_url(value): return p(label, style)
        return Paragraph('<link href="' + escape(value, {'"': '&quot;'}) + '" color="#24628b">' + escape(str(label)) + '</link>', styles[style])

    def table(headers, rows, widths):
        result = Table([[p(x, 'thead') for x in headers]] + rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
        result.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#252525')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#f4f5f6')]),
            ('GRID',(0,0),(-1,-1),.3,colors.HexColor('#dddddd')),
            ('VALIGN',(0,0),(-1,-1),'TOP'), ('TOPPADDING',(0,0),(-1,-1),5),
            ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ]))
        return result

    mode = summary['mode']
    manual = mode == 'browser-review'
    imported = mode == 'axe-import'
    pages = summary['pages']
    names = {page['url']: page_name(page) for page in pages}
    completed = [page for page in pages if page['status'] == ('REVIEWED' if manual else 'COMPLETED')]
    counts = Counter(page['status'] for page in pages)
    known_traffic = sum(page.get('pageviews') or 0 for page in completed)
    partial_traffic = any(page.get('pageviews') is None for page in completed)
    title = summary['domain'] + (' Accessibility Review' if manual else ' Accessibility Audit')
    generated = summary['generatedAt']
    try: date = datetime.fromisoformat(generated.replace('Z', '+00:00')).strftime('%B %d, %Y').replace(' 0', ' ')
    except ValueError: date = generated
    source_times = sorted(page.get('completedAt') or page.get('inspectedAt') for page in completed if page.get('completedAt') or page.get('inspectedAt'))
    story = [p(title, 'title'), p(f'{summary["domain"]}  |  {summary["standard"]}  |  {len(completed)} of {len(pages)} pages ' + ('reviewed' if manual else 'with completed results'), 'small'), p('Report date: ' + date, 'small')]
    if source_times:
        story.append(p('Original evidence: ' + source_times[0] + (' to ' + source_times[-1] if source_times[-1] != source_times[0] else ''), 'small'))
    engines = sorted({str(page['scanner'].get('name','')) + ' ' + str(page['scanner'].get('version','')) for page in completed if page.get('scanner')})
    viewports = sorted({f"{page['viewport'].get('width','?')} × {page['viewport'].get('height','?')}" for page in completed if page.get('viewport')})
    if engines or viewports:
        story.append(p('Engine: ' + (', '.join(engines) or 'Not supplied') + ' | Viewport: ' + (', '.join(viewports) or 'Not supplied'), 'small'))
    story.append(p(disclaimer if reference_copy else 'This report is informational, not legal advice or a compliance certification. Manual keyboard and assistive-technology testing remain necessary.', 'small'))
    story.append(p('Executive summary', 'h2'))
    if manual:
        story += [p('Browser-based accessibility review — axe not run. Automated scans completed: 0. All automated severity counts are unknown.'),
                  p(f'{len(completed)} of {len(pages)} selected pages reviewed; {len(summary["findings"])} confirmed manual observations. These are not automated violations or pooled fixes.')]
    elif imported:
        story += [p(summary['importSummary']), p('These are imported completed axe results with original provenance. Repeated findings count once per scan state. Shared fixes and unique affected elements have not been verified.')]
    else:
        story += [p(f'{len(completed)} of {len(pages)} selected pages have completed automated results. Their known traffic totals {known_traffic:,} pageviews' + (' (partial traffic coverage).' if partial_traffic else '.')),
                  p(f'{summary["rawInstances"]:,} violation instances are grouped into {summary["uniqueFixes"]:,} fixes. The evidence contains {summary["violatedRuleCount"]} distinct violated rules across {summary["affectedElementCount"]:,} affected page/target elements.')]
        if reference_copy: story.append(p(standard_statement))
    story.append(p('Traffic window: ' + summary.get('trafficWindow', 'Not supplied') + '. Pageviews are exposure context, not affected people.', 'small'))
    story.append(p('Coverage: ' + '; '.join(f'{key.lower()}: {value}' for key, value in counts.items()) + '.', 'small'))
    story.append(p('Automated severity counts — ' + ('unknown; axe not run' if manual else 'unpooled rule/scan records' if imported else 'pooled fixes'), 'small'))
    palette = [('#b72424','#fbefed'),('#995400','#fff2e3'),('#8c7000','#fff8df'),('#555555','#f2f2f2')]
    cards = []
    for severity, (ink, fill) in zip(('critical','serious','moderate','minor'), palette):
        value = summary['severityCounts'].get(severity)
        count_style = ParagraphStyle(severity, parent=styles['count'], fontSize=12 if value is None else 22, textColor=colors.HexColor(ink))
        card = Table([[Paragraph(number(value),count_style)],[p(severity.title(),'countlabel')]], colWidths=[116])
        card.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor(fill)),('BOX',(0,0),(-1,-1),.6,colors.HexColor(ink)),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        cards.append(card)
    totals = Table([cards], colWidths=[128]*4)
    totals.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0)]))
    story += [totals]
    if summary['severityCounts'].get('needs_review'):
        story.append(p(f'{summary["severityCounts"]["needs_review"]} further finding groups have unknown severity.', 'small'))
    story.append(p('Pages reviewed' if manual else 'Pages scanned', 'h2'))
    rows = []
    for page in pages:
        rows.append([link(page['url'],names[page['url']]), p(page['status'].title(),'small'), p(number(page.get('pageviews')),'small'),
                     p(number(page.get('violationInstances')),'small'),p(number(page.get('violatedRuleCount')),'small'),
                     p(number(page.get('affectedElementCount')),'small'),p(number(page.get('incompleteCount')),'small')])
    story.append(table(['Page','Status','Pageviews','Instances¹','Rules','Elements','Incomplete'],rows,[142,62,65,60,45,60,78]))
    story.append(p('¹ ' + ('Automated counts unknown; manual observations are listed below.' if manual else 'Imported instances and incomplete records count repeated states separately; elements are unknown.' if imported else 'Instances count rule/node occurrences; elements count unique page/target pairs. Incomplete checks are not confirmed violations.'), 'small'))
    if not manual:
        story.append(p('Needs manual review: ' + number(summary.get('incompleteCheckCount')) + ' incomplete rule records' + ('' if summary.get('incompleteCountComplete',True) else ' (partial; some results did not include incomplete arrays)') + '. Full records, original scan options and node evidence are retained in the accompanying JSON.', 'small'))
    story += [PageBreak(), p('Key manual observations' if manual else 'Key findings','h2'),
              p('Manual observations are separate from automated results.' if manual else 'Imported groups are unpooled and ordered by observed severity and instance count.' if imported else 'Ordered by priority: severity weighted by known page traffic and verified shared-component breadth.','small')]
    findings = summary['findings']
    rows=[]
    for i,f in enumerate(findings,1):
        label = f.get('title') or TITLES.get(f['rule'], f['help'])
        rows.append([p(i,'small'),p(label,'small'),p(criteria(f),'small'),p((f.get('impact') or 'Unknown').upper(),'small')])
    story.append(table(['#','Finding','WCAG criterion','Severity'],rows or [[p('—'),p('No confirmed findings in the supplied evidence.'),p('—'),p('—')]],[24,285,125,78]))
    for i,f in enumerate(findings,1):
        label=f.get('title') or TITLES.get(f['rule'],f['help'])
        traffic=number(f.get('knownPageviews')) + ('' if f.get('trafficComplete') else ' (partial/unknown)')
        prefix=[p(f'{i}. {label}','h3'),p(f'Severity: {(f.get("impact") or "Unknown").upper()}  |  Pages: {len(f["pages"])}  |  Known pageviews: {traffic}  |  Instances: {len(f["instances"])}','small')]
        story.append(KeepTogether(prefix))
        story.append(link(f.get('criterionUrl') or f.get('helpUrl'), 'WCAG / rule reference: ' + criteria(f)))
        story.append(p(f.get('explanation') or f['instances'][0].get('failureSummary') or f['help']))
        story += [p('Selector','h3'),p(f['selector'],'code')]
        snippet=f['instances'][0].get('html','')
        if snippet:
            story += [p('Example HTML' + (' (excerpt; full evidence in JSON)' if len(snippet)>1200 else ''),'h3'),p(snippet[:1200],'code')]
        story += [p('What needs to change','h3'),p(f.get('suggestedFix') or 'Verify source and ownership to determine the exact change for this flagged element.'),
                  p('Verification','h3'),p(f.get('verification') or 'Reproduce the finding in the recorded state, verify the user experience manually, then rerun the relevant check.')]
        affected = [names.get(value,value) for value in f['pages']]
        story += [p('Pages affected: ' + ', '.join(affected),'small'),p('Finding ID: ' + f['id'],'small'),Spacer(1,5)]
    story += [p('Coverage and limitations','h2'),p('Only recorded rendered states are covered. Hidden states, unselected pages, cross-origin frames, shadow roots, keyboard behavior and assistive-technology use require explicit verification. Unreviewed pages are not clean.','small')]
    for note in summary.get('notes',[]): story.append(p(note,'small'))
    for page in pages:
        if page.get('error'): story.append(p(names[page['url']] + ': ' + page['error'],'small'))
        for note in page.get('limitations',[]): story.append(p(names[page['url']] + ': ' + note,'small'))
    for check in summary.get('reviewChecks',[]):
        if check['status']!='issue-observed':
            story.append(p(f'{names.get(check["url"],check["url"])} — {check["title"]}: {check["status"]}. {check.get("evidence","Not tested")}', 'small'))
    if technical_appendix:
        story += [PageBreak(),p('Technical appendix','h2')]
        for page in pages:
            story.append(p(names[page['url']],'h3'))
            for key in ['state','startedAt','completedAt','inspectedAt','viewport','scanner','scanOptions']:
                if page.get(key) is not None: story.append(p(f'{key}: {page[key]}','small'))
            for scan in page.get('scans',[]): story.append(p(str(scan),'small'))
            for rule in page.get('incomplete',[]):
                story.append(link(rule.get('helpUrl'),f'Incomplete: {rule["id"]} — {len(rule.get("nodes",[]))} node records'))
    story.append(p('The evidence JSON contains full scanner metadata, individual targets, states and raw checks. This PDF has not been verified as tagged or PDF/UA conformant.','small'))

    def footer(canvas, doc):
        canvas.saveState(); canvas.setFont('Audit',6.5); canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(50,29,summary['domain'][:70]+' · '+date)
        canvas.drawRightString(562,29,'Page '+str(doc.page)); canvas.restoreState()
    doc=SimpleDocTemplate(str(output),pagesize=letter,leftMargin=50,rightMargin=50,topMargin=46,bottomMargin=48,title=title,author='Noibu')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
