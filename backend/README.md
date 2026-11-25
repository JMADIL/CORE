# Core backend

Python package: `src/core`. Application entry point: `core.main:app`.

From this directory:

```sh
uv sync --frozen
uv run uvicorn core.main:app --reload --port 8000
uv run python -m unittest discover -s tests -v
```

The installed `core-api` command starts the production server and respects `PORT`.
Source checkouts read the repository root `.env`; relative SQLite paths also resolve
from the repository root. Docker receives configuration through environment variables.

See the [project README](../README.md) for configuration, tool installation, Docker,
and API details, and [architecture](../README.md#architecture) for module responsibilities.

Owner-only ElevenLabs authorization is available with `uv run core-elevenlabs-setup`.
See the [ElevenLabs guide](../README.md#elevenlabs) before running setup.
