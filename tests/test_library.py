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
