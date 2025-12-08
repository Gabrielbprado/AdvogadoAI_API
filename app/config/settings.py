"""Application settings and configuration helpers."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed settings loaded from the environment or .env files."""

    app_name: str = Field(default="LawerAI")
    environment: str = Field(default="development")
    storage_dir: Path = Field(default=Path("data/uploads"))
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
    cors_allowed_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"],
        validation_alias="CORS_ALLOWED_ORIGINS",
    )

    model_config = SettingsConfigDict(env_file=".env", env_prefix="LAWERAI_", case_sensitive=False)

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
