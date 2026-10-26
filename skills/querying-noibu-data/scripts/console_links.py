"""Validate console destinations or build documented routes from verified IDs.

No requests are made. Callers must establish identity/provenance from Noibu
results; syntactic validation does not prove that an object exists or is visible.
"""
import argparse
import re
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID


def domain_uuid(value):
    if not isinstance(value, str):
        raise ValueError('Expected domain UUID, not its numeric ID or hostname')
    return str(UUID(value))


def validate_url(url, domain_id=None):
    if not isinstance(url, str) or len(url) > 4096 or re.search(r'[\s\\\x00-\x1f]', url):
        raise ValueError('Invalid console URL')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'console.noibu.com' or parsed.fragment:
        raise ValueError('Expected HTTPS console.noibu.com URL without credentials or fragment')
    segments = parsed.path.split('/')
    if len(segments) < 3 or not segments[2] or '%' in parsed.path or any(part in {'.', '..'} for part in segments):
        raise ValueError('Expected domain-scoped console route')
    actual_domain = domain_uuid(segments[1])
    if domain_id is not None and actual_domain != domain_uuid(domain_id):
        raise ValueError('Console URL belongs to a different domain')
    if any(re.search(r'token|secret|password|authorization|code', key, re.I) for key, _ in parse_qsl(parsed.query)):
        raise ValueError('Do not expose credential-bearing query parameters')
    return url


def console_link(domain_id, kind, resource):
    domain_id = domain_uuid(domain_id)
    if kind == 'ab-test':
        if isinstance(resource, bool) or not re.fullmatch(r'[1-9][0-9]*', str(resource)):
            raise ValueError('AB test URL needs the actual positive numeric id, not key/rank')
        route = 'ab-tests/' + str(resource)
    elif kind == 'performance':
        if resource not in {'LCP', 'INP', 'CLS', 'FCP', 'TTFB'}:
            raise ValueError('Unsupported performance metric')
        route = 'performance/' + resource
    else:
        raise ValueError('No documented generated route for this resource')
    return validate_url('https://console.noibu.com/' + domain_id + '/' + route, domain_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--domain-id', required=True)
    parser.add_argument('--kind', choices=['ab-test', 'performance'], required=True)
    parser.add_argument('--resource', required=True)
    args = parser.parse_args()
    try:
        print(console_link(args.domain_id, args.kind, args.resource))
    except ValueError as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
