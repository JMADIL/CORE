# Multi-Agent Chatbot System

A production-grade, portfolio-quality multi-agent chatbot system featuring LangGraph-based orchestration, dynamic tool discovery via the Model Context Protocol (MCP), real-time FastAPI SSE streaming, and a polished Next.js frontend built with an editorial-minimalist design language.

---

## Key Features

- **Supervisor Orchestration Pattern**: Orchestrates complex tasks using a supervisor agent that dynamically routes queries between a specialized tool agent node and standard responder nodes.
- **Model Context Protocol (MCP)**: Dynamic tool discovery and execution from external servers (Weather, Time, Research, Puppeteer, Sequential Thinking) without hardcoded tool definitions.
- **Real-Time Token Streaming**: Server-Sent Events (SSE) stream LLM tokens, active agent states, tool calls, and results.
- **Editorial Minimalist UI**: Restrained typography, generous whitespace, smooth micro-animations, collapsible thought processes, and real-time activity indicators inspired by [tingyan.me](https://www.tingyan.me/).
- **Dynamic Gemini Fallback**: Smart model name mapping that gracefully falls back to native Gemini models when OpenRouter is not used.
- **Leak-Free SSE Hook**: Clean React client hook using `AbortController` to prevent SSE request leakage and state corruption during chat resets.

---

## System Architecture

```
┌──────────┐    HTTP POST     ┌──────────┐    invoke()    ┌────────────┐
│          │ ──────────────▶  │          │ ────────────▶  │            │
│  Next.js │    SSE stream    │  FastAPI  │  astream()    │  LangGraph │
│  Client  │ ◀──────────────  │  Server   │ ◀────────────  │  StateGraph│
│          │                  │          │                │            │
└──────────┘                  └──────────┘                └─────┬──────┘
                                                                │
                                                    ┌───────────┴──────────┐
                                                    │                      │
                                              ┌─────▼─────┐        ┌──────▼─────┐
                                              │ Supervisor │        │ Tool Agent │
                                              │   Node     │        │   Node     │
                                              └─────┬──────┘        └──────┬─────┘
                                                    │                      │
                                                    ▼                      ▼
                                              ┌───────────┐        ┌────────────┐
                                              │  Gemini    │        │ MCP Server │
                                              │  (route)   │        │  (stdio)   │
                                              └───────────┘        └────────────┘
```

For more detailed architectural documentation, please see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI**: Lightweight ASGI API framework.
- **LangGraph**: Framework for building stateful, multi-agent applications.
- **langchain-google-genai** & **langchain-openai**: LLM integrations.
- **langchain-mcp-adapters**: Adapter mapping MCP tools to LangChain tools.
- **mcp**: Model Context Protocol SDK.
- **uv**: Ultra-fast Python package resolver.

### Frontend
- **Next.js 15+** with App Router.
- **React 19**
- **Tailwind CSS v4**
- **Framer Motion**: Smooth animations.
- **React Markdown** & **remarkGfm**: Beautiful rich-text formatting.

---

## Local Setup

### 1. Prerequisites
- **Python 3.11+** installed.
- **Node.js 18+** & **npm** installed.
- **uv** (Python package installer) installed:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
# OpenRouter Configuration (Optional but recommended)
OPENROUTER_API_KEY=your-openrouter-key
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free

# Native Google Gemini Configuration (Fallback)
GOOGLE_API_KEY=your-google-api-key
```

### 3. Backend Setup
1. Sync dependencies and build the virtual environment using `uv`:
   ```bash
   uv sync
   ```
2. Start the FastAPI development server:
   ```bash
   PYTHONPATH=. uv run uvicorn src.api.app:app --reload --port 8000
   ```
   The backend server will start on [http://localhost:8000](http://localhost:8000).

### 4. Frontend Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install frontend dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   The user interface will be accessible at [http://localhost:3000](http://localhost:3000).

---

## Testing

To run the automated test suite, execute the following from the root directory:

```bash
# Test Gemini LLM integration
PYTHONPATH=. uv run python tests/test_llm.py

# Test LangGraph node orchestration
PYTHONPATH=. uv run python tests/test_graph.py

# Test MCP server tool discovery
PYTHONPATH=. uv run python tests/test_mcp.py

# Test API endpoints and SSE stream
PYTHONPATH=. uv run python tests/test_api.py
```
