"""Compact audit PDF presentation. Counting and evidence stay in the normalizers."""
from collections import Counter
from datetime import datetime
from pathlib import Path
import re
import textwrap
from urllib.parse import unquote, urlsplit
from xml.sax.saxutils import escape


TITLES = {
    'aria-required-parent': 'An ARIA role lacks its required parent structure',
    'svg-img-alt': 'An SVG image has no text alternative',
    'label-content-name-mismatch': 'Visible link text is missing from its accessible name',
    'link-name': 'A link has no accessible name',
    'link-in-text-block': 'An inline link relies on color alone',
}

CRITERION_NAMES = {
    '1.1.1': 'Non-text Content', '1.3.1': 'Info and Relationships',
    '1.4.1': 'Use of Color', '2.4.4': 'Link Purpose (In Context)',
    '2.5.3': 'Label in Name', '4.1.2': 'Name, Role, Value',
}

IMPACTS = {
    'aria-required-parent': 'The announced structure may be confusing to people navigating with assistive technology.',
    'svg-img-alt': 'People using assistive technology may not receive the image’s meaning. A named surrounding control can already convey the same purpose.',
    'label-content-name-mismatch': 'People using voice control may have difficulty activating the link by its visible wording.',
    'link-name': 'People navigating by links may not be able to identify the destination.',
    'link-in-text-block': 'People who cannot reliably distinguish colors may have difficulty recognizing the link.',
}


def finding_title(finding):
    if finding.get('title'):
        return finding['title']
    target = finding.get('selector', '')
    if finding['rule'] == 'svg-img-alt' and 'wishlist' in target.lower():
        return 'Wishlist heart icon has no text alternative'
    if finding['rule'] == 'aria-required-parent' and 'nav-item' in target:
        return 'Navigation menu items lack the required parent structure'
    if finding['rule'] == 'link-name' and 'dy-video-link' in target:
        return 'Hero video link has an empty accessible name'
    if finding['rule'] == 'label-content-name-mismatch':
        # Decode a serialized selector, then use only its recorded visible-text cue.
        readable = target.replace('\\"', '"')
        match = re.search(r'data-mobile="([^"\n]{1,80})"', readable)
        if match:
            return f'“{match.group(1)}” link omits its visible wording'
    return TITLES.get(finding['rule'], finding['help'])


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
    return '; '.join(value + (' ' + CRITERION_NAMES[value] if value in CRITERION_NAMES else '') for value in sorted(values)) or ('Best practice (not WCAG)' if 'best-practice' in finding.get('tags', []) else 'Not supplied')


def number(value):
    return f'{value:,}' if isinstance(value, (int, float)) else 'Unknown'


def create_pdf(summary, output, *, technical_appendix=False, reference_copy=False,
               disclaimer='', standard_statement=''):
    try:
        import reportlab
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Flowable, HRFlowable, Preformatted
    except ImportError as exc:
        raise ValueError('PDF not created: ReportLab is unavailable. Use the HTML companion.') from exc

    fonts = Path(reportlab.__file__).parent / 'fonts'
    for name, filename in [('Audit', 'Vera.ttf'), ('AuditBold', 'VeraBd.ttf'), ('AuditItalic', 'VeraIt.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))
    pdfmetrics.registerFontFamily('Audit', normal='Audit', bold='AuditBold', italic='AuditItalic', boldItalic='AuditBold')
    styles = {
        'body': ParagraphStyle('body', fontName='Audit', fontSize=9.2, leading=13, spaceAfter=7, allowWidows=0, allowOrphans=0),
        'small': ParagraphStyle('small', fontName='Audit', fontSize=7.7, leading=10.4, spaceAfter=5, allowWidows=0, allowOrphans=0),
        'subtitle': ParagraphStyle('subtitle', fontName='Audit', fontSize=9.4, leading=13, spaceAfter=5, textColor=colors.HexColor('#555555')),
        'disclaimer': ParagraphStyle('disclaimer', fontName='AuditItalic', fontSize=8, leading=11, spaceAfter=9),
        'title': ParagraphStyle('title', fontName='AuditBold', fontSize=21, leading=26, spaceAfter=7),
        'h2': ParagraphStyle('h2', fontName='AuditBold', fontSize=14, leading=18, spaceBefore=15, spaceAfter=8, keepWithNext=True),
        'h3': ParagraphStyle('h3', fontName='AuditBold', fontSize=10.7, leading=14, spaceBefore=15, spaceAfter=7, keepWithNext=True),
        'code': ParagraphStyle('code', fontName='Courier', fontSize=7.3, leading=10),
        'thead': ParagraphStyle('thead', fontName='AuditBold', fontSize=7.7, leading=10.4, textColor=colors.white),
    }
    def p(value, style='body'):
        # Every supplied string, including node HTML, is untrusted evidence.
        return Paragraph(escape(str(value)).replace('\n', '<br/>'), styles[style])

    def labelled(label, value, style='body'):
        return Paragraph('<b>' + escape(label) + '</b> ' + escape(str(value)).replace('\n','<br/>'), styles[style])

    def code_block(value):
        # Preformatted draws literal text, preserving indentation. Escape non-ASCII
        # glyphs for Courier coverage; the exact original remains in evidence JSON.
        lines = []
        for line in str(value).expandtabs(4).split('\n'):
            line = line.encode('ascii', 'backslashreplace').decode('ascii')
            indent = line[:len(line)-len(line.lstrip())][:16]
            lines.extend(textwrap.wrap(line, width=110, subsequent_indent=indent+'  ',
                                       replace_whitespace=False, drop_whitespace=False,
                                       break_long_words=True, break_on_hyphens=False) or [''])
        block = Table([[Preformatted('\n'.join(lines), styles['code'])]], colWidths=[512], hAlign='LEFT', splitInRow=1)
        block.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f4f4f4')),
                                   ('BOX',(0,0),(-1,-1),.4,colors.HexColor('#dedede')),
                                   ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
                                   ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        block.spaceAfter=9
        return block

    def safe_url(value):
        if not isinstance(value, str) or re.search(r'[\x00-\x20]', value): return False
        try:
            parsed = urlsplit(value)
            return parsed.scheme in {'https', 'http'} and bool(parsed.hostname) and not parsed.username and not parsed.password
        except ValueError:
            return False

    def link(value, label, style='small'):
        if not safe_url(value): return p(label, style)
        return Paragraph('<link href="' + escape(value, {'"': '&quot;'}) + '" color="#0757a6"><u>' + escape(str(label)) + '</u></link>', styles[style])

    class SeverityCards(Flowable):
        def __init__(self):
            super().__init__()
            self.width, self.height = 512, 76

        def draw(self):
            palette = [('#b72424','#fbefed'),('#995400','#fff2e3'),('#8c7000','#fff8df'),('#555555','#f2f2f2')]
            self.canv.saveState()
            for index, (severity, (ink, fill)) in enumerate(zip(('critical','serious','moderate','minor'),palette)):
                x=index*130
                self.canv.setStrokeColor(colors.HexColor(ink)); self.canv.setFillColor(colors.HexColor(fill))
                self.canv.setLineWidth(.6); self.canv.roundRect(x,0,122,76,6,stroke=1,fill=1)
                value=summary['severityCounts'].get(severity)
                self.canv.setFillColor(colors.HexColor(ink)); self.canv.setFont('AuditBold',28 if value is not None else 13)
                self.canv.drawCentredString(x+61,34,number(value))
                self.canv.setFont('Audit',9); self.canv.drawCentredString(x+61,17,severity.title())
            self.canv.restoreState()

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
    display_domain = summary['domain'].removeprefix('www.')
    title = display_domain[:1].upper() + display_domain[1:] + (' Accessibility Review' if manual else ' Accessibility Audit')
    generated = summary['generatedAt']
    try: date = datetime.fromisoformat(generated.replace('Z', '+00:00')).strftime('%B %d, %Y').replace(' 0', ' ')
    except ValueError: date = generated
    source_times = sorted(page.get('startedAt') or page.get('completedAt') or page.get('inspectedAt') for page in completed if page.get('startedAt') or page.get('completedAt') or page.get('inspectedAt'))
    evidence_dates = sorted({value[:10] for value in source_times})
    story = [p(title, 'title'), p(f'{summary["domain"]}  |  {summary["standard"]}  |  {len(completed)} of {len(pages)} pages ' + ('reviewed' if manual else 'with completed results'), 'subtitle'), p('Report date: ' + date, 'subtitle')]
    if evidence_dates:
        story.append(p('Evidence date: ' + evidence_dates[0] + (' to ' + evidence_dates[-1] if evidence_dates[-1] != evidence_dates[0] else '') + (' (imported original results)' if imported else ''), 'small'))
    story += [HRFlowable(width='100%', thickness=.5, color=colors.HexColor('#cccccc'), spaceBefore=9, spaceAfter=10),
              p(disclaimer if reference_copy else 'This report is informational, not legal advice or a compliance certification. Manual keyboard and assistive-technology testing remain necessary.', 'disclaimer'),
              p('Executive summary', 'h2')]
    if manual:
        story += [p('Browser-based accessibility review — axe not run. Automated scans completed: 0. All automated severity counts are unknown.'),
                  p(f'We reviewed {len(completed)} of {len(pages)} selected pages and recorded {len(summary["findings"])} confirmed manual observations. These are separate from automated findings.')]
    elif imported:
        story += [p(summary['importSummary']), p('These are imported completed axe results with original provenance. Repeated findings count once per scan state. Shared fixes and unique affected elements have not been verified.')]
    else:
        story.append(p(f'We checked {len(completed)} of {len(pages)} selected pages in their recorded rendered states. Together, these pages account for {known_traffic:,} known pageviews' + (' (partial traffic coverage).' if partial_traffic else '.')))
        if reference_copy:
            story.append(p(standard_statement))
        story.append(p(f'We found {summary["rawInstances"]:,} violation instances. Many repeat across pages or elements; once grouped by verified component evidence, they represent {summary["uniqueFixes"]:,} unique fixes.'))
    if len(completed) != len(pages):
        story.append(p('Coverage: ' + '; '.join(f'{key.lower()}: {value}' for key, value in counts.items()) + '.', 'small'))
    story.append(p('Automated severity counts — unknown; axe not run' if manual else 'Unpooled rule/scan records by severity' if imported else 'Unique fixes by severity', 'small'))
    story += [SeverityCards(), Spacer(1,8)]
    if summary['severityCounts'].get('needs_review'):
        story.append(p(f'{summary["severityCounts"]["needs_review"]} further finding groups have unknown severity.', 'small'))
    story.append(p('Pages reviewed' if manual else 'Pages scanned', 'h2'))
    rows = []
    for page in pages:
        label=names[page['url']]
        if page not in completed:
            label += ' (' + page['status'].lower() + ')'
        rows.append([link(page['url'],label), p(number(page.get('pageviews')),'small'), p(number(page.get('violationInstances')),'small')])
    story.append(table(['Page','Pageviews¹','Violation instances'], rows, [256,128,128]))
    story.append(p('¹ Traffic window: ' + summary.get('trafficWindow', 'Not supplied') + '. Pageviews describe exposure, not affected people.', 'small'))
    if manual:
        story.append(p('Automated counts are unknown. Manual observations are listed below.', 'small'))
    else:
        story.append(p('Needs manual review: ' + number(summary.get('incompleteCheckCount')) + ' incomplete rule records' + ('' if summary.get('incompleteCountComplete',True) else ' (partial coverage)') + '. These are not confirmed violations. Detailed counts, scan options and exact timestamps remain in the evidence JSON and optional appendix.', 'small'))
    story += [PageBreak(), p('Key manual observations' if manual else 'Key findings','h2'),
              p('Manual observations are separate from automated results.' if manual else 'Imported groups are unpooled and ordered by observed severity and instance count.' if imported else 'Ordered by priority: severity weighted by known page traffic and verified shared-component breadth.','small')]
    findings = summary['findings']
    rows=[]
    for i,f in enumerate(findings,1):
        label = finding_title(f)
        rows.append([p(i,'small'),p(label,'small'),p(criteria(f),'small'),p((f.get('impact') or 'Unknown').upper(),'small')])
    story.append(table(['#','Finding','WCAG criterion','Severity'],rows or [[p('—'),p('No confirmed findings in the supplied evidence.'),p('—'),p('—')]],[24,285,125,78]))
    for i,f in enumerate(findings,1):
        label=finding_title(f)
        traffic=number(f.get('knownPageviews')) + ('' if f.get('trafficComplete') else ' (partial/unknown)')
        severity=(f.get('impact') or 'Unknown').upper()
        ink={'CRITICAL':'#b72424','SERIOUS':'#995400','MODERATE':'#8c7000','MINOR':'#555555'}.get(severity,'#555555')
        meta=Paragraph('<b>Severity:</b> <font color="'+ink+'">'+escape(severity)+'</font>  |  <b>Pages affected:</b> '+str(len(f['pages']))+'  |  <b>Known pageviews:</b> '+escape(traffic)+'  |  <b>Instances:</b> '+str(len(f['instances'])), styles['small'])
        status='Manual observation' if manual else 'Manually verified' if f.get('evidenceStatus')=='manually-verified' else 'Imported scanner finding; manual reproduction pending' if imported else 'Scanner finding; manual reproduction pending'
        explanation=f.get('explanation') or f['instances'][0].get('failureSummary') or f['help']
        impact=f.get('userImpact') or IMPACTS.get(f['rule'])
        introduction=[p(f'{i}. {label}','h3'),meta,link(f.get('criterionUrl') or f.get('helpUrl'),criteria(f)), labelled('Evidence:',status,'small')]
        introduction[0].finding_context=f'{i}. {label}'
        selector=f['selector']
        try:
            import json
            paths=json.loads(selector)
            if isinstance(paths,list):selector=' → '.join(str(path) for path in paths)
        except (ValueError,TypeError):pass
        first_evidence=[p('Selector','h3'),code_block(selector)]
        # Reserve the heading, explanation and first selector together when the
        # introduction is short. Unusually long evidence must remain splittable.
        intro=p(explanation)
        if len(explanation)<900 and len(selector)<500:
            introduction.append(intro)
            if impact: introduction.append(labelled('Potential user impact:',impact))
            introduction.extend(first_evidence)
            story.append(KeepTogether(introduction))
        else:
            story.append(KeepTogether(introduction)); story.append(intro)
            if impact:story.append(labelled('Potential user impact:',impact))
            story.extend(first_evidence)
        if f.get('verificationEvidence'):
            story.append(labelled('Verification evidence:',f['verificationEvidence'],'small'))
        snippet=f['instances'][0].get('html','')
        if snippet:
            story += [p('Example HTML' + (' (excerpt; full evidence in JSON)' if len(snippet)>1200 else ''),'h3'), code_block(snippet[:1200])]
        tail=[labelled('What needs to change:', f.get('suggestedFix') or 'Verify source and ownership to determine the exact change for this flagged element.'),
              labelled('Verification:', f.get('verification') or 'Reproduce the finding in the recorded state, verify the user experience manually, then rerun the relevant check.')]
        affected=[]
        for value in f['pages']:
            name=escape(names.get(value,value))
            affected.append('<link href="'+escape(value,{'"':'&quot;'})+'" color="#0757a6"><u>'+name+'</u></link>' if safe_url(value) else name)
        affected_line=Paragraph('<b>Scanned pages affected:</b> '+', '.join(affected),styles['small'])
        affected_line.finding_end=True
        tail.append(affected_line)
        if sum(len(f.get(key,'')) for key in ['suggestedFix','verification'])<900 and len(affected)<20:
            story.append(KeepTogether(tail))
        else:story.extend(tail)
        story.append(Spacer(1,7))
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
        count_rows=[[link(page['url'],names[page['url']]),p(page['status'],'small'),p(number(page.get('violatedRuleCount')),'small'),p(number(page.get('affectedElementCount')),'small'),p(number(page.get('incompleteCount')),'small')] for page in pages]
        story.append(table(['Page','Status','Rules','Elements','Incomplete'],count_rows,[190,85,65,82,90]))
        if not manual:
            story.append(p(f'Distinct violated rules: {number(summary.get("violatedRuleCount"))}; affected page/target elements: {number(summary.get("affectedElementCount"))}. Instances count rule/node occurrences; pooled fixes describe verified shared components.','small'))
        for finding in findings:story.append(p(f'{finding_title(finding)} — Finding ID: {finding["id"]}','small'))
        for page in pages:
            story.append(p(names[page['url']],'h3'))
            for key in ['state','startedAt','completedAt','inspectedAt','viewport','scanner','scanOptions']:
                if page.get(key) is not None: story.append(p(f'{key}: {page[key]}','small'))
            for scan in page.get('scans',[]): story.append(p(str(scan),'small'))
            for rule in page.get('incomplete',[]):
                story.append(link(rule.get('helpUrl'),f'Incomplete: {rule["id"]} — {len(rule.get("nodes",[]))} node records'))
    story.append(p('The evidence JSON contains full scanner metadata, individual targets, states and raw checks. This PDF has not been verified as tagged or PDF/UA conformant.','small'))

    class AuditDocument(SimpleDocTemplate):
        active_finding=None

        def afterFlowable(self, flowable):
            if getattr(flowable,'finding_context',None):self.active_finding=flowable.finding_context
            if getattr(flowable,'finding_end',False):self.active_finding=None

    def footer(canvas, doc):
        canvas.saveState(); canvas.setFont('Audit',6.5); canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(50,29,summary['domain'][:70]+' · '+date)
        canvas.drawRightString(562,29,'Page '+str(doc.page))
        if doc.active_finding:
            context=doc.active_finding
            while pdfmetrics.stringWidth(context+' (continued)','Audit',7.3)>512:context=context[:-2]
            canvas.setFont('Audit',7.3);canvas.drawString(50,765,context+' (continued)')
        canvas.restoreState()
    doc=AuditDocument(str(output),pagesize=letter,leftMargin=44,rightMargin=44,topMargin=40,bottomMargin=42,title=title,author='Noibu')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
