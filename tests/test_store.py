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
        try:
            os.unlink(self.tmp.name)
        except FileNotFoundError:
            pass

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
