from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GOOGLE_API_KEY: str = "placeholder"
    OPENROUTER_API_KEY: str = "placeholder"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    GEMINI_MODEL: str = "google/gemini-2.0-flash-exp:free"
    GOOGLE_MAPS_API_KEY: str = ""
    MINIMAX_API_KEY: str = ""
    MCP_SERVER_COMMAND: str = "python"
    MCP_SERVER_SCRIPT: str = "src/mcp_server/server.py"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
