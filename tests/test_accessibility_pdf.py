"""PDF regression coverage using fictional storefront evidence only."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/accessibility-audit/scripts/build_deliverables.py'
spec = importlib.util.spec_from_file_location('deliverables', SCRIPT)
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
pdf = builder.module('pdf_report', SCRIPT.parent/'pdf_report.py')
try:
    from pypdf import PdfReader
    import reportlab
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


def example():
    paths = ['/womens/bracelets.html','/','/search','/womens/rings.html','/mens/bracelets.html',
             '/womens/necklaces.html','/women.html','/womens/earrings.html','/mens/necklaces-and-chains.html','/mens/rings.html']
    pages = []
    for index,path in enumerate(paths):
        rules = []
        if index not in [1,2,6]:
            rules.append({'id':'svg-img-alt','help':'Image icons need text alternatives','impact':'serious',
                          'helpUrl':'https://example.test/rules/svg-img-alt','tags':['wcag2a','wcag111'],
                          'nodes':[{'target':[f'.product:nth-child({n}) svg'], 'groupingKey':'verified-product-heart',
                                    'html':'<svg role="img"></svg>', 'failureSummary':'Image has no text alternative.'} for n in range(1,3)]})
        if index in [1,6]:
            rules.append({'id':'link-name','help':'Links need names','impact':'serious',
                          'helpUrl':'https://example.test/rules/link-name','tags':['wcag244','wcag412'],
                          'nodes':[{'target':['.hero-link'],'html':'<a href="/gifts"></a>','failureSummary':'Focusable link has no accessible name.'}]})
        if index==3:
            rules.append({'id':'link-in-text-block','help':'Distinguish links from surrounding text','impact':'serious',
                          'helpUrl':'https://example.test/rules/link-in-text-block','tags':['wcag141'],
                          'nodes':[{'target':['.intro a'],'html':'<a href="/rings">Shop rings</a>','failureSummary':'Link relies on color alone.'}]})
        pages.append({'url':'https://example.test'+path,'status':'COMPLETED','pageviews':10000-index*300,
                      'startedAt':'2026-11-01T12:00:00Z','completedAt':'2026-11-01T12:01:00Z',
                      'scanner':{'name':'axe-core','version':'4.14.0'},'scanOptions':{'runOnly':{'type':'tag','values':['wcag2a','wcag2aa','wcag21a','wcag21aa']}},
                      'state':'Synthetic default state; not a real scan','viewport':{'width':1280,'height':800},
                      'violations':rules,'incomplete':[{'id':'color-contrast','helpUrl':'https://example.test/rules/color-contrast','nodes':[{'html':'DO_NOT_DUMP_RAW_INCOMPLETE_NODES','target':['.hero']}]}]})
    return {'domain':'example.test','standard':'WCAG 2.1 AA','trafficWindow':'November 1–November 2, 2026 (synthetic)',
            'notes':['Fictional data for layout testing. No live storefront was scanned.'],'pages':pages}


@unittest.skipUnless(PDF_AVAILABLE, 'ReportLab and pypdf required for PDF regression checks')
class PdfTests(unittest.TestCase):
    def render(self, summary, appendix=False):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'report.pdf'; before=copy.deepcopy(summary)
            builder.create_pdf(summary,path,appendix)
            self.assertEqual(before,summary,'Presentation must not mutate evidence or totals')
            reader=PdfReader(path)
            return '\n'.join(page.extract_text() for page in reader.pages),len(reader.pages),[
                str(ref.get_object().get('/A',{}).get('/URI','')) for page in reader.pages for ref in page.get('/Annots',[])]

    def test_compact_example_keeps_totals_and_reference_copy(self):
        summary=builder.normalize(example()); text,pages,links=self.render(summary)
        self.assertEqual(summary['uniqueFixes'],3)
        self.assertIn('17 violation instances',text)
        self.assertIn(builder.axe.CLAUDE_DISCLAIMER,text.replace('\n',' '))
        self.assertIn(builder.axe.CLAUDE_STANDARD_STATEMENT,text.replace('\n',' '))
        self.assertIn('Homepage',text); self.assertIn("Women's Bracelets",text)
        self.assertIn('1.1.1',text); self.assertNotIn('DO_NOT_DUMP_RAW_INCOMPLETE_NODES',text)
        self.assertLessEqual(pages,4)
        self.assertIn('https://example.test/',links)

    def test_partial_and_unknown_counts_stay_visible(self):
        data=example(); data['pages'][0]['pageviews']=None
        data['pages'][2]={'url':'https://example.test/search','status':'FAILED','pageviews':None,'error':'Execution blocked'}
        summary=builder.normalize(data); text,_,_=self.render(summary)
        self.assertIn('9 of 10',text); self.assertIn('partial traffic',text)
        self.assertIn('Execution blocked',text); self.assertIn('Unknown',text)

    def test_zero_findings_and_long_snippets_paginate(self):
        data=example()
        for page in data['pages']:page['violations']=[]
        text,_,_=self.render(builder.normalize(data)); self.assertIn('No confirmed findings',text)
        data=example();data['pages'][1]['violations'][0]['nodes'][0]['html']='<a>'+('very-long-unbroken-selector-'*2000)+'</a>'
        text,_,_=self.render(builder.normalize(data)); self.assertIn('excerpt; full evidence in JSON',text)

    def test_limited_review_never_inherits_automated_counts(self):
        data={'schema':'noibu.accessibility-review/1','domain':'example.test','automationBlocker':'Page execution unavailable',
              'pages':[{'url':'https://example.test/','status':'REVIEWED','pageviews':None,'inspectedAt':'2026-11-01T12:00:00Z',
                        'checks':[{'id':'keyboard','title':'Keyboard behavior','status':'not-tested'}]}]}
        text,_,_=self.render(builder.normalize(data))
        self.assertIn('axe not run',text);self.assertIn('Automated scans completed: 0',text)
        self.assertIn('All automated severity counts are unknown',' '.join(text.split()))
        self.assertNotIn(builder.axe.CLAUDE_STANDARD_STATEMENT,text)

    def test_optional_appendix_adds_metadata_without_raw_node_dump(self):
        text,_,_=self.render(builder.normalize(example()),True)
        self.assertIn('Technical appendix',text);self.assertIn('4.14.0',text)
        self.assertNotIn('DO_NOT_DUMP_RAW_INCOMPLETE_NODES',text)

    def test_untrusted_markup_and_unsafe_links_are_not_executed(self):
        summary=builder.normalize(example())
        summary['findings'][0]['explanation']='<b>untrusted literal text</b>'
        summary['findings'][0]['helpUrl']='javascript:alert(1)'
        text,_,links=self.render(summary)
        self.assertIn('<b>untrusted literal text</b>',text)
        self.assertFalse(any(link.startswith('javascript:') for link in links))

    def test_imported_states_keep_original_counting_or_report_prerequisite(self):
        rule=example()['pages'][1]['violations'][0]
        scan={'url':'https://example.test/','timestamp':'2026-10-29T12:00:00Z',
              'testEngine':{'name':'axe-core','version':'4.10.2'},'toolOptions':{'runOnly':['wcag2a']},
              'violations':[rule],'incomplete':[],'passes':[],'inapplicable':[]}
        data={'page':scan['url'],'scan_index':[{'label':'closed','state':'Menu closed'},{'label':'open','state':'Menu open'}],
              'scans':{'closed':scan,'open':copy.deepcopy(scan)}}
        if not (SCRIPT.parent/'import_axe_bundle.py').exists():
            with self.assertRaisesRegex(ValueError,'require the accessibility recovery/import update'):
                builder.normalize(data)
            return
        summary=builder.normalize(data)
        self.assertEqual(len(summary['pages']),1)
        self.assertEqual(summary['rawInstances'],2)
        self.assertIsNone(summary['uniqueFixes'])
        self.assertEqual(summary['severityCounts']['serious'],2)
        text,_,_=self.render(summary)
        self.assertIn('2 completed scan states across 1 distinct page',text)
        self.assertIn('unpooled rule/scan records',text)
        self.assertIn('2026-10-29T12:00:00Z',text)
        self.assertNotIn(builder.axe.CLAUDE_STANDARD_STATEMENT,text)


if __name__=='__main__':unittest.main()
