from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    APP_NAME: str = "Metohub"
    APP_ENV: str = "local"
    APP_DEBUG: bool = True
    APP_URL: str = "http://127.0.0.1:8000"
    SECRET_KEY: str = "glov-dev-secret-change-me"

    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_NAME: str = "glov_py"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    MAIL_HOST: str = "smtp.hostinger.com"
    MAIL_PORT: int = 465
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_ENCRYPTION: str = "ssl"
    MAIL_FROM_ADDRESS: str = ""
    MAIL_FROM_NAME: str = "Metohub"

    MAX_IMAGE_BYTES: int = 400 * 1024

    @property
    def database_url(self) -> str:
        password = self.DB_PASSWORD or ""
        auth = self.DB_USER if not password else f"{self.DB_USER}:{password}"
        return (
            f"mysql+pymysql://{auth}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            "?charset=utf8mb4"
        )


settings = Settings()
