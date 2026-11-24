from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Source checkouts use the shared repository .env and data directory, regardless
# of whether uv is launched from the root or backend/. Installed wheels use cwd.
_PROJECT_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = _PROJECT_DIR.parent if (_PROJECT_DIR.parent / "frontend/package.json").is_file() else Path.cwd()


class Settings(BaseSettings):
    GOOGLE_API_KEY: str = "placeholder"
    OPENROUTER_API_KEY: str = "placeholder"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "nvidia/nemotron-3.5-lightning:free"
    GOOGLE_MODEL: str = "gemini-2.5-flash"
    DATABASE_PATH: str = str(REPOSITORY_ROOT / ".data/sessions.sqlite3")
    DATABASE_URL: str = ""
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    SESSION_TTL_SECONDS: int = Field(default=604800, ge=60)
    MAX_SESSIONS: int = Field(default=1000, ge=1)
    MAX_HISTORY_TURNS: int = Field(default=20, ge=1, le=100)
    REQUESTS_PER_MINUTE: int = Field(default=30, ge=1)
    GLOBAL_REQUESTS_PER_MINUTE: int = Field(default=120, ge=1)
    MAX_REQUEST_BYTES: int = Field(default=65536, ge=1024)
    MAX_HISTORY_BYTES: int = Field(default=250000, ge=20000)
    CHAT_TIMEOUT_SECONDS: int = Field(default=120, ge=1)
    TOOL_TIMEOUT_SECONDS: int = Field(default=30, ge=1)
    DISCOVERY_TIMEOUT_SECONDS: int = Field(default=15, ge=1)
    MAX_TOOL_ROUNDS: int = Field(default=4, ge=1, le=10)
    MCP_CACHE_SECONDS: int = Field(default=300, ge=0)
    # Optional deployment-wide protection, intended for a trusted reverse proxy.
    CHAT_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    MINIMAX_API_KEY: str = ""
    MINIMAX_API_HOST: str = ""
    ELEVENLABS_CONNECTOR: str = ""
    ELEVENLABS_SHARED_ACCOUNT: bool = False
    ELEVENLABS_OWNER_SETUP_HASH: str = ""
    ELEVENLABS_DEMO_PER_VISITOR: int = Field(default=5, ge=1, le=1000)
    ELEVENLABS_DEMO_GLOBAL: int = Field(default=20, ge=1, le=10000)
    ELEVENLABS_TTS_DEMO_PER_VISITOR: int = Field(default=5, ge=1, le=1000)
    ELEVENLABS_TTS_DEMO_GLOBAL: int = Field(default=20, ge=1, le=10000)
    CORE_PUBLIC_URL: str = ""

    model_config = SettingsConfigDict(env_file=REPOSITORY_ROOT / ".env", extra="ignore")

    @field_validator("DATABASE_PATH", mode="after")
    @classmethod
    def resolve_database_path(cls, value: str) -> str:
        path = Path(value).expanduser()
        return str(path if path.is_absolute() else REPOSITORY_ROOT / path)

    @field_validator("*", mode="before")
    @classmethod
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            v = v.strip().strip("'").strip('"').strip()
            if v.startswith("Bearer "):
                v = v[7:].strip()
        return v

settings = Settings()
