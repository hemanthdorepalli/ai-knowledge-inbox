"""Pytest bootstrap.

`app.config.Settings` requires several env vars at import time. The unit tests
below exercise only offline logic (chunking) and never hit the network or the
database, so we inject dummy values before any app module is imported.
"""

import os

os.environ.setdefault("GEMINI_API_KEY", "test-key-not-used")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://user:pass@localhost:5432/test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
