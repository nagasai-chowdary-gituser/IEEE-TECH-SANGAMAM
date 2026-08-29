"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { getSessionMe } from "@/lib/api";
import { persistSession } from "@/lib/session";

export function AuthCallback() {
  const params = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      router.replace("/?auth_error=google");
      return;
    }
    void getSessionMe(token)
      .then((session) => {
        persistSession(session);
        router.replace("/");
      })
      .catch(() => router.replace("/?auth_error=google"));
  }, [params, router]);

  return <p className="px-6 py-16 text-sm text-muted-foreground">Finishing Google sign-in…</p>;
}
