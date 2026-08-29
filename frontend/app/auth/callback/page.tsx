import { Suspense } from "react";

import { AuthCallback } from "@/components/auth/auth-callback";

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<p className="px-6 py-16 text-sm text-muted-foreground">Finishing Google sign-in…</p>}>
      <AuthCallback />
    </Suspense>
  );
}
