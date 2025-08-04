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
    phoenix_api_key: SecretStr
    phoenix_collector_endpoint: str = "http://localhost:4317"
    phoenix_collector_http_endpoint: str = "http://localhost:6006/v1/traces"

    # --- convenience ---------------------------------------------
    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://postgres:{self.postgres_password.get_secret_value()}@localhost:5432/langgraph"
        )

settings = Settings()