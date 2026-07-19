import json
import unittest
import unittest.mock
from http.server import HTTPServer
from io import BytesIO
import threading
import urllib.request

import server


SAMPLE_BOOK = {
    "id": "572329",
    "url": "https://katalog.wbpg.org.pl/document/572329",
    "title": "Czas grzechu",
    "author": "Sakowicz, Anna",
    "cover_url": "https://katalog.wbpg.org.pl/api/image/115928_min.jpg"
}



class TestRoutes(unittest.TestCase):
    def _request(self, method, path, body=None, port=None):
        url = f'http://localhost:{port}{path}'
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, method=method)
        if data:
            req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_get_books_returns_empty_list(self):
        with unittest.mock.patch('server.store') as mock_store:
            mock_store.load_books.return_value = []
            httpd = HTTPServer(('localhost', 0), server.Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.handle_request)
            t.daemon = True
            t.start()
            status, data = self._request('GET', '/books', port=port)
            self.assertEqual(status, 200)
            self.assertEqual(data, [])
            httpd.server_close()

    def test_post_books_adds_book(self):
        with unittest.mock.patch('server.store') as mock_store, \
             unittest.mock.patch('server.library') as mock_lib:
            mock_lib.extract_book_id.return_value = '572329'
            mock_lib.fetch_book_metadata.return_value = SAMPLE_BOOK
            mock_store.add_book.return_value = [SAMPLE_BOOK]
            httpd = HTTPServer(('localhost', 0), server.Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.handle_request)
            t.daemon = True
            t.start()
            status, data = self._request('POST', '/books', {'url': 'https://katalog.wbpg.org.pl/document/572329'}, port=port)
            self.assertEqual(status, 200)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['id'], '572329')
            httpd.server_close()

    def test_post_books_returns_400_for_invalid_url(self):
        with unittest.mock.patch('server.library') as mock_lib:
            mock_lib.extract_book_id.side_effect = ValueError('bad url')
            httpd = HTTPServer(('localhost', 0), server.Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.handle_request)
            t.daemon = True
            t.start()
            status, data = self._request('POST', '/books', {'url': 'https://example.com'}, port=port)
            self.assertEqual(status, 400)
            httpd.server_close()

    def test_get_check_returns_availability(self):
        with unittest.mock.patch('server.store') as mock_store, \
             unittest.mock.patch('server.library') as mock_lib:
            mock_store.load_books.return_value = [SAMPLE_BOOK]
            mock_lib.fetch_availability.return_value = {'manhattan': 'Order', 'zaspa': 'Reserve'}
            httpd = HTTPServer(('localhost', 0), server.Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.handle_request)
            t.daemon = True
            t.start()
            status, data = self._request('GET', '/check', port=port)
            self.assertEqual(status, 200)
            self.assertEqual(data[0]['manhattan'], 'Order')
            self.assertEqual(data[0]['zaspa'], 'Reserve')
            httpd.server_close()

    def test_delete_book_removes_it(self):
        with unittest.mock.patch('server.store') as mock_store:
            mock_store.remove_book.return_value = []
            httpd = HTTPServer(('localhost', 0), server.Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.handle_request)
            t.daemon = True
            t.start()
            status, data = self._request('DELETE', '/books/572329', port=port)
            self.assertEqual(status, 200)
            self.assertEqual(data, [])
            mock_store.remove_book.assert_called_once_with('572329')
            httpd.server_close()


if __name__ == '__main__':
    unittest.main()
