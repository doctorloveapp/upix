"""Persistenza reale, errori atomici e storage browser con lo stesso contratto."""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from uuid import uuid4

from highscores import BrowserScoreStore, JsonScoreStore, ScoreEntry, ScoreStoreError, normalize_name
from manifest import MANIFEST


def entry(name='Lukso', score=1000):
    return ScoreEntry.create(str(uuid4()), name, score, 1, 1000, False)


class StorageTests(unittest.TestCase):
    def test_file_is_versioned_utf8_and_reloaded_from_another_store(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'user_data' / 'highscores.json'
            store = JsonScoreStore(path)
            self.assertEqual(store.load(), [])
            saved = entry('Niccolò', 123456)
            store.submit(saved)
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(data['campaign_id'], MANIFEST['campaign_id'])
            self.assertEqual(data['schema_version'], 1)
            self.assertEqual(data['entries'][0]['name'], 'Niccolò')
            self.assertEqual(JsonScoreStore(path).load(), [saved])
            self.assertEqual(list(path.parent.glob('*.tmp')), [])

    def test_order_limit_and_duplicate_run_are_stable(self):
        with tempfile.TemporaryDirectory() as folder:
            store = JsonScoreStore(Path(folder) / 'highscores.json')
            for score in range(15):
                store.submit(entry(score=score))
            best = store.load()
            self.assertEqual([item.score for item in best], list(range(14, 4, -1)))
            store.submit(replace(best[0], score=100000))
            self.assertEqual(store.load(), best)  # Retry non assegna punti due volte.

    def test_atomic_replace_failure_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'highscores.json'
            store = JsonScoreStore(path)
            store.submit(entry())
            before = path.read_bytes()
            with mock.patch('highscores.os.replace', side_effect=PermissionError('busy')):
                with self.assertRaises(ScoreStoreError):
                    store.submit(entry(score=2000))
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(path.parent.glob('*.tmp')), [])

    def test_corrupt_or_unknown_json_is_never_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'highscores.json'
            for text in ('broken json', '{"schema_version":999}',
                         json.dumps({'schema_version': 1, 'campaign_id': 'different', 'entries': []})):
                path.write_text(text, encoding='utf-8')
                with self.assertRaises(ScoreStoreError):
                    JsonScoreStore(path).submit(entry())
                self.assertEqual(path.read_text(encoding='utf-8'), text)

    def test_invalid_names_scores_and_boolean_numbers_are_rejected(self):
        self.assertEqual(normalize_name('  Niс  LUKSO  '), 'Niс LUKSO')
        for name in ('', '<script>', 'a' * 33):
            with self.subTest(name=name), self.assertRaises(ValueError):
                entry(name)
        for score in (-1, True, 1.2, MANIFEST['leaderboard']['max_score'] + 1):
            with self.subTest(score=score), self.assertRaises(ValueError):
                entry(score=score)

    def test_browser_storage_uses_shared_codec_and_surfaces_write_failure(self):
        class Storage:
            data = {}

            def getItem(self, key):
                return self.data.get(key)

            def setItem(self, key, value):
                self.data[key] = value

        storage = Storage()
        store = BrowserScoreStore(storage)
        saved = entry()
        store.submit(saved)
        self.assertEqual(BrowserScoreStore(storage).load(), [saved])
        with mock.patch.object(storage, 'setItem', side_effect=RuntimeError('quota')):
            with self.assertRaises(ScoreStoreError):
                store.submit(entry(score=2000))
        self.assertEqual(store.load(), [saved])
