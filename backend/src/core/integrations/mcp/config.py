"""Local MCP executable configuration and restricted child-process environments."""
import os
import shutil
import sys

from core.config import settings
from core.integrations.llm import configured


def get_mcp_server_configs(owner: str | None = None) -> dict:
    # Pass only process essentials to third-party servers, not model/provider credentials.
    env = {key: value for key, value in os.environ.items() if key in {
        "PATH", "HOME", "USER", "LANG", "LC_ALL", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR",
        "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR",
    }}
    configs = {"time": {"transport": "stdio", "command": sys.executable, "args": ["-m", "mcp_server_time"], "env": env}}
    npx = shutil.which("npx")

    def add(name, binary, package, args=(), extra_env=None):
        executable = shutil.which(binary)
        if executable or npx:
            configs[name] = {
                "transport": "stdio", "command": executable or npx,
                # Never silently download and execute packages during a chat request.
                "args": list(args) if executable else ["--no", package, *args],
                "env": {**env, **(extra_env or {})},
            }

    add("weather", "mcp-server-weather", "@h1deya/mcp-server-weather")
    add("research", "researchmcp", "researchmcp", ("arxiv",))
    add("sequential-thinking", "mcp-server-sequential-thinking", "@modelcontextprotocol/server-sequential-thinking")
    if configured(settings.GOOGLE_MAPS_API_KEY):
        add("google-maps", "mcp-server-google-maps", "@modelcontextprotocol/server-google-maps", extra_env={"GOOGLE_MAPS_API_KEY": settings.GOOGLE_MAPS_API_KEY})
    # MiniMax must be installed explicitly, like the other MCP executables.
    if configured(settings.MINIMAX_API_KEY) and settings.MINIMAX_API_HOST:
        executable = shutil.which("minimax-mcp")
        if executable:
            configs["minimax"] = {
                "transport": "stdio", "command": executable, "args": [],
                "env": {**env, "MINIMAX_API_KEY": settings.MINIMAX_API_KEY, "MINIMAX_API_HOST": settings.MINIMAX_API_HOST},
            }
    if owner:
        from core.integrations.elevenlabs import ElevenLabsAuth, MCP_URL, enabled
        if enabled():
            configs["elevenlabs"] = {
                "transport": "streamable_http", "url": MCP_URL,
                "auth": ElevenLabsAuth(owner), "timeout": 20, "sse_read_timeout": 30,
            }
    return configs
