import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  const error = request.nextUrl.searchParams.get("error");
  if (error || !code || !state) {
    return NextResponse.redirect(new URL("/?auth_error=google", request.url));
  }
  try {
    const complete = new URL(`${BACKEND}/api/v1/auth/google/complete`);
    complete.searchParams.set("code", code);
    complete.searchParams.set("state", state);
    const response = await fetch(complete, { cache: "no-store" });
    if (!response.ok) {
      return NextResponse.redirect(new URL("/?auth_error=google", request.url));
    }
    const payload = (await response.json()) as { token?: string };
    if (!payload.token) {
      return NextResponse.redirect(new URL("/?auth_error=google", request.url));
    }
    const dest = new URL("/auth/callback", request.url);
    dest.searchParams.set("token", payload.token);
    return NextResponse.redirect(dest);
  } catch {
    return NextResponse.redirect(new URL("/?auth_error=backend", request.url));
  }
}
