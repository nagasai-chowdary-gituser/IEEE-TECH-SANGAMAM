"use client";

import Link from "next/link";
import { Shield } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { clearSession, getSession } from "@/lib/session";

export function ProductTopbar() {
  const router = useRouter();
  const session = typeof window === "undefined" ? null : getSession();
  return (
    <header className="border-b bg-card/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded border border-foreground/15 bg-foreground text-background">
            <Shield className="h-3.5 w-3.5" />
          </span>
          <span className="text-sm font-semibold tracking-tight">DocuVerify</span>
        </Link>
        <div className="flex items-center gap-3">
          {session ? (
            <>
              <p className="hidden text-xs text-muted-foreground sm:block">
                {session.name || session.email} · {session.role}
              </p>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  clearSession();
                  router.replace("/");
                  router.refresh();
                }}
              >
                Sign out
              </Button>
            </>
          ) : (
            <p className="hidden text-xs text-muted-foreground sm:block">Document intelligence · compliance decision support</p>
          )}
        </div>
      </div>
    </header>
  );
}
