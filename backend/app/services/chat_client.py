from openai import OpenAI

from app.config import settings

# Chat client. Talks to an OpenAI-compatible endpoint -- by default Gemini's
# OpenAI-compatibility layer (see config.chat_base_url), which lets us keep the
# whole OpenAI-shaped tool-calling loop in rag.py while running on Gemini's
# GEMINI_API_KEY. Isolating construction here means the rest of the app depends
# on `client`, not on how chat is configured, so swapping providers is a
# config-only change (CHAT_BASE_URL / CHAT_MODEL / CHAT_API_KEY).
client = OpenAI(api_key=settings.resolved_chat_api_key, base_url=settings.chat_base_url)
