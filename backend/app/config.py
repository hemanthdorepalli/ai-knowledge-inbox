from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    gemini_api_key: str
    embedding_model: str = "gemini-embedding-001"
    chat_model: str = "gemini-2.5-flash"
    # Gemini can return 768/1536/3072-dim embeddings. We use 768 because
    # pgvector's HNSW index supports up to 2000 dimensions, and 768 is smaller
    # and cheaper while still high quality. Must match vector(768) in the schema.
    embedding_dim: int = 768

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

    # Fixed lifetime token budget given to a new user (covers both ingestion
    # embeddings and chat). Protects the shared Gemini key from runaway cost.
    default_token_quota: int = 50_000

    # Dev-only escape hatch: allows MCP server URLs that resolve to localhost /
    # private IPs, so a developer can test against a locally-running MCP server.
    # Must stay False in any real deployment -- it exists purely for local dev.
    allow_local_mcp_urls: bool = False

    # Public hostname this backend is served on (e.g. "my-api.onrender.com").
    # The bundled demo MCP server keeps DNS-rebinding protection enabled, which
    # validates the Host header against an allowlist -- so the deployed host has
    # to be named here or requests to /mcp-demo get rejected with a 421.
    public_host: str = ""

    # Max tool-calling round trips per question, so a misbehaving MCP server
    # (or a model stuck calling tools) can't loop indefinitely on one request.
    mcp_max_tool_rounds: int = 4

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
