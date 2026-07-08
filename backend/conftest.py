"""Pytest bootstrap.

`app.config.Settings` requires GEMINI_API_KEY at import time. The unit tests
below exercise only the offline logic (chunking, cosine search) and never make
network calls, so we inject a dummy key before any app module is imported.
"""

import os

os.environ.setdefault("GEMINI_API_KEY", "test-key-not-used")
