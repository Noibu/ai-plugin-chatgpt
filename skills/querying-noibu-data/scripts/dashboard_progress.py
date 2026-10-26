"""Derive truthful dashboard readiness from observed evidence; no network or writes."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

FLAGS = ('dependenciesReady', 'sourceReady', 'buildPassed', 'hostedInitialReadPassed', 'hostedRefreshPassed', 'persistenceReady', 'totalsVerified', 'persistenceReadbackPassed')
ALLOWED = {'mode', 'eligibility', 'projectId', *FLAGS, 'savedVersionId', 'deploymentStatus', 'liveUrl', 'failure'}
DEPLOYMENT = {'not-started', 'pending', 'building', 'publishing', 'succeeded', 'failed'}

def assess(value):
    if not isinstance(value, dict) or set(value) - ALLOWED:
        raise ValueError('Unsupported progress fields')
    mode = value.get('mode', 'persistent-snapshot')
    if mode not in {'persistent-snapshot', 'visitor-connected'}:
        raise ValueError('Unsupported dashboard data mode')
    if value.get('eligibility') not in {'allowed', 'denied', 'unknown'}:
        raise ValueError('Record the observed Sites eligibility')
    if any(k in value and type(value[k]) is not bool for k in FLAGS):
        raise ValueError('Verification flags must be booleans')
    for key in ('projectId', 'savedVersionId'):
        if value.get(key) is not None and (not isinstance(value[key], str) or not value[key].strip()):
            raise ValueError('Keep actual opaque IDs or null')
    deployment = value.get('deploymentStatus', 'not-started')
    if deployment not in DEPLOYMENT:
        raise ValueError('Unsupported deployment status')
    url = value.get('liveUrl')
    if url is not None:
        parsed = urlparse(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Use a credential-free returned HTTPS live URL')
    verified_url = url if deployment == 'succeeded' and value.get('projectId') and value.get('savedVersionId') else None
    result = {'ready': False, 'state': 'continue', 'next': None, 'liveUrl': verified_url}
    if value['eligibility'] != 'allowed':
        return {**result, 'state': 'blocked', 'next': 'resolve-sites-eligibility'}
    failure = value.get('failure')
    if failure is not None:
        if not isinstance(failure, dict) or set(failure) != {'step', 'message', 'needsUser'} or type(failure['needsUser']) is not bool or not all(isinstance(failure[k], str) and failure[k].strip() for k in ('step', 'message')):
            raise ValueError('Failure needs exact step, message and needsUser boolean')
        return {**result, 'state': 'blocked' if failure['needsUser'] else 'repair-required', 'next': failure['step'], 'failure': failure}
    source_step = 'implement-persistent-source' if mode == 'persistent-snapshot' else 'implement-connected-source'
    for passed, step in ((bool(value.get('projectId')), 'register-or-recover-site'), (value.get('dependenciesReady'), 'complete-dependency-setup'), (value.get('sourceReady'), source_step), (value.get('buildPassed'), 'check-and-build'), (bool(value.get('savedVersionId')), 'save-exact-version')):
        if not passed:
            return {**result, 'next': step}
    if deployment in {'pending', 'building', 'publishing'}:
        return {**result, 'state': 'deployment-running', 'next': 'check-existing-deployment'}
    if deployment == 'failed':
        return {**result, 'state': 'repair-required', 'next': 'inspect-deployment-error'}
    if deployment != 'succeeded':
        return {**result, 'next': 'deploy-saved-version-privately'}
    if not url:
        return {**result, 'state': 'verification-pending', 'next': 'resolve-returned-live-url'}
    result['liveUrl'] = url
    if mode == 'persistent-snapshot':
        for flag, step in [('totalsVerified', 'verify-report-totals'), ('persistenceReady', 'persist-verified-snapshot'), ('persistenceReadbackPassed', 'verify-independent-persistence-readback'), ('hostedInitialReadPassed', 'verify-hosted-snapshot-read')]:
            if not value.get(flag):
                return {**result, 'state': 'deployed-unverified', 'next': step}
        return {**result, 'ready': True, 'state': 'persistent-verified', 'next': None}
    if not value.get('hostedInitialReadPassed') or not value.get('hostedRefreshPassed'):
        return {**result, 'state': 'deployed-unverified', 'next': 'verify-visitor-read-and-refresh'}
    return {**result, 'ready': True, 'state': 'connected-verified', 'next': None}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('progress', type=Path, help='Task-local JSON containing observed tool results, not credentials')
    args = parser.parse_args()
    try:
        print(json.dumps(assess(json.loads(args.progress.read_text())), indent=2))
    except (ValueError, TypeError) as error:
        parser.exit(1, f'Invalid progress evidence: {error}\n')

if __name__ == '__main__':
    main()
