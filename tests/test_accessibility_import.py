"""Synthetic evidence only: these fixtures are not storefront scan results."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/accessibility-audit/scripts/import_axe_bundle.py'
spec = importlib.util.spec_from_file_location('axe_import', SCRIPT)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


def bundle():
    rule = {'id': 'link-name', 'impact': 'serious', 'help': 'Links need names',
            'helpUrl': 'https://example.test/rules/link-name', 'tags': ['wcag2a', 'wcag244'],
            'nodes': [{'target': ['.hero-link'], 'html': '<a href="/shop"></a>', 'failureSummary': 'Missing name'}]}
    scan = {'url': 'https://example.test/', 'timestamp': '2026-10-29T14:30:00Z',
            'testEngine': {'name': 'axe-core', 'version': '4.10.2'},
            'toolOptions': {'runOnly': ['wcag2a', 'best-practice']},
            'violations': [rule], 'incomplete': [copy.deepcopy(rule)], 'passes': [], 'inapplicable': []}
    return {'page': scan['url'], 'scan_index': [
        {'label': 'closed', 'state': 'Menu closed', 'scope': 'document', 'viewport': {'width': 390, 'height': 844}},
        {'label': 'open', 'state': 'Menu open', 'scope': '#navigation', 'viewport': {'width': 390, 'height': 844}}],
        'scans': {'closed': scan, 'open': copy.deepcopy(scan)}}


class ImportTests(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'input.json'
            path.write_text(json.dumps(data))
            return importer.load_bundle(path)

    def test_states_keep_provenance_and_separate_count_units(self):
        data = self.load(bundle())
        result = importer.summarize(data)
        self.assertEqual((result['scanCount'], result['distinctPages']), (2, 1))
        self.assertEqual(result['violationNodeScanInstances'], 2)
        self.assertEqual(result['incompleteRuleScanInstances'], 2)
        self.assertEqual(result['distinctViolatedRules'], 1)
        self.assertEqual(result['scans'][1]['scope'], '#navigation')
        self.assertEqual(result['scans'][0]['timestamp'], data['scans']['closed']['timestamp'])
        self.assertEqual(result['scans'][0]['options'], data['scans']['closed']['toolOptions'])
        self.assertNotIn('October 29', importer.render(result))

    def test_missing_results_are_not_zero_findings(self):
        data = bundle(); del data['scans']['open']['incomplete']
        with self.assertRaisesRegex(ValueError, 'missing incomplete'):
            self.load(data)

    def test_rejects_ambiguous_times_and_index(self):
        for mutation in ['timestamp', 'index', 'url']:
            data = bundle()
            if mutation == 'timestamp': data['scans']['open']['timestamp'] = '2026-10-29T14:30:00'
            elif mutation == 'index': data['scan_index'][1]['label'] = 'closed'
            else: data['scans']['open']['url'] = 'https://secret@example.test/'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.load(data)

    def test_wcag_and_best_practice_remain_separate(self):
        data = bundle()
        data['scans']['open']['violations'][0].update(id='region', tags=['best-practice'])
        result = importer.summarize(self.load(data))
        self.assertEqual({r['category'] for r in result['violations']}, {'WCAG tagged', 'best-practice only'})

    def test_cli_preserves_raw_evidence_and_escapes_html(self):
        data = bundle(); data['scans']['closed']['violations'][0]['nodes'][0]['html'] = '<script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder); (path/'input.json').write_text(json.dumps(data))
            subprocess.run([sys.executable, str(SCRIPT), str(path/'input.json'), '--output-dir', str(path/'out')], check=True, capture_output=True)
            self.assertEqual(json.loads((path/'out/imported-axe-evidence.json').read_text()), data)
            report = (path/'out/imported-axe-report.html').read_text()
            self.assertNotIn('<script>alert(1)</script>', report)
            self.assertIn('&lt;script&gt;', report)


if __name__ == '__main__':
    unittest.main()
