from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    gemini_api_key: str
    embedding_model: str = "gemini-embedding-001"
    chat_model: str = "gemini-2.5-flash"
    db_path: str = "./data/inbox.db"
    cors_origins: str = "http://localhost:5173"

    chunk_size_chars: int = 1000
    chunk_overlap_chars: int = 150
    top_k: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
