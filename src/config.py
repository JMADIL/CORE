from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GOOGLE_API_KEY: str = "placeholder"
    OPENROUTER_API_KEY: str = "placeholder"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"
    GOOGLE_MAPS_API_KEY: str = ""
    MINIMAX_API_KEY: str = ""
    MINIMAX_API_HOST: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("*", mode="before")
    @classmethod
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            v = v.strip().strip("'").strip('"').strip()
            if v.startswith("Bearer "):
                v = v[7:].strip()
        return v

settings = Settings()
