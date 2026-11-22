# Core — Multi-Agent Chatbot

Core stands for **Collaborative Orchestration & Reasoning Engine**.

A chat application using LangGraph orchestration, MCP tools, a FastAPI streaming API, and a Next.js interface.

Deploy both application services on Vercel with Neon PostgreSQL using the
[Vercel deployment guide](docs/deploy-vercel.md).

## Repository layout

```text
backend/                 Python project, dependency lock, tests, and Dockerfile
  src/core/
    main.py              Application startup and ASGI entry point
    api/                 HTTP routes, validation, auth dependencies, and SSE
    graph/               Agent state, routing, and execution nodes
    integrations/        Model providers and MCP clients
    storage/             SQLite sessions, retention, and transport-free errors
frontend/                Next.js app, components, hooks, utilities, and shared types
scripts/                 Explicit manual/live integration checks
docs/                   Current architecture and archived plans
```

The root `.env` is shared configuration for local development and Compose. The
backend resolves relative database paths from the repository root, so changing the
working directory does not create a second session database.

## How it works

```text
Next.js → same-origin /backend proxy → FastAPI → supervisor
                                               ├─ responder → streamed answer
                                               └─ tool agent → supervisor → … → responder
```

The supervisor uses word-boundary matching and short follow-up context to route requests. The tool agent discovers tools from independently handled MCP servers, lets the configured model select tools, and can use results in later rounds. Execution stops after a configurable round limit. The responder streams the final answer through Server-Sent Events.

Tool servers include time, weather, arXiv research, and sequential thinking. Google Maps and MiniMax are optional. Routing is heuristic; it does not understand every paraphrase or language.

The browser stores thread display history in `localStorage`. The backend stores model conversation context in SQLite locally, or PostgreSQL when `DATABASE_URL` is set, with atomic request leases to reject overlapping requests for the same thread. Successful turns are committed; failed and cancelled turns are rolled back. History is bounded by turns and bytes, and inactive sessions expire after seven days by default. After expiration, an old browser thread starts fresh backend context.

Each browser generates a random ownership token and sends it in `X-Client-Token`; the server stores only its hash. This isolates anonymous browser sessions. It is not a user account or login system. Keep the browser token if you want continued access to its threads. For a private deployment, put the app behind an authenticated gateway; the optional `CHAT_API_KEY` can protect direct API access when injected by that gateway. Never put this secret in `NEXT_PUBLIC_*` variables.

## Stack

- Python 3.12+, FastAPI, LangGraph, LangChain MCP adapters, SQLite/PostgreSQL, uv
- Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, Base UI
- OpenRouter, or Google Gemini when OpenRouter is not configured

Provider selection happens before the request; it does not automatically retry a failed OpenRouter request against Gemini. `GOOGLE_MODEL` controls the Gemini model when `LLM_MODEL` is an OpenRouter model name.

## Run locally

Prerequisites: Python 3.12+, Node.js 22.18+, npm, and uv.

1. Copy `.env.example` to `.env` and configure a provider key.
2. Install dependencies:

   ```sh
   uv sync --project backend --frozen
   npm ci --prefix frontend
   ```

3. Start the backend from the repository root:

   ```sh
   uv run --project backend uvicorn core.main:app --reload --port 8000
   ```

4. Start the frontend in a second terminal:

   ```sh
   cd frontend
   npm run dev
   ```

Open http://localhost:3000. The frontend proxies `/backend/*` to `http://127.0.0.1:8000` by default. To change the target, set `API_PROXY_URL` before starting development or building. For separately hosted frontends, set `NEXT_PUBLIC_API_URL` at build time and add the exact frontend origin to the backend's JSON `ALLOWED_ORIGINS` list. There is no hardcoded production API fallback.

Google Fonts are downloaded during the Next.js build, so that step needs internet access.

### Install MCP tools

The Python time server is included in `uv sync`. Install the Node tools explicitly:

```sh
npm install -g @h1deya/mcp-server-weather@0.1.3 researchmcp@1.0.2 @modelcontextprotocol/server-sequential-thinking@2026.7.4
```

Missing or failing servers do not disable healthy servers. Discovery is cached for five minutes by default; restarting the backend refreshes it immediately. Runtime requests do not automatically download packages. Install optional Google Maps / MiniMax executables and configure their variables to enable them. The NOAA weather server's geographic coverage depends on its upstream service.

## API

- `GET /health`: process reachability and selected model; does not probe providers or MCP servers.
- `POST /api/chat`: `{ "message": "Hello", "session_id": "thread-id" }`; requires `X-Client-Token` (32–128 characters). Omit `session_id` to generate one; the `done` event returns it.
- `POST /api/sessions/{session_id}/cancel`: `{ "request_id": "UUID" }`; cancels the matching owned request. Supply that UUID as `request_id` in the original chat request. The UI waits for cancellation acknowledgement before accepting another message, and workers stop cancelled graph execution even when a hosting proxy retains the stream.
- `DELETE /api/sessions/{session_id}`: deletes backend context owned by the browser token. Busy sessions return 409.

SSE events: `agent_state`, `tool_call`, `tool_result`, `token`, `error`, and `done`. An error is terminal and does not emit `done`. Tokens are normalized to text before streaming. Provider errors are logged server-side without returning internal exception details to the browser.

Request validation rejects empty/blank messages, messages over 12,000 characters, and bodies over 64 KiB. Per-source-IP and global per-minute limits apply to accepted chat requests; limits and leases are shared by workers through SQLite. Set ASGI's trusted proxy list explicitly when deploying behind a reverse proxy. Clients behind the same unconfigured proxy share its IP budget. Configure all timeouts together if you raise the default 120-second backend timeout: the frontend proxy and browser currently allow 150 seconds.

## Tests

Offline regression suite, with no provider credentials or network services required:

```sh
uv run --project backend python -m unittest discover -s backend/tests -v
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

Backend coverage includes streaming through the real graph with a fake model, session persistence, ownership, concurrent claims, rollback, expiration, stale leases, validation, rate limits, timeouts, routing, multi-round tools, and isolated discovery failures. Frontend tests cover fragmented SSE frames, Unicode, cancellation, malformed/oversized events, interrupted streams, and stored history validation.

Optional live checks (these may call providers or start installed MCP processes):

```sh
uv run --project backend python scripts/check_llm.py
uv run --project backend python scripts/check_mcp.py
```

## Docker

```sh
docker compose build
docker compose up -d
```

Frontend: port 3000. Backend: port 8000. Compose uses the internal backend hostname for the frontend proxy and a named volume for SQLite persistence. Both runtime images use non-root users. `.env` and local session data are excluded from build contexts. Removing containers preserves history; removing the named data volume deletes it.

SQLite supports multiple workers on one host with a shared local database file. Multiple independently hosted backend replicas need a shared database and coordination strategy rather than separate SQLite files. Add user authentication at the gateway before offering private user accounts.

See [current architecture](docs/architecture.md) for module responsibilities. Original plans are retained in [docs/archive](docs/archive).
