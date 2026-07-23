import type { MetaResponse, VizPayload } from "./types";
import type { ThemeName } from "./themes";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    return JSON.stringify(data);
  } catch {
    return res.statusText || "Request failed";
  }
}

export async function fetchMeta(): Promise<MetaResponse> {
  const res = await fetch(`${API_URL}/api/meta`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function sendChat(question: string): Promise<VizPayload> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function setServerTheme(theme: ThemeName): Promise<void> {
  const res = await fetch(`${API_URL}/api/theme`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ theme }),
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export function exportDownloadUrl(pathOrName: string): string {
  const name = pathOrName.split(/[/\\]/).pop() || pathOrName;
  return `${API_URL}/api/exports/${encodeURIComponent(name)}`;
}

export { API_URL };
