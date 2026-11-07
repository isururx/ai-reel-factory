from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Reel Factory API"
    app_env: str = "development"
    database_url: str = "sqlite:///./reel_factory.db"
    redis_url: str = "redis://localhost:6379/0"
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket_name: str | None = None
    r2_public_base_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def r2_endpoint_url(self) -> str | None:
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com" if self.r2_account_id else None

settings = Settings()
