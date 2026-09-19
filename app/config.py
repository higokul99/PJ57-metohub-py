from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Application
    APP_NAME: str = "Metohub"
    APP_ENV: str = "local"
    APP_DEBUG: bool = False
    APP_URL: str = "http://127.0.0.1:8000"

    # Security
    SECRET_KEY: str

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "metohub"
    DB_USER: str = "metohub"
    DB_PASSWORD: str

    # Mail
    MAIL_HOST: str = "smtp.hostinger.com"
    MAIL_PORT: int = 465
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_ENCRYPTION: str = "ssl"
    MAIL_FROM_ADDRESS: str = ""
    MAIL_FROM_NAME: str = "Metohub"

    # Uploads
    MAX_IMAGE_BYTES: int = 400 * 1024

    @property
    def database_url(self) -> str:
        user = quote_plus(self.DB_USER)
        password = quote_plus(self.DB_PASSWORD)

        return (
            f"postgresql+psycopg://"
            f"{user}:{password}@"
            f"{self.DB_HOST}:{self.DB_PORT}/"
            f"{self.DB_NAME}"
        )


settings = Settings()
