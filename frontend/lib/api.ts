/**
 * API client for communicating with the FastAPI backend.
 * Handles SSE streaming connections for real-time chat.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000");

/**
 * Send a chat message to the backend and return the raw Response
 * for SSE stream consumption.
 */
export async function sendChatMessage(
  message: string,
  sessionId: string,
  signal?: AbortSignal
): Promise<Response> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
    }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Server returned HTTP ${response.status}`);
  }

  return response;
}

/**
 * Health check — verifies the backend API is reachable.
 */
export async function checkHealth(): Promise<{
  status: string;
  model: string;
}> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: HTTP ${response.status}`);
  }
  return response.json();
}

export { API_BASE_URL };
