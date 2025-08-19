from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    host: str = "0.0.0.0"
    port: int = 8094
    # --- secrets & endpoints you actually need --------------------
    postgres_password: SecretStr
    postgres_url: str = "localhost"
    phoenix_api_key: SecretStr
    phoenix_collector_endpoint: str = "http://host.docker.internal:4317"
    # phoenix_collector_http_endpoint: str = "http://host.docker.internal:6006/v1/traces"
    openai_base_url: str = "http://host.docker.internal:11434/v1"
    openai_api_key: SecretStr
    searxng_host: str = "http://host.docker.internal"
    searxng_port: int = 8082

    # --- convenience ---------------------------------------------
    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://postgres:{self.postgres_password.get_secret_value()}@{self.postgres_url}:5432/langgraph"
        )

settings = Settings()