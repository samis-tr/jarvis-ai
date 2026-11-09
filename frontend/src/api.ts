// Session token: passed once in the URL by the desktop launcher, then kept in sessionStorage.
const params = new URLSearchParams(location.search);
const urlToken = params.get("token");
if (urlToken) {
  try { sessionStorage.setItem("jarvis_token", urlToken); } catch { /* ignore */ }
  history.replaceState(null, "", location.pathname);
}
let stored = "";
try { stored = sessionStorage.getItem("jarvis_token") || ""; } catch { /* ignore */ }
export const TOKEN = urlToken || stored;

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T = unknown>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(path, {
    method: opts.method || (opts.body !== undefined ? "POST" : "GET"),
    headers: { "Content-Type": "application/json", "X-Jarvis-Token": TOKEN },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch { /* ignore */ }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

export const audioUrl = (id: string) => `/api/tts/${id}?token=${encodeURIComponent(TOKEN)}`;

export type JarvisEvent = { type: string; [k: string]: any };

export function connectEvents(onEvent: (e: JarvisEvent) => void, onConn: (up: boolean) => void): () => void {
  let ws: WebSocket | null = null;
  let closed = false;
  let retry = 500;
  const open = () => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws?token=${encodeURIComponent(TOKEN)}`);
    ws.onopen = () => { retry = 500; onConn(true); };
    ws.onmessage = (m) => { try { onEvent(JSON.parse(m.data)); } catch { /* ignore */ } };
    ws.onclose = () => {
      onConn(false);
      if (!closed) setTimeout(open, (retry = Math.min(retry * 2, 8000)));
    };
  };
  open();
  return () => { closed = true; ws?.close(); };
}
