from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Reel Factory API"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://reel_factory:reel_factory_dev@localhost:5432/reel_factory"
    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


settings = Settings()
