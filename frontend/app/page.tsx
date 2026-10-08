"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { LoginLanding } from "@/components/auth/login-landing";
import { ProductHome } from "@/components/product/product-home";
import { getSession, type AuthSession } from "@/lib/session";

function HomeSwitch() {
  const params = useSearchParams();
  const router = useRouter();
  const [session, setSession] = useState<AuthSession | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const current = getSession();
    if (current?.role === "admin") {
      router.replace("/admin");
      return;
    }
    setSession(current);
    setReady(true);
  }, [router]);

  if (!ready) {
    return <p className="px-6 py-16 text-sm text-muted-foreground">Loading…</p>;
  }
  if (!session) {
    return <LoginLanding authError={params.get("auth_error")} />;
  }
  return <ProductHome />;
}

export default function HomePage() {
  return (
    <Suspense fallback={<p className="px-6 py-16 text-sm text-muted-foreground">Loading…</p>}>
      <HomeSwitch />
    </Suspense>
  );
}
