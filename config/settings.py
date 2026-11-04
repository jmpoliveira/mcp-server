"""Centralized application settings loaded from environment variables."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "development", "production"]
LogFormat = Literal["console", "json"]
_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


@dataclass(frozen=True, slots=True)
class _LoggingProfile:
    """Logging defaults of one environment. Explicit LOG_* variables override them."""

    level: str
    format: LogFormat
    file_enabled: bool


# One place that answers "how does logging behave in each environment?".
LOGGING_PROFILES: dict[Environment, _LoggingProfile] = {
    # Developer machine, run directly: readable terminal output plus a JSONL file.
    "local": _LoggingProfile(level="DEBUG", format="console", file_enabled=True),
    # Shared dev / docker compose: JSON on stdout only, ready for a log collector.
    "development": _LoggingProfile(level="DEBUG", format="json", file_enabled=False),
    # Production: JSON on stdout only, no debug noise.
    "production": _LoggingProfile(level="INFO", format="json", file_enabled=False),
}


@dataclass(frozen=True, slots=True)
class LoggingOptions:
    """Fully resolved logging configuration (profile defaults + overrides)."""

    level: str
    format: LogFormat
    file_enabled: bool
    file_path: Path
    access_log: bool
    max_message_chars: int
    max_stacktrace_chars: int
    queue_size: int
    service: str
    environment: str
    version: str


class Settings(BaseSettings):
    """Application settings. Values come from the environment or a .env file.

    ``mcp_host`` and ``mcp_port`` have no defaults on purpose: the service
    fails fast at startup if they are not configured.
    """

    # env_ignore_empty: "LOG_LEVEL=" in a .env file means "not set", not an empty string.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    mcp_server_name: str = "mcp-server"
    mcp_host: str
    mcp_port: int

    # Deployment environment. Defaults to the safest profile, so a forgotten
    # APP_ENV in a real deployment never produces debug logs or log files.
    app_env: Environment = "production"
    service_version: str = "0.1.0"

    # Logging. None means "use the default of the APP_ENV profile".
    log_level: str | None = None
    log_format: LogFormat | None = None
    log_file_enabled: bool | None = None
    log_file: Path = Path("logs/mcp-server.log.jsonl")
    log_access: bool = False  # uvicorn access log (one line per HTTP request)
    log_max_message_chars: int = Field(default=4000, ge=200, le=12000)
    log_max_stacktrace_chars: int = Field(default=6000, ge=200, le=12000)
    log_queue_size: int = Field(default=10000, ge=100)

    # OpenTelemetry (OTLP over HTTP). The endpoint is the base URL, for example
    # http://jaeger:4318; the traces path is appended by the telemetry module.
    otel_enabled: bool = False
    otel_service_name: str = "mcp-server"
    otel_exporter_otlp_endpoint: str | None = None

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        level = value.strip().upper()
        if level not in _LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {', '.join(_LOG_LEVELS)}")
        return level

    @model_validator(mode="after")
    def _require_endpoint_when_tracing(self) -> "Settings":
        if self.otel_enabled and not self.otel_exporter_otlp_endpoint:
            raise ValueError("OTEL_EXPORTER_OTLP_ENDPOINT is required when OTEL_ENABLED is true")
        return self

    @property
    def logging_options(self) -> LoggingOptions:
        """Resolve logging options: explicit LOG_* value > APP_ENV profile default."""
        profile = LOGGING_PROFILES[self.app_env]
        return LoggingOptions(
            level=self.log_level or profile.level,
            format=self.log_format or profile.format,
            file_enabled=(
                profile.file_enabled if self.log_file_enabled is None else self.log_file_enabled
            ),
            file_path=self.log_file,
            access_log=self.log_access,
            max_message_chars=self.log_max_message_chars,
            max_stacktrace_chars=self.log_max_stacktrace_chars,
            queue_size=self.log_queue_size,
            # Same identity as the traces, so logs and traces line up in Grafana.
            service=self.otel_service_name,
            environment=self.app_env,
            version=self.service_version,
        )


def get_settings() -> Settings:
    """Build settings from the current environment."""
    return Settings()  # pyright: ignore[reportCallIssue]  # values come from the environment
