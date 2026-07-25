from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    log_level: str = "INFO"
    log_json: bool = True
    database_url: str


settings = Settings()  # pyright: ignore[reportCallIssue] -- required fields come from env vars
