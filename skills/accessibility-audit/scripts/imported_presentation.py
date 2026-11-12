"""Present validated multi-state imports without claiming verified pooled fixes."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from urllib.parse import urlsplit


def normalize(data, importer):
    source = importer.summarize(data)
    pages, findings = {}, {}
    severity = Counter()
    for indexed in data['scan_index']:
        scan = data['scans'][indexed['label']]
        page = pages.setdefault(scan['url'], {
            'url': scan['url'], 'status': 'COMPLETED', 'pageviews': None,
            'violationInstances': 0, 'affectedElementCount': None,
            'incompleteCount': 0, 'incomplete': [], 'scans': [],
        })
        page['scans'].append({'label': indexed['label'], 'timestamp': scan['timestamp'],
                              'state': indexed.get('state'), 'scope': indexed.get('scope'),
                              'viewport': indexed.get('viewport'), 'engine': scan['testEngine'],
                              'options': scan['toolOptions']})
        times = [item['timestamp'] for item in page['scans']]
        time_key = lambda value: datetime.fromisoformat(value.replace('Z','+00:00'))
        page['startedAt'] = min(times, key=time_key)
        page['completedAt'] = max(times, key=time_key)
        page['violationInstances'] += sum(len(rule['nodes']) for rule in scan['violations'])
        page['incompleteCount'] += len(scan['incomplete'])
        page['incomplete'].extend(scan['incomplete'])
        for rule in scan['violations']:
            severity[rule.get('impact') or 'needs_review'] += 1
            for node in rule['nodes']:
                identity = json.dumps([scan['url'], rule['id'], node['target']], sort_keys=True)
                finding = findings.setdefault(identity, {
                    'id': 'import-' + hashlib.sha256(identity.encode()).hexdigest()[:16],
                    'rule': rule['id'], 'help': rule.get('help',rule['id']),
                    'helpUrl': rule.get('helpUrl'), 'tags': rule.get('tags',[]),
                    'impact': rule.get('impact'), 'selector': json.dumps(node['target']),
                    'pages': {scan['url']: None}, 'knownPageviews': None,
                    'trafficComplete': False, 'instances': [],
                })
                finding['instances'].append({'url': scan['url'], 'scan': indexed['label'],
                                             'target': node['target'], 'html': node.get('html',''),
                                             'failureSummary': node.get('failureSummary','')})
                weights={'critical':5,'serious':3,'moderate':1.5,'minor':.5}
                if weights.get(rule.get('impact'),0)>weights.get(finding['impact'],0):
                    finding['impact']=rule['impact']
    for page in pages.values():
        page['violatedRuleCount'] = len({rule['id'] for scan in data['scans'].values() if scan['url']==page['url'] for rule in scan['violations']})
    weights={'critical':5,'serious':3,'moderate':1.5,'minor':.5}
    ordered=sorted(findings.values(),key=lambda f:(weights.get(f['impact'],0),len(f['instances'])),reverse=True)
    return {
        'mode':'axe-import', 'domain':urlsplit(data['page']).hostname,
        'generatedAt':datetime.now(timezone.utc).isoformat(),
        'standard':'Imported axe checks — original options retained; WCAG and other rules may differ',
        'trafficWindow':'Not supplied with imported results', 'pages':list(pages.values()),
        'severityCounts':{key:severity[key] for key in ['critical','serious','moderate','minor','needs_review']},
        'severityCountBasis':'unpooled-rule-scan-records', 'findings':ordered,
        'rawInstances':source['violationNodeScanInstances'], 'uniqueFixes':None,
        'affectedElementCount':None, 'violatedRuleCount':source['distinctViolatedRules'],
        'incompleteCheckCount':source['incompleteRuleScanInstances'], 'incompleteCountComplete':True,
        'importSummary':f'{source["scanCount"]} completed scan states across {len(pages)} distinct page(s); {source["distinctViolatedRules"]} distinct violated rules; {source["violationNodeScanInstances"]} node/scan instances and {source["incompleteRuleScanInstances"]} incomplete rule/scan records.',
        'importedSummary':source,
        'notes':['Imported evidence is not a fresh browser scan. Findings are listed by original rule and page/target; repeated states are retained. No shared-component pooling or affected-traffic estimate was performed. WCAG-tagged, best-practice and unclassified rules retain their original tags. Manual notes are retained separately in the evidence and are not automated findings.'] + data.get('notes',[]),
    }
