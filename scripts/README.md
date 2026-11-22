# Manual integration checks

Run from the repository root after `uv sync --project backend --frozen`:

```sh
uv run --project backend python scripts/check_llm.py
uv run --project backend python scripts/check_mcp.py
```

The model check uses the configured provider and may incur usage charges. The MCP
check starts installed tool processes. Neither runs during the offline test suite.

`manual/test_stream.html` is an explicit browser streaming diagnostic. To use it,
start the backend on port 8000 and serve this directory on an allowed frontend
origin, for example `python -m http.server 3000 --directory scripts/manual` while
the Next.js dev server is stopped. Open `http://localhost:3000/test_stream.html` and
click Run. It is not shipped in the application's public assets.
