import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = f"sqlite:///{(Path(__file__).resolve().parent.parent / 'agape.db').as_posix()}"
    secret_key: str = "development-only-change-before-deploying"
    session_cookie_name: str = "agape_session"
    cookie_secure: bool = False
    session_hours: int = 168
    cors_origins: str = "http://localhost:5173"
    business_whatsapp: str = "5511933293434"
    business_email: str = "agapeconfeitaria06@gmail.com"
    instagram_url: str = "https://www.instagram.com/confeitaria_agape_artesanal_/"
    minimum_order_notice_hours: int = 48
    upload_dir: str = Field(default_factory=lambda: "/tmp/uploads" if os.environ.get("VERCEL") == "1" else "./uploads")
    app_env: str = "development"

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        if isinstance(value, str):
            for prefix in ("postgres://", "postgresql://"):
                if value.startswith(prefix):
                    return value.replace(prefix, "postgresql+psycopg://", 1)
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()