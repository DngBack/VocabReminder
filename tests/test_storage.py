import tempfile
import unittest
import sqlite3
from pathlib import Path

from vocab_reminder.storage import Store


class RotationTest(unittest.TestCase):
    def test_every_word_is_seen_before_cycle_repeats(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.sqlite3")
            deck = store.decks()[0]["id"]
            for number in range(7):
                store.add_word(deck, f"word-{number}", "noun", "", "nghĩa", "")
            first = store.next_batch(deck, 5)
            second = store.next_batch(deck, 5)
            self.assertEqual(len({word["id"] for word in first + second}), 7)
            self.assertEqual(len({word["id"] for word in first}), 5)
            self.assertEqual(len({word["id"] for word in second}), 5)
            store.record_review(first[0]["id"])
            self.assertEqual(store.stats(deck), (7, 1, 1, 1))
            store.close()

    def test_existing_deck_keeps_words_after_sprite_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old.sqlite3"
            db = sqlite3.connect(path)
            db.executescript("""
                CREATE TABLE decks(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
                    orb TEXT NOT NULL, queue TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE words(id INTEGER PRIMARY KEY, deck_id INTEGER NOT NULL,
                    term TEXT NOT NULL, part_of_speech TEXT NOT NULL,
                    meaning_en TEXT NOT NULL, meaning_vi TEXT NOT NULL,
                    example TEXT NOT NULL, created_at TEXT NOT NULL,
                    UNIQUE(deck_id, term));
                INSERT INTO decks VALUES(1,'Old','coral','[]','2026-01-01');
                INSERT INTO words VALUES(1,1,'hello','','','xin chào','','2026-01-01');
            """)
            db.close()
            store = Store(path)
            self.assertEqual(store.decks()[0]["orb"], "poke_ball")
            self.assertEqual(store.decks()[0]["pokemon"], "pikachu")
            self.assertEqual(store.words(1)[0]["term"], "hello")
            store.close()


if __name__ == "__main__":
    unittest.main()
