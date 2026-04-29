from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str
    database_url: str = "sqlite:////data/app.db"
    domain: str = "localhost"
    debug: bool = False
    cookie_secure: bool = True
    session_max_age_days: int = 7
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
