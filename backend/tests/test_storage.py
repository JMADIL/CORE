"""SQLite lease regressions without the HTTP application or a running event loop."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from core.storage.errors import SessionBusy
from core.storage.sessions import SessionStore


class SessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / "sessions.db")
        self.store = SessionStore(self.path)

    def test_atomic_claim_across_workers(self):
        store = self.store
        owner = "owner"
        def claim():
            try:
                lease, _ = SessionStore(self.path).claim("parallel", owner, "local")
                return lease
            except SessionBusy:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: claim(), range(2)))
        self.assertEqual(sum(isinstance(value, str) for value in results), 1)
        self.assertIn(None, results)
        for result in results:
            if isinstance(result, str):
                store.finish("parallel", result)

    def test_expiration_and_stale_lease(self):
        store = self.store
        owner = "owner"
        lease, _ = store.claim("expiring", owner, "local")
        with store.connect() as db:
            db.execute("UPDATE sessions SET updated = 0, busy_until = 0 WHERE id = 'expiring'")
        replacement, _ = store.claim("expiring", "new-owner", "local")
        store.finish("expiring", lease)
        with store.connect() as db:
            self.assertEqual(db.execute("SELECT lease FROM sessions WHERE id = 'expiring'").fetchone()[0], replacement)


if __name__ == "__main__":
    unittest.main()
