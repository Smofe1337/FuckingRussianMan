# database — thin sqlite wrapper for learned messages
# opens a fresh connection per call — no pooling needed for this workload

import sqlite3
import logging
from typing import List

log = logging.getLogger(__name__)


class Database:
    # holds all learned texts — injected path so no hardcoded shit anywhere

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        # new connection every time — sqlite handles this fine dont overthink it
        return sqlite3.connect(self._db_path)

    def _ensure_table(self) -> None:
        # creates the table if it doesnt exist — safe to call multiple times
        with self._connect() as con:
            con.execute('''
                CREATE TABLE IF NOT EXISTS learned_messages (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    text       TEXT NOT NULL,
                    source     TEXT DEFAULT 'channel',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            con.commit()

    def get_transcripts(self) -> List[str]:
        # returns all texts in random order — used for building the rag index
        con = self._connect()
        cur = con.cursor()
        cur.execute(
            'SELECT text FROM learned_messages WHERE length(text) > 15 ORDER BY RANDOM()'
        )
        rows = [r[0] for r in cur.fetchall()]
        con.close()
        return rows

    def save_learned(self, text: str, source: str = 'channel') -> None:
        # shoves a new message into db — fire and forget
        with self._connect() as con:
            con.execute(
                'INSERT INTO learned_messages (text, source) VALUES (?, ?)',
                (text, source),
            )
            con.commit()

    def get_learned(self, limit: int = 80) -> List[str]:
        # most recent messages up to limit — used when rag has no examples
        con = self._connect()
        cur = con.cursor()
        cur.execute(
            'SELECT text FROM learned_messages ORDER BY created_at DESC LIMIT ?',
            (limit,),
        )
        rows = [r[0] for r in cur.fetchall()]
        con.close()
        return rows

    def stats(self) -> dict:
        # total count and breakdown by source — for the stats panel
        con = self._connect()
        cur = con.cursor()

        cur.execute('SELECT source, COUNT(*) FROM learned_messages GROUP BY source')
        by_source = dict(cur.fetchall())

        cur.execute('SELECT COUNT(*) FROM learned_messages')
        total = cur.fetchone()[0]

        con.close()
        return {'total': total, 'by_source': by_source}
