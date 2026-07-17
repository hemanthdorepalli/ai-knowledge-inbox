from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Gemini powers both embeddings and chat here, using one GEMINI_API_KEY.
    gemini_api_key: str
    embedding_model: str = "gemini-embedding-001"
    # Gemini can return 768/1536/3072-dim embeddings. We use 768 because
    # pgvector's HNSW index supports up to 2000 dimensions, and 768 is smaller
    # and cheaper while still high quality. Must match vector(768) in the schema.
    embedding_dim: int = 768

    # Chat goes through an OpenAI-compatible endpoint, so we use the OpenAI SDK
    # pointed at a base URL rather than pulling in a second vendor SDK. The
    # default is Gemini's OpenAI-compatibility layer (same GEMINI_API_KEY,
    # generous free tier, and reliable function calling for MCP tools). To swap
    # providers -- e.g. back to Groq -- set CHAT_BASE_URL + CHAT_MODEL +
    # CHAT_API_KEY; no code changes needed.
    chat_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    chat_model: str = "gemini-2.5-flash"
    # Defaults to gemini_api_key when empty (see resolved_chat_api_key), so the
    # single-provider setup needs only one key. Set it to point chat at a
    # different provider than embeddings.
    chat_api_key: str = ""

    @property
    def resolved_chat_api_key(self) -> str:
        return self.chat_api_key or self.gemini_api_key

    # Supabase Postgres connection string (Project Settings -> Database -> URI).
    supabase_db_url: str

    # Supabase project URL + anon key (Project Settings -> API). Used to verify
    # the user's login token on each request.
    supabase_url: str
    supabase_anon_key: str

    cors_origins: str = "http://localhost:5173"

    chunk_size_chars: int = 1000
    chunk_overlap_chars: int = 150
    top_k: int = 5

    # Token budget per user per rolling window, covering both ingestion
    # (embeddings) and chat, to protect the shared API keys from runaway cost.
    #
    # Note: this is only a real guardrail while it's below the provider's own
    # ceiling. On a free tier the provider's per-day cap can be lower than this
    # per-user quota, in which case a user hits the provider's 429 before their
    # own limit. Lower this (or use a paid key) if the quota should actually
    # bound spend.
    default_token_quota: int = 1_000_000

    # Length of the rolling usage window. The reset is lazy: the first request
    # after the window expires zeroes the counter, so no scheduler is needed.
    quota_window_hours: int = 24

    # Dev-only escape hatch: allows MCP server URLs that resolve to localhost /
    # private IPs, so a developer can test against a locally-running MCP server.
    # Must stay False in any real deployment -- it exists purely for local dev.
    allow_local_mcp_urls: bool = False

    # Public hostname this backend is served on (e.g. "my-api.onrender.com").
    # The bundled demo MCP server keeps DNS-rebinding protection enabled, which
    # validates the Host header against an allowlist -- so the deployed host has
    # to be allowed or requests to /mcp-demo are rejected with a 421.
    #
    # Usually you don't need to set this: the host is auto-detected from the
    # platform (see public_hostname below). Set it only to override, or on a
    # platform we can't detect.
    public_host: str = ""

    # Render sets this automatically to the service's external hostname.
    render_external_hostname: str = ""

    @property
    def public_hostname(self) -> str:
        """The hostname this app is reachable at, explicit setting first."""
        return self.public_host or self.render_external_hostname

    # Max tool-calling round trips per question, so a misbehaving MCP server
    # (or a model stuck calling tools) can't loop indefinitely on one request.
    mcp_max_tool_rounds: int = 4

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
