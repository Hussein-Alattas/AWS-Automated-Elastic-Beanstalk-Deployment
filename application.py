"""Small, stateless WSGI learning app. No database or external API calls."""
from pathlib import Path
import hashlib
import json
import socket
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parent
RELEASE = json.loads((ROOT / 'release.json').read_text())
VERSION = RELEASE['version']
INSTANCE = hashlib.sha256(socket.gethostname().encode()).hexdigest()[:10]
ART = (ROOT / 'static' / 'krakow.webp').read_bytes()
THEME = '#128b8a' if RELEASE['theme'] == 'teal' else '#da874b'
HTML = ("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title></title><link rel="icon" href="data:,"><style>
*{box-sizing:border-box}body{margin:0;background:BG;font-family:system-ui}
main{max-width:1440px;margin:auto;padding:clamp(12px,3vw,36px)}
.hero{display:block;width:100%;border-radius:24px;border:6px solid rgba(255,255,255,.8);box-shadow:0 12px 36px #0003}
.gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:20px}
.gallery img{width:100%;height:240px;object-fit:cover;border:5px solid #ffffffc9;border-radius:20px;box-shadow:0 8px 24px #0002}
.gallery img:nth-child(1){object-position:0% 30%}.gallery img:nth-child(2){object-position:30% 100%}.gallery img:nth-child(3){object-position:100% 25%}
@media(max-width:650px){.gallery{grid-template-columns:1fr}.gallery img{height:220px}}
</style></head><body><main aria-label="Illustrated Krakow gallery">
<img class="hero" src="/static/krakow.webp" alt="Cartoon panorama inspired by Krakow, with a castle, river, dragon and market square">
<div class="gallery"><img src="/static/krakow.webp" alt="Castle detail" style="object-fit:none;object-position:5% 10%" loading="lazy">
<img src="/static/krakow.webp" alt="Dragon and river detail" style="object-fit:none;object-position:20% 100%" loading="lazy">
<img src="/static/krakow.webp" alt="Market square detail" style="object-fit:none;object-position:100% 15%" loading="lazy"></div>
</main></body></html>""").replace('BG', THEME).encode()

def application(environ, start_response):
    method = environ.get('REQUEST_METHOD', 'GET')
    path = environ.get('PATH_INFO', '/')
    status, kind, body = '200 OK', 'text/html; charset=utf-8', HTML
    if method not in ('GET', 'HEAD'):
        status, kind, body = '405 Method Not Allowed', 'text/plain', b'Method not allowed'
    elif path == '/health':
        healthy = RELEASE.get('health_ok', True)
        status = '200 OK' if healthy else '503 Service Unavailable'
        kind = 'application/json'
        body = json.dumps({'status': 'ok' if healthy else 'unhealthy', 'version': VERSION}).encode()
    elif path == '/version':
        kind = 'application/json'
        body = json.dumps({'version': VERSION, 'instance': INSTANCE}).encode()
    elif path == '/static/krakow.webp':
        kind, body = 'image/webp', ART
    elif path != '/':
        status, kind, body = '404 Not Found', 'text/plain', b'Not found'
    headers = [('Content-Type', kind), ('Content-Length', str(len(body))),
               ('X-App-Version', VERSION), ('X-App-Instance', INSTANCE),
               ('Cache-Control', 'public, max-age=86400' if path == '/static/krakow.webp' else 'no-store'),
               ('X-Content-Type-Options', 'nosniff'),
               ('Content-Security-Policy', "default-src 'self'; style-src 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'")]
    if status.startswith('405'):
        headers.append(('Allow', 'GET, HEAD'))
    start_response(status, headers)
    return [b'' if method == 'HEAD' else body]

if __name__ == '__main__':
    with make_server('127.0.0.1', 8000, application) as server:
        print('Local preview: http://127.0.0.1:8000')
        server.serve_forever()
