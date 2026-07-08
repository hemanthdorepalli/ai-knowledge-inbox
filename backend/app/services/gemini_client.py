from google import genai

from app.config import settings

# Single shared Gemini client. Isolating construction here means the rest of the
# app depends on `client`, not on how it's configured, so swapping providers is
# a one-file change.
client = genai.Client(api_key=settings.gemini_api_key)
