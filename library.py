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
