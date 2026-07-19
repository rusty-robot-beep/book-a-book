import json
import os
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

import library
import store

PORT = 8080
HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress request logging

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/':
            self._serve_html()
        elif path == '/books':
            self._json(200, store.load_books())
        elif path == '/check':
            self._handle_check()
        else:
            self._json(404, {'error': 'Not found'})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/books':
            self._handle_add_book()
        else:
            self._json(404, {'error': 'Not found'})

    def do_PATCH(self):
        path = urlparse(self.path).path
        parts = path.strip('/').split('/')
        if len(parts) == 2 and parts[0] == 'books':
            book_id = parts[1]
            length = int(self.headers.get('Content-Length', 0))
            try:
                body = json.loads(self.rfile.read(length))
            except json.JSONDecodeError:
                self._json(400, {'error': 'Invalid JSON'})
                return
            title = body.get('title', '').strip()
            author = body.get('author', '').strip()
            if not title:
                self._json(400, {'error': 'Title cannot be empty'})
                return
            note = body.get('note', '')
            books = store.update_book(book_id, title, author, note)
            self._json(200, books)
        else:
            self._json(404, {'error': 'Not found'})

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith('/books/'):
            book_id = path.split('/')[-1]
            books = store.remove_book(book_id)
            self._json(200, books)
        else:
            self._json(404, {'error': 'Not found'})

    def _handle_add_book(self):
        length = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self._json(400, {'error': 'Invalid JSON'})
            return
        url = body.get('url', '').strip()
        try:
            book_id = library.extract_book_id(url)
            book = library.fetch_book_metadata(book_id)
            books = store.add_book(book)
            self._json(200, books)
        except (ValueError, KeyError) as e:
            self._json(400, {'error': str(e)})

    def _handle_check(self):
        books = store.load_books()
        results = []
        for book in books:
            try:
                avail = library.fetch_availability(book['id'])
            except ValueError:
                avail = {'manhattan': '', 'zaspa': ''}
            results.append({'id': book['id'], **avail})
        self._json(200, results)

    def _serve_html(self):
        try:
            with open(HTML_FILE, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._json(503, {'error': 'Frontend not available'})

    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run():
    httpd = HTTPServer(('localhost', PORT), Handler)
    print(f"Book-a-Book running at http://localhost:{PORT}")
    threading.Timer(0.5, lambda: webbrowser.open(f'http://localhost:{PORT}')).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        httpd.server_close()


if __name__ == '__main__':
    run()
