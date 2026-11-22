import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.config import settings
from core.storage.factory import create_session_store
from core.storage.sessions import SessionStore


class StorageFactoryTests(unittest.TestCase):
    def test_local_development_keeps_sqlite(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"VERCEL": ""}), patch.object(settings, "DATABASE_URL", ""), patch.object(settings, "DATABASE_PATH", str(Path(temp) / "sessions.db")):
            self.assertIsInstance(create_session_store(), SessionStore)

    def test_vercel_refuses_ephemeral_sqlite(self):
        with patch.dict(os.environ, {"VERCEL": "1"}), patch.object(settings, "DATABASE_URL", ""):
            with self.assertRaisesRegex(ValueError, "DATABASE_URL"):
                create_session_store()

    def test_database_url_selects_postgres(self):
        with patch.object(settings, "DATABASE_URL", "postgresql://example/test"), patch("core.storage.postgres.PostgresSessionStore") as factory:
            self.assertIs(create_session_store(), factory.return_value)
            factory.assert_called_once_with("postgresql://example/test")
