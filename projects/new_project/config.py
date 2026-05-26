from pydantic_settings import BaseSettings, SettingsConfigDict
from functantic.typing import Literal


class Settings(BaseSettings):
    # Database connection URL
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/todo_db"

    # Application environment
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"

    # Define the .env file location
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()