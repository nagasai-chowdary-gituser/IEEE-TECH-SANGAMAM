"use client";

import { FileSearch, History, Landmark, PenLine, Plus, Settings, Shield } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useHealth } from "@/hooks/use-health";
import { clearSession, getSession } from "@/lib/session";
import { cn } from "@/lib/utils";

export function AppSidebar() {
  const pathname = usePathname();
  const health = useHealth();
  const apiOk = health.data?.status === "ok";
  const compliance = pathname.startsWith("/compliance");
  const signatures = pathname.startsWith("/signatures");
  const nav = compliance
    ? [
        { href: "/compliance", label: "New assessment", icon: Plus },
        { href: "/compliance/history", label: "Compliance history", icon: History },
        { href: "/", label: "Product home", icon: Landmark },
      ]
    : signatures
      ? [
          { href: "/signatures", label: "New certificate analysis", icon: Plus },
          { href: "/signatures/history", label: "Certificate history", icon: History },
          { href: "/signatures/references", label: "Add reference signature", icon: PenLine },
          { href: "/", label: "Product home", icon: Landmark },
        ]
      : [
          { href: "/forensics", label: "New analysis", icon: Plus },
          { href: "/history", label: "Analysis history", icon: History },
          { href: "/signatures/references", label: "Add reference signature", icon: PenLine },
          { href: "/", label: "Product home", icon: Landmark },
        ];

  const subtitle = compliance ? "Bid compliance" : signatures ? "Certificate analyzer" : "Document forensics";

  return (
    <aside className="flex w-full shrink-0 flex-col border-b bg-card lg:h-screen lg:w-60 lg:border-b-0 lg:border-r">
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded border border-foreground/15 bg-foreground text-background">
          <Shield className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold tracking-tight">DocuVerify</p>
          <p className="text-[11px] text-muted-foreground">{subtitle}</p>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-1 px-3 pb-4">
        {nav.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href ||
            (item.href === "/history" && pathname.startsWith("/history")) ||
            (item.href === "/forensics" && (pathname.startsWith("/forensics") || pathname.startsWith("/analysis"))) ||
            (item.href === "/compliance" && pathname.startsWith("/compliance") && pathname !== "/compliance/history") ||
            (item.href === "/compliance/history" && pathname.startsWith("/compliance/history")) ||
            (item.href === "/signatures" && pathname.startsWith("/signatures") && !pathname.startsWith("/signatures/history") && !pathname.startsWith("/signatures/references")) ||
            (item.href === "/signatures/history" && pathname.startsWith("/signatures/history")) ||
            (item.href === "/signatures/references" && pathname.startsWith("/signatures/references"));
          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                active ? "bg-muted font-medium text-foreground" : "text-muted-foreground hover:bg-muted/70 hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
        <div className="mt-2 flex items-center justify-between rounded-md px-3 py-2 text-sm text-muted-foreground">
          <span className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Settings
          </span>
          <span className="text-[10px] uppercase tracking-wide">Soon</span>
        </div>
        <div className="mt-2 rounded-md border px-3 py-2">
          <div className="mb-1 flex items-center gap-2 text-sm text-foreground">
            <FileSearch className="h-4 w-4" />
            System Status
          </div>
          <p className="text-[11px] text-muted-foreground">
            {health.isLoading
              ? "Checking API…"
              : health.isError
                ? "DocuVerify API unreachable. Keep the backend running, then refresh."
                : `${health.data?.service ?? "API"} · ${health.data?.database ?? "unknown"} db`}
          </p>
          <div className="mt-2 flex items-center gap-2 text-[11px]">
            <span className={cn("h-1.5 w-1.5 rounded-full", health.isError ? "bg-destructive" : apiOk ? "bg-success" : "bg-warning")} />
            {health.isError ? "Offline" : apiOk ? "Operational" : "Degraded"}
          </div>
        </div>
      </nav>
      <p className="hidden px-5 pb-4 text-[11px] text-muted-foreground lg:block">
        {getSession() ? `${getSession()?.role} · ` : ""}
        Decision support · not legal proof
        {getSession() ? (
          <>
            {" · "}
            <button
              type="button"
              className="underline-offset-4 hover:underline"
              onClick={() => {
                clearSession();
                window.location.href = "/";
              }}
            >
              Sign out
            </button>
          </>
        ) : null}
      </p>
    </aside>
  );
}
