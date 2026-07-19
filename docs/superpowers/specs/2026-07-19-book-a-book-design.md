# Book-a-Book: Design Spec
_Date: 2026-07-19_

## What we're building

A personal tool to check whether books from the Gdańsk public library catalog (katalog.wbpg.org.pl) are currently available to borrow at two specific branches: **Manhattan** (Filia nr 001) and **Zaspa** (Filia nr 006 Biblioteka Pilotów).

The user maintains a personal list of books and checks availability on demand.

---

## Phase 1: Python MVP (local)

### User experience

1. User double-clicks `Launch.command` in Finder — browser opens automatically to `http://localhost:8080`
2. User pastes a book catalog URL (e.g. `https://katalog.wbpg.org.pl/document/572329`) and clicks **Add**
3. Book appears in the list with its cover, title, and author
4. User clicks **Check availability** — all books are checked against the library API
5. Table updates showing status per branch:
   - **Order** — can be borrowed now
   - **Reserve** — all copies currently on loan
   - _(empty)_ — this branch doesn't have the book
6. Clicking a book's status links to its catalog page

The book list persists between sessions.

### Architecture

```
Launch.command (double-click to start)
    └── starts server.py → opens browser

browser (localhost:8080)
    ├── GET /          → HTML page (served inline from server.py)
    ├── GET /books     → returns saved book list (books.json)
    ├── POST /books    → adds a book by URL
    ├── DELETE /books/{id} → removes a book
    └── GET /check     → fetches live availability for all books
            ├── GET katalog.wbpg.org.pl/api/document/{id}
            └── GET katalog.wbpg.org.pl/api/holding/{id}
```

### Library API

Base URL: `https://katalog.wbpg.org.pl`

**Book metadata:** `GET /api/document/{id}`
- Yields: title (field code `245`, subfield `a`+`b`+`c`), author (field `100`, subfield `a`), cover image URL (from `imageLst[0].urlMin`)

**Availability:** `GET /api/holding/{id}`
- Returns array of branch objects, each with a `holdingLst` array
- Each holding has `availability: "available" | "loaned"` and a `label` string
- Branch identification is via the label string:
  - Manhattan → label contains `"F. 001"`
  - Zaspa → label contains `"F. 006"`
- If no holding matches a branch label, status = "Not held"

**Book ID extraction:** strip from URL path, e.g. `katalog.wbpg.org.pl/document/572329` → `572329`

### Files

```
book-a-book/
├── server.py          # Python stdlib only — HTTP server + API proxy + HTML
├── books.json         # Persisted book list (created on first run)
└── Launch.command     # Double-clickable macOS launcher
```

No third-party Python packages. Requires Python 3 (pre-installed on macOS).

### Error handling

- Invalid URL pasted → show inline error, don't add to list
- Book ID not found by library API → show "Not found" in list
- Library API unreachable → show error banner, keep last known results
- Empty book list → show prompt to add first book

---

## Phase 2: Lovable web app

To be designed separately. Key constraints carried forward:

- **CORS:** `katalog.wbpg.org.pl` does not send permissive CORS headers — all API calls must go through a server-side proxy (Supabase Edge Function)
- **Same API endpoints** and data shape as Phase 1
- **Same two branches** (F. 001 Manhattan, F. 006 Zaspa)
- Supabase database replaces `books.json` for persistence
- Accessible from any device (phone, tablet)

---

## Key discoveries from investigation

- The site is an Angular SPA but exposes clean JSON REST APIs — **no browser automation or JS rendering needed**
- Availability data is fully available in `/api/holding/{id}` without clicking any UI elements
- The map modal described in the original spec is just a visual layer over this API data
- CORS blocks direct browser-to-API calls from any non-`katalog.wbpg.org.pl` origin
