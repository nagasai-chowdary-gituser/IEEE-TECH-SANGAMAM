import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET(request: NextRequest) {
  const role = request.nextUrl.searchParams.get("role") === "admin" ? "admin" : "user";
  try {
    const response = await fetch(`${BACKEND}/api/v1/auth/google/url?role=${role}`, { cache: "no-store" });
    if (!response.ok) {
      return NextResponse.redirect(new URL("/?auth_error=google", request.url));
    }
    const payload = (await response.json()) as { url?: string };
    if (!payload.url) {
      return NextResponse.redirect(new URL("/?auth_error=google", request.url));
    }
    return NextResponse.redirect(payload.url);
  } catch {
    return NextResponse.redirect(new URL("/?auth_error=backend", request.url));
  }
}
