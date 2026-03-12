from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o"
    max_validation_retries: int = 1
    confidence_threshold: float = 0.7

    model_config = SettingsConfigDict(env_file=".env")


def get_settings() -> Settings:
    return Settings()
