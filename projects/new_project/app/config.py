from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://user:password@localhost:5432/fastapi_db"

    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent / '.env', extra='ignore')

settings = Settings()