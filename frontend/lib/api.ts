/** Same-origin proxy by default; an explicit URL supports separate hosting. */
const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "/backend").replace(
  /\/$/,
  "",
);
const TOKEN_KEY = "core_client_token_v1";
let browserToken: string | undefined;

function clientToken(): string {
  if (browserToken) return browserToken;
  try {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (saved && /^[a-f0-9]{64}$/.test(saved)) browserToken = saved;
  } catch {
    /* A temporary token still supports this tab when storage is disabled. */
  }
  if (!browserToken) {
    browserToken = Array.from(
      crypto.getRandomValues(new Uint8Array(32)),
      (byte) => byte.toString(16).padStart(2, "0"),
    ).join("");
    try {
      localStorage.setItem(TOKEN_KEY, browserToken);
    } catch {
      /* Storage unavailable. */
    }
  }
  return browserToken;
}

async function checked(response: Response): Promise<Response> {
  if (!response.ok) {
    let detail = `Server returned HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* Non-JSON error from a proxy. */
    }
    throw new Error(detail);
  }
  return response;
}

export async function sendChatMessage(
  message: string,
  sessionId: string,
  signal?: AbortSignal,
  requestId?: string,
): Promise<Response> {
  return checked(
    await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Client-Token": clientToken(),
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        request_id: requestId,
      }),
      signal,
    }),
  );
}

export async function cancelChatRequest(
  sessionId: string,
  requestId: string,
): Promise<void> {
  await checked(
    await fetch(
      `${API_BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}/cancel`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Client-Token": clientToken(),
        },
        body: JSON.stringify({ request_id: requestId }),
        signal: AbortSignal.timeout(10_000),
      },
    ),
  );
}

export async function deleteChatSession(sessionId: string): Promise<void> {
  await checked(
    await fetch(
      `${API_BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}`,
      {
        method: "DELETE",
        headers: { "X-Client-Token": clientToken() },
      },
    ),
  );
}

export async function checkHealth(
  signal?: AbortSignal,
): Promise<{ status: string; model: string }> {
  return (
    await checked(
      await fetch(`${API_BASE_URL}/health`, { signal, cache: "no-store" }),
    )
  ).json();
}

export { API_BASE_URL };
