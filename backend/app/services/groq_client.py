from openai import OpenAI

from app.config import settings

# Groq exposes an OpenAI-compatible API, so we use the OpenAI SDK pointed at
# Groq's base URL rather than pulling in another vendor SDK. Isolating the
# client here means the rest of the app depends on `client`, not on how chat is
# configured -- the same shape as gemini_client.py does for embeddings.
client = OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
