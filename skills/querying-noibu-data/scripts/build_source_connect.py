"""Build the inline source-connect card shown when Get fix has no verified source. No network or writes."""
import argparse
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('noibu_presentation', Path(__file__).with_name('build_presentation.py'))
board = importlib.util.module_from_spec(spec)
spec.loader.exec_module(board)
require, text, escape, safe_json = board.require, board.text, board.escape, board.safe_json

FIELDS = {'schema', 'action', 'finding', 'diagnosis', 'platform', 'shopifyTheme', 'codeHostNote', 'prefill', 'repositories', 'mode'}
MODES = {'connect', 'choose', 'enter'}
PROVIDERS = {'GitHub', 'Bitbucket', 'GitLab', 'Azure DevOps', 'Other'}
REPO = re.compile(r'[A-Za-z0-9._-]+(/[A-Za-z0-9._-]+){1,4}')
BRANCH = re.compile(r'(?!/)(?!.*\.\.)(?!.*//)[A-Za-z0-9._/-]{1,100}')
PLATFORMS = {'shopify', 'bigcommerce', 'magento', 'woocommerce', 'salesforce-commerce', 'custom', 'unknown'}

def validate(data):
    require(isinstance(data, dict) and set(data) <= FIELDS, 'Unsupported source-connect fields')
    require(data.get('schema') == 'noibu.source-connect/1', 'Unsupported source-connect schema')
    base = data.get('action')
    require(isinstance(base, dict) and set(base) <= {'workflow', 'reportId', 'domain', 'window', 'generatedAt'}, 'Action needs the original report identity')
    # Reuse the board's identity checks so the card's actions match the original report.
    board.validate({'schema': 'noibu.presentation/1', 'summary': 'source connect', **base})
    finding = data.get('finding')
    require(isinstance(finding, dict) and set(finding) == {'id', 'title'} and text(finding['id'], 100) and text(finding['title'], 300), 'Finding needs id and title')
    diagnosis = data.get('diagnosis')
    require(isinstance(diagnosis, dict) and set(diagnosis) == {'happening', 'pointsTo', 'hypothesis'} and all(text(diagnosis[k], 600) for k in diagnosis), 'Diagnosis needs happening, pointsTo and hypothesis')
    require(data.get('platform') in PLATFORMS, 'Platform must be the resolved Noibu platform or unknown')
    if 'shopifyTheme' in data:
        # Shown only when Noibu says the store is on Shopify; never a generic option.
        require(data['platform'] == 'shopify', 'Shopify theme option requires a Shopify store')
        theme = data['shopifyTheme']
        require(isinstance(theme, dict) and set(theme) <= {'reason'} and ('reason' not in theme or text(theme['reason'], 300)), 'Invalid Shopify theme status')
    require('codeHostNote' not in data or text(data['codeHostNote'], 300), 'Invalid code host note')
    # connect: no code host yet, no form. choose: connected, several candidates. enter: connected, nothing found.
    mode = data.get('mode', 'connect')
    require(mode in MODES, 'Mode must be connect, choose or enter')
    require((mode == 'choose') == bool(data.get('repositories')), 'Repositories go with choose mode only, and choose mode needs them')
    require('prefill' not in data or mode == 'enter', 'Prefill is only for enter mode')
    require(mode != 'enter' or text(data.get('codeHostNote'), 300), 'Enter mode needs a codeHostNote saying what was searched')
    prefill = data.get('prefill', {})
    require(isinstance(prefill, dict) and set(prefill) <= {'repository', 'branch'} and all(text(v, 200) for v in prefill.values()), 'Invalid prefill')
    repos = data.get('repositories', [])
    # Only repositories the connected code host actually returned; never guessed names.
    require(isinstance(repos, list) and len(repos) <= 30, 'Up to 30 repositories')
    seen = set()
    for repo in repos:
        require(isinstance(repo, dict) and {'name', 'provider'} <= set(repo) <= {'name', 'provider', 'defaultBranch', 'likely'}, 'Repository needs name and provider')
        require(isinstance(repo['name'], str) and REPO.fullmatch(repo['name']) and repo['name'] not in seen, 'Invalid or duplicate repository name')
        seen.add(repo['name'])
        require(repo['provider'] in PROVIDERS, 'Unknown code host')
        require('defaultBranch' not in repo or isinstance(repo['defaultBranch'], str) and BRANCH.fullmatch(repo['defaultBranch']), 'Invalid default branch')
        require(type(repo.get('likely', False)) is bool, 'likely must be true or false')
    safe_json(data)
    return data

def render(data):
    validate(data)
    base, finding = data['action'], data['finding']
    common = {'schema': 'noibu.presentation-action/1', 'workflow': base['workflow'], 'reportId': base['reportId'], 'domain': base['domain'], 'window': base['window'], 'generatedAt': base['generatedAt'], 'target': {'findingId': finding['id']}}
    model = {
        'getFix': {**common, 'kind': 'get-fix', 'execution': {'route': 'source-access', 'sources': ['shopify-theme-via-noibu', 'code-host-connector'], 'connection': 'verify-before-fix-or-prompt', 'repository': 'resolve-or-ask', 'withoutSource': 'diagnosis-hint-and-connect-step', 'mode': 'read-only'}},
        'ticket': {**common, 'kind': 'create-ticket', 'execution': {'route': 'ticket-destination-first', 'chooser': 'native-question-or-text', 'question': 'Where should the ticket go?', 'options': ['Linear', 'Jira', 'GitHub Issues', 'Notion'], 'connection': 'discover-after-selection', 'completion': 'verified-ticket-or-explicit-draft-or-specific-blocker'}},
    }
    root = 'noibu-src-' + re.sub(r'[^a-z0-9-]', '-', (base['reportId'] + '-' + finding['id']).lower())[:120]
    shopify = ''
    if 'shopifyTheme' in data:
        reason = data['shopifyTheme'].get('reason')
        note = '<p class="noibu-secondary">' + escape(reason) + '</p>' if reason else ''
        label = 'Check theme access again' if reason else 'Check theme access'
        shopify = ('<div class="noibu-sc-option"><h4>Shopify theme through Noibu</h4><p>Noibu can read your live theme directly, so no code host is needed.</p>'
                   + note + f'<div class="viz-row"><button type="button" class="btn" data-noibu-theme>{label}</button></div></div>')
    prefill = data.get('prefill', {})
    repos = sorted(data.get('repositories', []), key=lambda r: not r.get('likely', False))
    model['repositories'] = [{k: r[k] for k in ('name', 'provider', 'defaultBranch') if k in r} for r in repos]
    mode = data.get('mode', 'connect')
    branch_field = f'<label class="form-label">Branch<input name="branch" class="form-control" maxlength="100" placeholder="default branch" value="{escape(prefill.get("branch", ""))}"></label>'
    submit = '<div class="viz-row"><button type="submit" class="btn btn-primary">Get fix</button></div>'
    if mode == 'connect':
        body = ('<ol><li>Connect GitHub, Bitbucket or another code host in ChatGPT.'
                '<div class="viz-row noibu-sc-link"><a class="btn" href="https://chatgpt.com/plugins" target="_blank" rel="noopener noreferrer">Open Plugins ↗</a>'
                '<span class="noibu-secondary">or ChatGPT → Plugins → search for your code host</span></div></li>'
                '<li>Come back and click Get fix. ChatGPT finds the repository with this code and checks it before writing anything.</li></ol>'
                '<div class="viz-row"><button type="button" class="btn btn-primary" data-noibu-discover>Get fix</button></div>')
    elif mode == 'choose':
        options = ''.join(f'<option value="{i}">{escape(r["name"])} · {escape(r["provider"])}{" · likely match" if r.get("likely") else ""}</option>' for i, r in enumerate(repos))
        body = ('<p>Pick the repository for this store. ChatGPT checks it contains the code from the evidence before writing a fix.</p>'
                '<form data-noibu-source novalidate><div class="noibu-sc-grid">'
                f'<label class="form-label noibu-sc-wide">Repository<select name="repoChoice" class="form-select">{options}<option value="other">Other repository…</option></select></label>'
                '<label class="form-label noibu-sc-wide" data-repository-field hidden>Other repository<input name="repository" class="form-control" maxlength="200" placeholder="owner/repo or URL"></label>'
                + branch_field + '</div>' + submit + '</form>')
    else:
        body = ('<p>Enter the repository that holds this store\'s code.</p>'
                '<form data-noibu-source novalidate><div class="noibu-sc-grid">'
                '<label class="form-label">Code host<select name="provider" class="form-select"><option value="">Auto-detect</option><option value="GitHub">GitHub</option><option value="Bitbucket">Bitbucket</option><option value="GitLab">GitLab</option><option value="Azure DevOps">Azure DevOps</option><option value="Other">Other</option></select></label>'
                f'<label class="form-label">Repository<input name="repository" class="form-control" maxlength="200" placeholder="owner/repo or URL" value="{escape(prefill.get("repository", ""))}" required></label>'
                + branch_field + '</div>' + submit + '</form>')
    values = {
        'ROOT': root,
        'STYLE': (HERE / 'assets/presentation/report.css').read_text().replace('{{ROOT}}', root),
        'DOMAIN': escape(base['domain']['name']),
        'TITLE': escape(finding['title']),
        'HAPPENING': escape(data['diagnosis']['happening']),
        'POINTSTO': escape(data['diagnosis']['pointsTo']),
        'HYPOTHESIS': escape(data['diagnosis']['hypothesis']),
        'SHOPIFY': shopify,
        'CODEHOSTHEADING': {'connect': 'Or connect your code host' if shopify else 'Connect your code host', 'choose': 'Choose the repository', 'enter': 'Enter the repository'}[mode],
        'CODEHOSTBODY': body,
        'INTRO': "A specific fix needs to read your site's code. Connect it once and Get fix will point to the exact lines and write the change for you to review." if mode == 'connect' else "Your code host is connected. Once we know which repository holds this store's code, Get fix will point to the exact lines and write the change for you to review.",
        'CODEHOSTNOTE': '<p class="noibu-secondary">' + escape(data['codeHostNote']) + '</p>' if data.get('codeHostNote') else '',
        'TICKET': '<button type="button" class="btn" data-noibu-ticket>Open a Ticket</button>',
        'MODEL': safe_json(model),
        'CONTROLLER': (HERE / 'assets/presentation/source-connect.js').read_text(),
    }
    template = (HERE / 'assets/presentation/source-connect.html').read_text()
    fragment = re.sub(r'\{\{([A-Z]+)\}\}', lambda match: values[match.group(1)], template)
    require(len(fragment.encode()) < 1000000, 'Card exceeds inline size limit')
    return fragment

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        output = render(json.loads(args.input.read_text()))
    except (ValueError, TypeError, KeyError) as error:
        parser.exit(1, f'Invalid source-connect card: {error}\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output)
    print(f'Created source-connect card: {args.output}; no external action executed')

if __name__ == '__main__':
    main()
