from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GOOGLE_API_KEY: str = "placeholder"
    GEMINI_MODEL: str = "gemini-2.0-flash"
    MCP_SERVER_COMMAND: str = "python"
    MCP_SERVER_SCRIPT: str = "src/mcp_server/server.py"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
