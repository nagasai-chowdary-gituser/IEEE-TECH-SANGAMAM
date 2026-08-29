"use client";

import { useEffect, useState } from "react";
import { Shield } from "lucide-react";

import { Button } from "@/components/ui/button";
import { loginWithPassword } from "@/lib/api";
import { persistSession, type SessionRole } from "@/lib/session";
import { cn } from "@/lib/utils";

export function LoginLanding({ authError }: { authError: string | null }) {
  const [role, setRole] = useState<SessionRole>("user");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(
    authError === "backend"
      ? "The API is not running. Start uvicorn on port 8000, then try again."
      : authError
        ? "Google sign-in was cancelled or failed."
        : null,
  );
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (authError === "backend") {
      setError("The API is not running. Start uvicorn on port 8000, then try again.");
    } else if (authError) {
      setError("Google sign-in was cancelled or failed.");
    }
  }, [authError]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const session = await loginWithPassword(username.trim(), password, role);
      persistSession(session);
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
      setPending(false);
    }
  }

  function googleHref() {
    return `/api/auth/google?role=${role}`;
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-3.5rem)] max-w-md flex-col justify-center px-6 py-12">
      <div className="mb-8 flex items-center gap-2.5">
        <span className="flex h-9 w-9 items-center justify-center rounded border border-foreground/15 bg-foreground text-background">
          <Shield className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-semibold tracking-tight">DocuVerify</p>
          <p className="text-[11px] text-muted-foreground">Sign in to continue</p>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-2 rounded-md border p-1">
        {(["user", "admin"] as const).map((item) => (
          <button
            key={item}
            type="button"
            className={cn(
              "h-9 rounded text-sm font-medium capitalize",
              role === item ? "bg-foreground text-background" : "text-muted-foreground hover:bg-muted",
            )}
            onClick={() => setRole(item)}
          >
            {item}
          </button>
        ))}
      </div>

      <form className="space-y-3" onSubmit={(event) => void onSubmit(event)}>
        <label className="block text-sm">
          <span className="text-muted-foreground">Username</span>
          <input
            className="mt-1 h-10 w-full rounded-md border bg-background px-3 text-sm"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </label>
        <label className="block text-sm">
          <span className="text-muted-foreground">Password</span>
          <input
            className="mt-1 h-10 w-full rounded-md border bg-background px-3 text-sm"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button type="submit" className="w-full" disabled={pending}>
          {pending ? "Signing in…" : `Sign in as ${role}`}
        </Button>
      </form>

      <div className="my-6 flex items-center gap-3 text-[11px] uppercase tracking-wide text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        or
        <span className="h-px flex-1 bg-border" />
      </div>

      <a
        href={googleHref()}
        className="inline-flex h-10 items-center justify-center rounded-md border bg-background text-sm font-medium hover:bg-muted"
      >
        Continue with Google ({role})
      </a>
      <p className="mt-4 text-xs text-muted-foreground">
        Local demo accounts: user / user123 and admin / admin123. Google uses the role selected above.
      </p>
    </div>
  );
}
