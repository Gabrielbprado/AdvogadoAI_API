"""Application settings and configuration helpers."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional
from urllib.parse import quote_plus
import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import EnvSettingsSource, DotEnvSettingsSource


class Settings(BaseSettings):
    """Strongly typed settings loaded from the environment or .env files."""

    app_name: str = Field(default="LawerAI")
    environment: str = Field(default="development")
    storage_dir: Path = Field(default=Path("data/uploads"))

    # Database configuration
    database_provider: Literal["sqlite", "mysql", "azure_sql"] = Field(default="sqlite")
    database_url: Optional[str] = Field(default=None, description="Overrides provider-based URL if set")

    # SQLite
    sqlite_path: Path = Field(default=Path("data/app.db"))

    # MySQL
    mysql_host: str = Field(default="localhost")
    mysql_port: int = Field(default=3306)
    mysql_user: str = Field(default="root")
    mysql_password: str = Field(default="password")
    mysql_db: str = Field(default="app")

    # Azure SQL (SQL Server)
    azure_sql_server: Optional[str] = Field(default=None, description="e.g. myserver.database.windows.net")
    azure_sql_port: int = Field(default=1433)
    azure_sql_database: Optional[str] = Field(default=None)
    azure_sql_user: Optional[str] = Field(default=None)
    azure_sql_password: Optional[str] = Field(default=None)
    azure_sql_trust_server_certificate: bool = Field(default=True)
    llm_provider: Literal["openai", "gemini", "groq", "ollama"] = Field(default="openai")
    crewai_model: Optional[str] = Field(default=None)
    openai_model: str = Field(default="gpt-4o-mini")
    gemini_model: str = Field(default="gemini-1.5-pro")
    groq_model: str = Field(default="llama3-70b-8192")
    ollama_model: str = Field(default="llama3")
    ollama_base_url: Optional[str] = Field(default="http://localhost:11434")
    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(default=None, validation_alias="GOOGLE_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, validation_alias="GROQ_API_KEY")
    crewai_log_level: Optional[str] = Field(default=None, validation_alias="CREWAI_LOG_LEVEL")
    crewai_logging_level: Optional[str] = Field(default=None, validation_alias="CREWAI_LOGGING_LEVEL")
    max_chunk_size: int = Field(default=2000, ge=256)
    langgraph_concurrency: int = Field(default=1, ge=1)
    jwt_secret_key: str = Field(default="change-me", min_length=16)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)
    cors_allowed_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        validation_alias="CORS_ALLOWED_ORIGINS",
    )

    # Database initialization
    run_ddl_on_startup: bool = Field(default=True, description="Run create_all at app start (disable in prod)")

    jwt_expiration_hours: Optional[int] = Field(default=None, description="Deprecated; use access_token_expire_minutes")
    api_rate_limit_per_minute: Optional[int] = Field(default=None, description="Reserved for future rate limiting")
    enable_api_auth: bool = Field(default=True, description="Toggle auth for debugging environments")

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        # Accept JSON array, comma-separated string, or empty/None -> fallback default
        if value in (None, "", "[]"):
            return ["http://localhost:5173", "http://127.0.0.1:5173"]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LAWERAI_",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        class SafeEnvSettingsSource(EnvSettingsSource):
            def decode_complex_value(self, field_name, field, value):
                try:
                    return super().decode_complex_value(field_name, field, value)
                except Exception:
                    if value in ("", None):
                        return None
                    if isinstance(value, str):
                        return [v.strip() for v in value.split(",") if v.strip()]
                    return value

        class SafeDotEnvSettingsSource(DotEnvSettingsSource):
            def decode_complex_value(self, field_name, field, value):
                try:
                    return super().decode_complex_value(field_name, field, value)
                except Exception:
                    if value in ("", None):
                        return None
                    if isinstance(value, str):
                        return [v.strip() for v in value.split(",") if v.strip()]
                    return value

        return (
            init_settings,
            SafeEnvSettingsSource(settings_cls),
            SafeDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )

    def resolve_llm_model(self) -> str:
        """Return the concrete model to be used by CrewAI based on provider preferences."""
        if self.crewai_model:
            return self.crewai_model
        provider_defaults = {
            "openai": self.openai_model,
            "gemini": self.gemini_model,
            "groq": self.groq_model,
            "ollama": self.ollama_model,
        }
        return provider_defaults[self.llm_provider]

    def resolve_llm_base_url(self) -> Optional[str]:
        """Return provider specific base URL overrides when needed."""
        if self.llm_provider == "ollama":
            return self.ollama_base_url
        return None

    def resolve_llm_api_key(self) -> Optional[str]:
        """Return provider specific API key when available."""
        if self.llm_provider == "openai":
            return self.openai_api_key
        if self.llm_provider == "gemini":
            return self.google_api_key
        if self.llm_provider == "groq":
            return self.groq_api_key
        return None

    def build_database_url(self) -> str:
        """Return the database URL based on provider or explicit override."""
        if self.database_url:
            return self.database_url

        if self.database_provider == "sqlite":
            return f"sqlite:///{self.sqlite_path}"

        if self.database_provider == "mysql":
            return (
                f"mysql+pymysql://{quote_plus(self.mysql_user)}:{quote_plus(self.mysql_password)}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
            )

        if self.database_provider == "azure_sql":
            if not all([self.azure_sql_server, self.azure_sql_database, self.azure_sql_user, self.azure_sql_password]):
                raise ValueError("Azure SQL requires server, database, user, and password to be set")
            trust = "yes" if self.azure_sql_trust_server_certificate else "no"
            params = f"driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate={trust}"
            return (
                f"mssql+pyodbc://{quote_plus(self.azure_sql_user)}:{quote_plus(self.azure_sql_password)}"
                f"@{self.azure_sql_server}:{self.azure_sql_port}/{self.azure_sql_database}?{params}"
            )

        raise ValueError(f"Unsupported database provider: {self.database_provider}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
