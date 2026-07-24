from pydantic_settings import BaseSettings
from dotenv import load_dotenv


load_dotenv()


class Settings(BaseSettings):
    log_level: str = "INFO"
    log_json: bool = True
    database_url: str


settings = Settings()  # pyright: ignore[reportCallIssue] -- required fields come from env vars
