"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { getSession } from "@/lib/session";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const publicPath = pathname === "/" || pathname.startsWith("/auth/callback");

  useEffect(() => {
    if (publicPath) return;
    if (!getSession()) router.replace("/");
  }, [pathname, publicPath, router]);

  if (!publicPath && typeof window !== "undefined" && !getSession()) {
    return <p className="px-6 py-10 text-sm text-muted-foreground">Redirecting to sign-in…</p>;
  }
  return <>{children}</>;
}
