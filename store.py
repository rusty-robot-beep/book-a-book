import json
import os

BOOKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.json")


def load_books():
    if not os.path.exists(BOOKS_FILE):
        return []
    try:
        with open(BOOKS_FILE, encoding='utf-8') as f:
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return []


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


def update_book(book_id, title, author, note):
    books = load_books()
    for book in books:
        if book['id'] == book_id:
            book['title'] = title
            book['author'] = author
            book['note'] = note
            break
    save_books(books)
    return books
