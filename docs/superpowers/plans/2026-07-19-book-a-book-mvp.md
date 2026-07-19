# Book-a-Book MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Python tool that checks Gdańsk public library book availability at Manhattan and Zaspa branches, launched by double-clicking a file in Finder.

**Architecture:** A stdlib Python HTTP server (`server.py`) serves a single-page frontend (`index.html`) and proxies requests to the library's JSON API. Books are persisted in `books.json`. A `Launch.command` script starts the server and opens the browser.

**Tech Stack:** Python 3 stdlib only (no pip), vanilla HTML/CSS/JS, macOS `.command` launcher.

## Global Constraints

- Python 3 stdlib only — no third-party packages, no pip installs
- macOS only (user's platform)
- Library base URL: `https://katalog.wbpg.org.pl`
- Branch identifiers in holding labels: Manhattan = `"F. 001"`, Zaspa = `"F. 006"`
- Status display: `"Order"` when a copy is available, `"Reserve"` when all copies are loaned, `""` (empty) when branch doesn't hold the book
- Book catalog URL pattern: `https://katalog.wbpg.org.pl/document/{id}`

---

## File Map

```
book-a-book/
├── library.py          # Library API client — fetches metadata + availability
├── store.py            # Book list persistence — reads/writes books.json
├── server.py           # HTTP server — routes, serves index.html, delegates to library/store
├── index.html          # Frontend — single page, vanilla JS, no build step
├── Launch.command      # macOS launcher — starts server, opens browser
├── books.json          # Auto-created on first run; not committed
└── tests/
    ├── test_library.py # Unit tests for library.py
    ├── test_store.py   # Unit tests for store.py
    └── test_routes.py  # Integration tests for HTTP routes
```

---

## Task 1: Project scaffold

**Files:**
- Create: `tests/__init__.py`
- Create: `books.json` (initial empty state)
- Create: `.gitignore`

**Interfaces:**
- Produces: nothing — just scaffolding

- [ ] **Step 1: Create the tests package and .gitignore**

```bash
cd /Users/iwona/Projects/book-a-book
mkdir -p tests
touch tests/__init__.py
echo '*.pyc\n__pycache__/\nbooks.json' > .gitignore
```

- [ ] **Step 2: Verify structure**

```bash
ls tests/
# Expected: __init__.py
```

- [ ] **Step 3: Commit**

```bash
git init
git add tests/__init__.py .gitignore
git commit -m "chore: project scaffold"
```

---

## Task 2: Book store

**Files:**
- Create: `store.py`
- Create: `tests/test_store.py`

**Interfaces:**
- Produces:
  - `load_books() -> list[dict]`
  - `save_books(books: list[dict]) -> None`
  - `add_book(book: dict) -> list[dict]` — no-op if book with same `id` already exists
  - `remove_book(book_id: str) -> list[dict]`
  - Each book dict shape: `{"id": str, "url": str, "title": str, "author": str, "cover_url": str}`

- [ ] **Step 1: Write failing tests**

Create `tests/test_store.py`:

```python
import json
import os
import tempfile
import unittest
import unittest.mock

import store


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self.tmp.close()
        self.patcher = unittest.mock.patch('store.BOOKS_FILE', self.tmp.name)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        os.unlink(self.tmp.name)

    def test_load_books_returns_empty_list_when_file_missing(self):
        os.unlink(self.tmp.name)
        result = store.load_books()
        self.assertEqual(result, [])

    def test_add_book_persists_and_returns_list(self):
        book = {"id": "123", "url": "http://x/123", "title": "T", "author": "A", "cover_url": "http://img"}
        result = store.add_book(book)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], '123')
        self.assertEqual(store.load_books(), result)

    def test_add_book_ignores_duplicate_id(self):
        book = {"id": "123", "url": "http://x/123", "title": "T", "author": "A", "cover_url": "http://img"}
        store.add_book(book)
        store.add_book(book)
        self.assertEqual(len(store.load_books()), 1)

    def test_remove_book_deletes_by_id(self):
        book = {"id": "123", "url": "http://x/123", "title": "T", "author": "A", "cover_url": "http://img"}
        store.add_book(book)
        result = store.remove_book('123')
        self.assertEqual(result, [])
        self.assertEqual(store.load_books(), [])

    def test_remove_book_nonexistent_id_is_noop(self):
        result = store.remove_book('999')
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_store.py -v
# Expected: ImportError or similar — store.py doesn't exist yet
```

- [ ] **Step 3: Implement store.py**

```python
import json
import os

BOOKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.json")


def load_books():
    if not os.path.exists(BOOKS_FILE):
        return []
    with open(BOOKS_FILE, encoding='utf-8') as f:
        return json.load(f)


def save_books(books):
    with open(BOOKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(books, f, indent=2, ensure_ascii=False)


def add_book(book):
    books = load_books()
    if any(b['id'] == book['id'] for b in books):
        return books
    books.append(book)
    save_books(books)
    return books


def remove_book(book_id):
    books = [b for b in load_books() if b['id'] != book_id]
    save_books(books)
    return books
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_store.py -v
# Expected: 5 passed
```

- [ ] **Step 5: Commit**

```bash
git add store.py tests/test_store.py
git commit -m "feat: book store with json persistence"
```

---

## Task 3: Library API client

**Files:**
- Create: `library.py`
- Create: `tests/test_library.py`

**Interfaces:**
- Consumes: nothing from prior tasks
- Produces:
  - `extract_book_id(url: str) -> str` — raises `ValueError` if URL doesn't match pattern
  - `fetch_book_metadata(book_id: str) -> dict` — returns `{"id": str, "url": str, "title": str, "author": str, "cover_url": str}`, raises `ValueError` if not found
  - `fetch_availability(book_id: str) -> dict` — returns `{"manhattan": str, "zaspa": str}` where each value is `"Order"`, `"Reserve"`, or `""`

- [ ] **Step 1: Write failing tests**

Create `tests/test_library.py`:

```python
import unittest
import unittest.mock
import json

import library


SAMPLE_DOCUMENT = {
    "id": 572329,
    "imageLst": [{"url": "/api/image/115928.jpg", "urlMin": "/api/image/115928_min.jpg"}],
    "fieldLst": [
        {"code": "245", "subFieldLst": [
            {"code": "a", "data": "Czas grzechu :"},
            {"code": "b", "data": "Gdańsk 1916-1939 /"},
            {"code": "c", "data": "Anna Sakowicz."}
        ]},
        {"code": "100", "subFieldLst": [
            {"code": "a", "data": "Sakowicz, Anna"},
            {"code": "d", "data": "(1972- )."},
            {"code": "e", "data": "Autor."}
        ]}
    ]
}

SAMPLE_HOLDING = [
    {
        "id": 144,
        "holdingLst": [
            {"id": 1, "availability": "available", "label": "(Sygnatura X)  (Wypożyczalnia)   (do wypożyczenia F. 001)"}
        ]
    },
    {
        "id": 148,
        "holdingLst": [
            {"id": 2, "availability": "loaned", "label": "(Sygnatura X)  (Wypożyczalnia)   (do wypożyczenia F. 006)"}
        ]
    }
]

SAMPLE_HOLDING_NO_BRANCHES = [
    {
        "id": 999,
        "holdingLst": [
            {"id": 3, "availability": "available", "label": "(Sygnatura X)  (Wypożyczalnia)   (do wypożyczenia F. 099)"}
        ]
    }
]


class TestExtractBookId(unittest.TestCase):
    def test_extracts_id_from_full_url(self):
        self.assertEqual(library.extract_book_id('https://katalog.wbpg.org.pl/document/572329'), '572329')

    def test_extracts_id_from_path_only(self):
        self.assertEqual(library.extract_book_id('https://katalog.wbpg.org.pl/document/731755'), '731755')

    def test_raises_for_invalid_url(self):
        with self.assertRaises(ValueError):
            library.extract_book_id('https://example.com/foo/bar')


class TestFetchBookMetadata(unittest.TestCase):
    def _mock_get_json(self, path):
        if '/api/document/' in path:
            return SAMPLE_DOCUMENT
        raise ValueError(f"Unexpected path: {path}")

    def test_returns_title_author_cover(self):
        with unittest.mock.patch('library._get_json', side_effect=self._mock_get_json):
            result = library.fetch_book_metadata('572329')
        self.assertEqual(result['id'], '572329')
        self.assertEqual(result['title'], 'Czas grzechu : Gdańsk 1916-1939')
        self.assertEqual(result['author'], 'Sakowicz, Anna')
        self.assertEqual(result['cover_url'], 'https://katalog.wbpg.org.pl/api/image/115928_min.jpg')
        self.assertEqual(result['url'], 'https://katalog.wbpg.org.pl/document/572329')

    def test_raises_value_error_when_no_image(self):
        doc = {**SAMPLE_DOCUMENT, 'imageLst': []}
        with unittest.mock.patch('library._get_json', return_value=doc):
            with self.assertRaises(ValueError):
                library.fetch_book_metadata('572329')


class TestFetchAvailability(unittest.TestCase):
    def test_order_when_copy_available(self):
        with unittest.mock.patch('library._get_json', return_value=SAMPLE_HOLDING):
            result = library.fetch_availability('572329')
        self.assertEqual(result['manhattan'], 'Order')

    def test_reserve_when_all_copies_loaned(self):
        with unittest.mock.patch('library._get_json', return_value=SAMPLE_HOLDING):
            result = library.fetch_availability('572329')
        self.assertEqual(result['zaspa'], 'Reserve')

    def test_empty_when_branch_not_held(self):
        with unittest.mock.patch('library._get_json', return_value=SAMPLE_HOLDING_NO_BRANCHES):
            result = library.fetch_availability('572329')
        self.assertEqual(result['manhattan'], '')
        self.assertEqual(result['zaspa'], '')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_library.py -v
# Expected: ImportError — library.py doesn't exist yet
```

- [ ] **Step 3: Implement library.py**

```python
import json
import re
import urllib.request
from urllib.error import URLError

BASE_URL = "https://katalog.wbpg.org.pl"
MANHATTAN_CODE = "F. 001"
ZASPA_CODE = "F. 006"


def extract_book_id(url):
    m = re.search(r'/document/(\d+)', url)
    if not m:
        raise ValueError(f"Cannot extract book ID from URL: {url}")
    return m.group(1)


def fetch_book_metadata(book_id):
    doc = _get_json(f"/api/document/{book_id}")
    if not doc.get('imageLst'):
        raise ValueError(f"Book {book_id} has no image — may not exist")
    title = _parse_title(doc['fieldLst'])
    author = _parse_author(doc['fieldLst'])
    cover_url = BASE_URL + doc['imageLst'][0]['urlMin']
    return {
        "id": str(book_id),
        "url": f"{BASE_URL}/document/{book_id}",
        "title": title,
        "author": author,
        "cover_url": cover_url,
    }


def fetch_availability(book_id):
    holdings = _get_json(f"/api/holding/{book_id}")
    return {
        "manhattan": _branch_status(holdings, MANHATTAN_CODE),
        "zaspa": _branch_status(holdings, ZASPA_CODE),
    }


def _branch_status(holdings, branch_code):
    copies = [
        h for branch in holdings
        for h in branch.get('holdingLst', [])
        if branch_code in h.get('label', '')
    ]
    if not copies:
        return ""
    if any(h['availability'] == 'available' for h in copies):
        return "Order"
    return "Reserve"


def _parse_title(field_lst):
    field = _find_field(field_lst, '245')
    if not field:
        return "Unknown title"
    # Subfields a = title proper, b = remainder of title. Subfield c is responsibility statement (author), excluded.
    parts = [
        sf['data'].strip().rstrip('/')
        for sf in field['subFieldLst']
        if sf['code'] in ('a', 'b')
    ]
    return ' '.join(parts).strip().rstrip(':').strip()


def _parse_author(field_lst):
    field = _find_field(field_lst, '100')
    if not field:
        return "Unknown author"
    for sf in field['subFieldLst']:
        if sf['code'] == 'a':
            return sf['data'].rstrip(',').strip()
    return "Unknown author"


def _find_field(field_lst, code):
    for f in field_lst:
        if f['code'] == code:
            return f
    return None


def _get_json(path):
    url = f"{BASE_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except URLError as e:
        raise ValueError(f"Failed to fetch {url}: {e}")
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_library.py -v
# Expected: 7 passed
```

- [ ] **Step 5: Commit**

```bash
git add library.py tests/test_library.py
git commit -m "feat: library API client for metadata and availability"
```

---

## Task 4: HTTP server and routes

**Files:**
- Create: `server.py`
- Create: `tests/test_routes.py`

**Interfaces:**
- Consumes:
  - `store.load_books() -> list[dict]`
  - `store.add_book(book: dict) -> list[dict]`
  - `store.remove_book(book_id: str) -> list[dict]`
  - `library.extract_book_id(url: str) -> str`
  - `library.fetch_book_metadata(book_id: str) -> dict`
  - `library.fetch_availability(book_id: str) -> dict`
- Produces:
  - HTTP server running on `localhost:8080`
  - Routes: `GET /`, `GET /books`, `POST /books`, `DELETE /books/{id}`, `GET /check`

- [ ] **Step 1: Write failing tests**

Create `tests/test_routes.py`:

```python
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


def start_test_server():
    httpd = HTTPServer(('localhost', 0), server.Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.handle_request)
    t.daemon = True
    return httpd, port


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


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_routes.py -v
# Expected: ImportError — server.py doesn't exist yet
```

- [ ] **Step 3: Implement server.py**

```python
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
        body = json.loads(self.rfile.read(length))
        url = body.get('url', '').strip()
        try:
            book_id = library.extract_book_id(url)
            book = library.fetch_book_metadata(book_id)
            books = store.add_book(book)
            self._json(200, books)
        except ValueError as e:
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
        with open(HTML_FILE, 'rb') as f:
            content = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
python -m pytest tests/test_routes.py -v
# Expected: 4 passed
```

- [ ] **Step 5: Commit**

```bash
git add server.py tests/test_routes.py
git commit -m "feat: HTTP server with book and availability routes"
```

---

## Task 5: Frontend

**Files:**
- Create: `index.html`

**Interfaces:**
- Consumes:
  - `GET /books` → `list[{id, url, title, author, cover_url}]`
  - `POST /books` body `{url: string}` → `list[{id, url, title, author, cover_url}]`
  - `DELETE /books/{id}` → `list[{id, url, title, author, cover_url}]`
  - `GET /check` → `list[{id, manhattan, zaspa}]` where each status is `"Order"`, `"Reserve"`, or `""`
- Produces: nothing (end of chain)

- [ ] **Step 1: Create index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Book-a-Book</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #222; }
    header { background: #1a73e8; color: white; padding: 16px 24px; display: flex; align-items: center; gap: 16px; }
    header h1 { font-size: 1.2rem; font-weight: 600; }
    .toolbar { display: flex; gap: 8px; flex: 1; }
    .toolbar input { flex: 1; padding: 8px 12px; border: none; border-radius: 6px; font-size: 0.9rem; }
    .btn { padding: 8px 16px; border: none; border-radius: 6px; font-size: 0.9rem; cursor: pointer; font-weight: 500; }
    .btn-add { background: white; color: #1a73e8; }
    .btn-check { background: #34a853; color: white; }
    .btn-add:hover { background: #e8f0fe; }
    .btn-check:hover { background: #2d8f47; }
    .error-banner { background: #fce8e6; color: #c5221f; padding: 10px 24px; font-size: 0.85rem; display: none; }
    main { padding: 24px; }
    .empty { text-align: center; color: #888; margin-top: 60px; font-size: 1rem; }
    table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    th { background: #f8f9fa; padding: 12px 16px; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; color: #666; border-bottom: 1px solid #e0e0e0; }
    td { padding: 12px 16px; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }
    tr:last-child td { border-bottom: none; }
    .book-cover { width: 40px; height: 56px; object-fit: cover; border-radius: 3px; }
    .book-title { font-weight: 500; font-size: 0.95rem; }
    .book-author { font-size: 0.82rem; color: #666; margin-top: 2px; }
    .status-order { display: inline-block; background: #e6f4ea; color: #137333; padding: 4px 10px; border-radius: 12px; font-size: 0.82rem; font-weight: 500; text-decoration: none; }
    .status-reserve { display: inline-block; background: #fce8e6; color: #c5221f; padding: 4px 10px; border-radius: 12px; font-size: 0.82rem; font-weight: 500; text-decoration: none; }
    .status-order:hover, .status-reserve:hover { opacity: 0.8; }
    .btn-delete { background: none; border: none; color: #ccc; cursor: pointer; font-size: 1.1rem; padding: 4px 8px; border-radius: 4px; }
    .btn-delete:hover { color: #c5221f; background: #fce8e6; }
    .checking { opacity: 0.5; }
    .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #ccc; border-top-color: #1a73e8; border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: middle; margin-right: 6px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <header>
    <h1>Book-a-Book</h1>
    <div class="toolbar">
      <input type="text" id="url-input" placeholder="Paste catalog URL, e.g. https://katalog.wbpg.org.pl/document/572329" />
      <button class="btn btn-add" onclick="addBook()">Add</button>
    </div>
    <button class="btn btn-check" onclick="checkAll()">Check availability</button>
  </header>
  <div class="error-banner" id="error-banner"></div>
  <main>
    <div class="empty" id="empty-msg">No books yet. Paste a catalog URL above to add one.</div>
    <table id="books-table" style="display:none">
      <thead>
        <tr>
          <th></th>
          <th>Book</th>
          <th>Manhattan</th>
          <th>Zaspa</th>
          <th></th>
        </tr>
      </thead>
      <tbody id="books-body"></tbody>
    </table>
  </main>

  <script>
    let books = [];
    let availability = {};

    async function loadBooks() {
      const res = await fetch('/books');
      books = await res.json();
      render();
    }

    async function addBook() {
      const input = document.getElementById('url-input');
      const url = input.value.trim();
      if (!url) return;
      showError('');
      input.disabled = true;
      try {
        const res = await fetch('/books', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({url})
        });
        const data = await res.json();
        if (!res.ok) { showError(data.error || 'Failed to add book'); return; }
        books = data;
        input.value = '';
        render();
      } catch (e) {
        showError('Could not reach server');
      } finally {
        input.disabled = false;
      }
    }

    async function removeBook(id) {
      const res = await fetch(`/books/${id}`, {method: 'DELETE'});
      books = await res.json();
      delete availability[id];
      render();
    }

    async function checkAll() {
      showError('');
      document.getElementById('books-body').classList.add('checking');
      try {
        const res = await fetch('/check');
        if (!res.ok) { showError('Check failed'); return; }
        const results = await res.json();
        availability = {};
        results.forEach(r => { availability[r.id] = r; });
        render();
      } catch (e) {
        showError('Could not reach server');
      } finally {
        document.getElementById('books-body').classList.remove('checking');
      }
    }

    function render() {
      const empty = document.getElementById('empty-msg');
      const table = document.getElementById('books-table');
      const tbody = document.getElementById('books-body');
      if (books.length === 0) {
        empty.style.display = 'block';
        table.style.display = 'none';
        return;
      }
      empty.style.display = 'none';
      table.style.display = 'table';
      tbody.innerHTML = books.map(book => {
        const avail = availability[book.id] || {};
        return `<tr>
          <td><img class="book-cover" src="${book.cover_url}" alt="" onerror="this.style.display='none'"></td>
          <td>
            <div class="book-title">${esc(book.title)}</div>
            <div class="book-author">${esc(book.author)}</div>
          </td>
          <td>${statusBadge(avail.manhattan, book.url)}</td>
          <td>${statusBadge(avail.zaspa, book.url)}</td>
          <td><button class="btn-delete" onclick="removeBook('${book.id}')" title="Remove">×</button></td>
        </tr>`;
      }).join('');
    }

    function statusBadge(status, url) {
      if (status === 'Order') return `<a class="status-order" href="${url}" target="_blank">Order</a>`;
      if (status === 'Reserve') return `<a class="status-reserve" href="${url}" target="_blank">Reserve</a>`;
      return '';
    }

    function showError(msg) {
      const el = document.getElementById('error-banner');
      el.textContent = msg;
      el.style.display = msg ? 'block' : 'none';
    }

    function esc(str) {
      return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    document.getElementById('url-input').addEventListener('keydown', e => {
      if (e.key === 'Enter') addBook();
    });

    loadBooks();
  </script>
</body>
</html>
```

- [ ] **Step 2: Verify server serves the page**

Start the server manually and open the browser:

```bash
python server.py
# Open http://localhost:8080 — should show the Book-a-Book UI with empty state
```

Stop with Ctrl+C.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: frontend — book list with add, check, and remove"
```

---

## Task 6: Launch.command (double-click launcher)

**Files:**
- Create: `Launch.command`

**Interfaces:**
- Consumes: `server.py` (runs it)
- Produces: running server + open browser tab

- [ ] **Step 1: Create Launch.command**

```bash
#!/bin/bash
cd "$(dirname "$0")"
python3 server.py
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x Launch.command
```

- [ ] **Step 3: Test by double-clicking**

Double-click `Launch.command` in Finder. A Terminal window should open and `http://localhost:8080` should open in the browser. Verify:
- Empty state message shown
- Paste `https://katalog.wbpg.org.pl/document/572329`, click Add — book appears with cover, title, author
- Click "Check availability" — Manhattan and Zaspa columns update
- Click Order/Reserve badge — opens catalog URL in new tab
- Click × — book removed

- [ ] **Step 4: Commit**

```bash
git add Launch.command
git commit -m "feat: double-click launcher for macOS"
```

---

## Task 7: Run all tests

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v
# Expected: all tests pass
```

- [ ] **Step 2: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address any issues found in full test run"
```
