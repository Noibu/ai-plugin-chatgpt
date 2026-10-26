"""Validate the ChatGPT A/B handoff without network calls or Noibu mutations."""
import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from uuid import UUID

PRIMARY = {'ADD_TO_CART_RATE', 'CHECKOUT_CONVERSION_RATE', 'PAGE_VIEW_TO_URL_RATE'}
GUARDRAILS = PRIMARY | {'AVERAGE_ORDER_VALUE'}
CREATE_FIELDS = {'title', 'hypothesis', 'successMetric', 'secondaryMetrics', 'deviceTypes', 'utmConditions', 'variations'}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def text(value):
    return isinstance(value, str) and bool(value.strip())

def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def timestamp(value):
    require(text(value), 'Timestamp must be a nonempty string')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(result.tzinfo is not None, 'Timestamp must include a timezone')
    return result

def metric(value, allowed):
    require(isinstance(value, dict), 'Metric must be an object')
    require(set(value) <= {'metric', 'pageUrl', 'pageGroup'}, 'Unsupported metric field')
    require(value.get('metric') in allowed, 'Unsupported metric')
    url, group = value.get('pageUrl'), value.get('pageGroup')
    if value['metric'] == 'PAGE_VIEW_TO_URL_RATE':
        require(('pageUrl' in value) != ('pageGroup' in value), 'Page-view metric needs exactly one pageUrl/pageGroup field')
        require(text(url) != text(group), 'Page-view metric needs a nonempty pageUrl/pageGroup')
        if url is not None:
            require(text(url) and (url.startswith('/') or url.startswith(('https://', 'http://'))), 'Invalid metric page URL')
    else:
        require(url is None and group is None, 'Only a page-view metric accepts page scope')

def validate_create(value):
    require(isinstance(value, dict), 'createInput must be an object')
    require(set(value) <= CREATE_FIELDS, 'Unsupported createInput field; lifecycle and opaque targeting are excluded')
    require(text(value.get('title')), 'Missing title')
    if 'hypothesis' in value:
        require(text(value['hypothesis']), 'Hypothesis must be nonempty')
    metric(value.get('successMetric'), PRIMARY)
    secondary = value.get('secondaryMetrics', [])
    require(isinstance(secondary, list) and len(secondary) <= 3, 'At most three guardrails')
    for item in secondary:
        metric(item, GUARDRAILS)
    variations = value.get('variations')
    require(isinstance(variations, list) and len(variations) >= 2, 'At least two variations required')
    names, splits, controls = [], [], 0
    for item in variations:
        require(isinstance(item, dict) and set(item) == {'name', 'isControl', 'trafficSplit'}, 'Invalid variation fields')
        require(text(item['name']), 'Missing variation name')
        require(type(item['isControl']) is bool, 'isControl must be boolean')
        require(finite(item['trafficSplit']) and 0 <= item['trafficSplit'] <= 100, 'Invalid traffic split')
        names.append(item['name'].strip())
        splits.append(item['trafficSplit'])
        controls += int(item['isControl'])
    require(len(set(names)) == len(names), 'Variation names must be unique')
    require(controls == 1, 'Exactly one control required')
    require(math.isclose(sum(splits), 100, abs_tol=1e-9), 'Traffic splits must total 100')
    if 'deviceTypes' in value:
        devices = value['deviceTypes']
        require(isinstance(devices, list) and devices and all(x in {'mobile', 'other'} for x in devices), 'Invalid device targeting')
        require(len(set(devices)) == len(devices), 'Duplicate device targeting')
    if 'utmConditions' in value:
        conditions = value['utmConditions']
        require(isinstance(conditions, list), 'UTM conditions must be a list')
        params = []
        for condition in conditions:
            require(isinstance(condition, dict) and set(condition) == {'parameter', 'values'}, 'Invalid UTM condition')
            require(condition['parameter'] in {'utm_campaign', 'utm_medium', 'utm_source', 'utm_term', 'utm_content'}, 'Invalid UTM parameter')
            require(isinstance(condition['values'], list) and condition['values'] and all(text(x) for x in condition['values']), 'Invalid UTM values')
            params.append(condition['parameter'])
        require(len(set(params)) == len(params), 'Combine duplicate UTM parameters into one condition')
    return value

def no_nonfinite(value):
    if isinstance(value, float):
        require(math.isfinite(value), 'Nonfinite evidence number')
    if isinstance(value, dict):
        for item in value.values():
            no_nonfinite(item)
    if isinstance(value, list):
        for item in value:
            no_nonfinite(item)

def validate_candidates(value):
    require(isinstance(value, dict) and value.get('schema') == 'noibu.ab-candidates/2', 'Unsupported handoff schema')
    require(set(value) <= {'schema', 'generatedAt', 'domain', 'domainId', 'goal', 'window', 'tests', 'caveats'}, 'Unsupported root fields')
    UUID(value.get('domainId', ''))
    require(text(value.get('domain')) and text(value.get('goal')), 'Missing domain/goal')
    timestamp(value.get('generatedAt'))
    window = value.get('window', {})
    require(isinstance(window, dict) and timestamp(window.get('start')) < timestamp(window.get('end')), 'Invalid analysis window')
    tests = value.get('tests')
    require(isinstance(tests, list), 'tests must be a list')
    require(isinstance(value.get('caveats', []), list), 'caveats must be a list')
    ranks, titles = [], []
    for test in tests:
        require(isinstance(test, dict), 'Invalid candidate')
        require(type(test.get('rank')) is int and test['rank'] > 0, 'Invalid rank')
        require(text(test.get('hypothesis')) and text(test.get('what')), 'Missing hypothesis/change')
        payload = validate_create(test.get('createInput'))
        require(test.get('title') == payload['title'], 'Candidate/create title mismatch')
        require(test['hypothesis'] == payload.get('hypothesis'), 'Candidate/create hypothesis mismatch')
        validation = test.get('validation', {})
        require(isinstance(validation, dict) and validation.get('status') in {'verified', 'partial', 'unvalidated'}, 'Missing validation status')
        if validation['status'] == 'unvalidated':
            require(not test.get('selectors'), 'Unvalidated candidates cannot claim verified selectors')
        evidence = test.get('evidence')
        require(isinstance(evidence, list) and evidence, 'Candidate needs evidence')
        for item in evidence:
            require(isinstance(item, dict) and text(item.get('claim')) and text(item.get('source')) and isinstance(item.get('numbers'), dict) and item['numbers'], 'Invalid evidence')
        ranks.append(test['rank'])
        titles.append(test['title'])
    require(len(set(ranks)) == len(ranks) and len(set(titles)) == len(titles), 'Duplicate rank/title')
    no_nonfinite(value)
    return value

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    try:
        data = validate_candidates(json.loads(args.input.read_text()))
    except (ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f'Invalid handoff: {exc}\n')
    print(f"Validated {len(data['tests'])} candidates; no Noibu objects were created.")

if __name__ == '__main__':
    main()
