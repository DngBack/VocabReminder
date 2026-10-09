"""Local SQLite persistence and fair deck rotation."""

import json
import os
import random
import sqlite3
from datetime import datetime
from pathlib import Path


def data_dir():
    base = Path(os.getenv("LOCALAPPDATA") or Path.home())
    path = base / "VocalReminderPoke"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Store:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_dir() / "vocabulary.sqlite3"
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
                orb TEXT NOT NULL DEFAULT 'poke_ball', pokemon TEXT NOT NULL DEFAULT 'pikachu',
                queue TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY, deck_id INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
                term TEXT NOT NULL, part_of_speech TEXT NOT NULL DEFAULT '',
                meaning_en TEXT NOT NULL DEFAULT '', meaning_vi TEXT NOT NULL DEFAULT '',
                example TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
                UNIQUE(deck_id, term)
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY, word_id INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
                reviewed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        self.db.commit()
        columns = {row[1] for row in self.db.execute("PRAGMA table_info(decks)")}
        if "pokemon" not in columns:
            with self.db:
                self.db.execute("ALTER TABLE decks ADD COLUMN pokemon TEXT NOT NULL DEFAULT 'pikachu'")
        legacy_orbs = {"coral": "poke_ball", "ocean": "great_ball",
                       "sunflower": "ultra_ball", "lavender": "master_ball",
                       "mint": "premier_ball", "sunset": "luxury_ball"}
        with self.db:
            for old, new in legacy_orbs.items():
                self.db.execute("UPDATE decks SET orb=? WHERE orb=?", (new, old))
        if not self.decks():
            self.add_deck("Bộ từ đầu tiên", "poke_ball", "pikachu")

    def decks(self):
        return self.db.execute("SELECT * FROM decks ORDER BY id").fetchall()

    def add_deck(self, name, orb, pokemon="pikachu"):
        with self.db:
            cur = self.db.execute("INSERT INTO decks(name,orb,pokemon,created_at) VALUES(?,?,?,?)",
                                  (name.strip(), orb, pokemon, datetime.now().isoformat()))
        return cur.lastrowid

    def update_deck(self, deck_id, name, orb, pokemon):
        with self.db:
            self.db.execute("UPDATE decks SET name=?,orb=?,pokemon=? WHERE id=?",
                            (name.strip(), orb, pokemon, deck_id))

    def add_word(self, deck_id, term, part_of_speech, meaning_en, meaning_vi, example):
        with self.db:
            cur = self.db.execute("""INSERT INTO words(deck_id,term,part_of_speech,meaning_en,meaning_vi,example,created_at)
                                     VALUES(?,?,?,?,?,?,?)""",
                                  (deck_id, term.strip(), part_of_speech.strip(), meaning_en.strip(),
                                   meaning_vi.strip(), example.strip(), datetime.now().isoformat()))
        return cur.lastrowid

    def words(self, deck_id):
        return self.db.execute("SELECT * FROM words WHERE deck_id=? ORDER BY id DESC", (deck_id,)).fetchall()

    def delete_word(self, word_id):
        with self.db:
            self.db.execute("DELETE FROM words WHERE id=?", (word_id,))

    def settings(self, key, default=None):
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_setting(self, key, value):
        with self.db:
            self.db.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                            (key, json.dumps(value)))

    def next_batch(self, deck_id, count):
        ids = [r[0] for r in self.db.execute("SELECT id FROM words WHERE deck_id=?", (deck_id,))]
        if not ids:
            return []
        count = min(count, len(ids))
        deck = self.db.execute("SELECT queue FROM decks WHERE id=?", (deck_id,)).fetchone()
        queue = [i for i in json.loads(deck[0]) if i in ids]
        selected = []
        while len(selected) < count:
            if not queue:
                queue = ids.copy()
                random.shuffle(queue)
            picked = queue.pop(0)
            if picked not in selected:
                selected.append(picked)
        with self.db:
            self.db.execute("UPDATE decks SET queue=? WHERE id=?", (json.dumps(queue), deck_id))
        marks = ",".join("?" for _ in selected)
        rows = self.db.execute(f"SELECT * FROM words WHERE id IN ({marks})", selected).fetchall()
        by_id = {r["id"]: r for r in rows}
        return [by_id[i] for i in selected]

    def record_review(self, word_id):
        with self.db:
            self.db.execute("INSERT INTO reviews(word_id,reviewed_at) VALUES(?,?)",
                            (word_id, datetime.now().isoformat()))

    def stats(self, deck_id):
        total = self.db.execute("SELECT COUNT(*) FROM words WHERE deck_id=?", (deck_id,)).fetchone()[0]
        reviewed = self.db.execute("""SELECT COUNT(DISTINCT r.word_id) FROM reviews r
                                      JOIN words w ON w.id=r.word_id WHERE w.deck_id=?""", (deck_id,)).fetchone()[0]
        sessions = self.db.execute("""SELECT COUNT(*) FROM reviews r JOIN words w ON w.id=r.word_id
                                      WHERE w.deck_id=?""", (deck_id,)).fetchone()[0]
        today = self.db.execute("""SELECT COUNT(*) FROM reviews r JOIN words w ON w.id=r.word_id
                                   WHERE w.deck_id=? AND substr(r.reviewed_at,1,10)=?""",
                                (deck_id, datetime.now().date().isoformat())).fetchone()[0]
        return total, reviewed, sessions, today

    def close(self):
        self.db.close()
