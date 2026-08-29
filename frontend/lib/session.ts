const SESSION_KEY = "docuverify.session";
const DEMO_KEY = "docuverify.demo-token";

export type SessionRole = "user" | "admin";

export interface AuthSession {
  token: string;
  role: SessionRole;
  name: string;
  email: string;
  method: "password" | "google";
}

let memory: AuthSession | null = null;

export function getSession(): AuthSession | null {
  if (memory) return memory;
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AuthSession;
    if (!parsed?.token) return null;
    memory = parsed;
    return parsed;
  } catch {
    return null;
  }
}

export function persistSession(session: AuthSession): void {
  memory = session;
  if (typeof window !== "undefined") {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  }
}

export function clearSession(): void {
  memory = null;
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(SESSION_KEY);
  }
}

export function getAccessToken(): string {
  return getSession()?.token ?? "";
}

export function getDemoToken(): string {
  if (typeof window !== "undefined") {
    const stored = sessionStorage.getItem(DEMO_KEY)?.trim();
    if (stored) return stored;
  }
  return (process.env.NEXT_PUBLIC_DEMO_TOKEN ?? "").trim();
}

export function persistDemoToken(token?: string): void {
  const value = (token ?? getDemoToken()).trim();
  if (!value || typeof window === "undefined") return;
  sessionStorage.setItem(DEMO_KEY, value);
}

export function authHeaders(headers?: HeadersInit): Headers {
  const merged = new Headers(headers);
  const session = getAccessToken();
  if (session) merged.set("Authorization", `Bearer ${session}`);
  const demo = getDemoToken();
  if (demo) merged.set("X-Demo-Token", demo);
  return merged;
}
