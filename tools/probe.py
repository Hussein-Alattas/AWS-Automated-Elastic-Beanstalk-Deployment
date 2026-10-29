"""Low-rate observer for YOUR lab URL, not a stress test. No third-party packages."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

p = argparse.ArgumentParser()
p.add_argument('url', help='Your own Elastic Beanstalk environment URL')
p.add_argument('--count', type=int, default=120)
a = p.parse_args()
if not 1 <= a.count <= 600:
    p.error('count must be 1 to 600; request rate is at most one per second')
if urlsplit(a.url).scheme not in ('http', 'https'):
    p.error('URL must start with http:// or https://')
counts = Counter()
for n in range(a.count):
    start = time.monotonic()
    req = Request(a.url.rstrip('/') + '/version', headers={'Cache-Control': 'no-cache', 'Connection': 'close'})
    try:
        with urlopen(req, timeout=5) as r:
            code = r.status
            version = r.headers.get('X-App-Version', '?')
            instance = r.headers.get('X-App-Instance', '?')
            r.read()
    except HTTPError as e:
        code, version, instance = e.code, '-', '-'
        e.close()
    except (URLError, TimeoutError, OSError):
        code, version, instance = 'ERROR', '-', '-'
    counts[(str(code), version, instance)] += 1
    print(datetime.now(timezone.utc).isoformat(timespec='seconds'), code, version, instance,
          str(round((time.monotonic()-start)*1000))+'ms', flush=True)
    if n + 1 < a.count:
        time.sleep(max(0, 1-(time.monotonic()-start)))
print('Summary:', dict(counts))
