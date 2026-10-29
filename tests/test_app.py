import json
import unittest
from application import application

def request(path='/', method='GET'):
    result = {}
    def start(status, headers):
        result['status'] = status
        result['headers'] = dict(headers)
    result['body'] = b''.join(application({'PATH_INFO': path, 'REQUEST_METHOD': method}, start))
    return result

class AppTests(unittest.TestCase):
    def test_home(self):
        r = request()
        self.assertEqual(r['status'], '200 OK')
        self.assertIn(b'<img', r['body'])
        self.assertNotIn(b'<h1', r['body'])
    def test_health(self):
        r = request('/health')
        self.assertEqual(r['status'], '200 OK')
        self.assertEqual(json.loads(r['body'])['status'], 'ok')
    def test_version(self):
        r = request('/version')
        self.assertIn(json.loads(r['body'])['version'], ('v1', 'v2'))
        self.assertIn('X-App-Instance', r['headers'])
    def test_art(self):
        r = request('/static/krakow.webp')
        self.assertEqual(r['headers']['Content-Type'], 'image/webp')
        self.assertEqual(r['body'][:4], b'RIFF')
    def test_missing(self):
        self.assertTrue(request('/missing')['status'].startswith('404'))
    def test_no_file_traversal(self):
        self.assertTrue(request('/static/../release.json')['status'].startswith('404'))
    def test_head(self):
        self.assertEqual(request('/', 'HEAD')['body'], b'')
    def test_post(self):
        self.assertTrue(request('/', 'POST')['status'].startswith('405'))

if __name__ == '__main__':
    unittest.main()
