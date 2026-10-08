"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileSearch, Landmark, PenLine, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ApiError, getAdminOverview, removeAiBlock } from "@/lib/api";
import { getSession } from "@/lib/session";
import { formatTimestamp } from "@/lib/utils";
import type { AiUsageWindow, ModuleStats, RecentActivity } from "@/types/admin";

const MODULE_LINKS: Record<RecentActivity["module"], (id: string) => string> = {
  forensics: (id) => `/analysis/${id}`,
  compliance: (id) => `/compliance/${id}`,
  certificate: (id) => `/signatures/${id}`,
};

const MODULE_LABELS: Record<RecentActivity["module"], string> = {
  forensics: "Forensics",
  compliance: "Compliance",
  certificate: "Certificate",
};

function outcomeVariant(value: string | null) {
  if (!value) return "muted" as const;
  if (["LOW", "COMPLIANT", "NO_MEANINGFUL_TAMPER_EVIDENCE", "LOW_MANIPULATION_RISK"].includes(value)) return "success" as const;
  if (["MODERATE", "REVIEW_REQUIRED", "MODERATE_MANIPULATION_RISK", "INCONCLUSIVE"].includes(value)) return "warning" as const;
  if (/HIGH|ELEVATED|FAIL/.test(value)) return "danger" as const;
  return "muted" as const;
}

function label(value: string) {
  return value.replaceAll("_", " ").toLowerCase();
}

function formatUsd(value: number) {
  return `$${value.toFixed(value < 1 ? 4 : 2)}`;
}

export function AdminDashboard() {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  useEffect(() => {
    setIsAdmin(getSession()?.role === "admin");
  }, []);

  if (isAdmin === null) {
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  }
  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-lg rounded-lg border bg-card px-6 py-10 text-center">
        <ShieldAlert className="mx-auto h-6 w-6 text-muted-foreground" />
        <h1 className="mt-3 text-base font-semibold">Admin access required</h1>
        <p className="mt-1 text-sm text-muted-foreground">Sign out and sign in with the admin role to open the admin console.</p>
        <Link href="/" className="mt-4 inline-block text-sm underline-offset-4 hover:underline">
          Back to product home
        </Link>
      </div>
    );
  }
  return <AdminConsole />;
}

function AdminConsole() {
  const queryClient = useQueryClient();
  const overview = useQuery({
    queryKey: ["admin-overview"],
    queryFn: getAdminOverview,
    refetchInterval: 15_000,
  });
  const unblock = useMutation({
    mutationFn: removeAiBlock,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-overview"] }),
  });
  const data = overview.data;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Admin console</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Platform activity, AI usage, and service configuration across all workspaces.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <WorkspaceLink href="/forensics" icon={FileSearch} label="Forensics" />
          <WorkspaceLink href="/compliance" icon={Landmark} label="Compliance" />
          <WorkspaceLink href="/signatures" icon={PenLine} label="Certificates" />
        </div>
      </header>

      {overview.isLoading ? (
        <div className="rounded-lg border bg-card px-5 py-8 text-sm text-muted-foreground">Loading admin overview…</div>
      ) : null}
      {overview.error ? (
        <div className="rounded-lg border border-destructive/30 bg-card px-5 py-8 text-sm text-destructive">
          {overview.error instanceof ApiError ? overview.error.message : "Unable to load the admin overview."}
        </div>
      ) : null}

      {data ? (
        <>
          {data.services.default_passwords_in_use ? (
            <div className="rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm">
              Demo passwords are still in use. Set <code className="font-mono">AUTH_USER_PASSWORD</code> and{" "}
              <code className="font-mono">AUTH_ADMIN_PASSWORD</code> in <code className="font-mono">backend/.env</code> before
              sharing this deployment.
            </div>
          ) : null}

          <section className="grid gap-4 md:grid-cols-3">
            <ModuleCard title="Document forensics" stats={data.forensics} />
            <ModuleCard title="Bid compliance" stats={data.compliance} />
            <ModuleCard title="Certificate analyzer" stats={data.certificates} />
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-lg border bg-card p-5">
              <h2 className="text-sm font-semibold">AI usage</h2>
              <div className="mt-4 grid grid-cols-2 gap-4">
                <UsageWindow title="Last 24 hours" usage={data.ai_usage.last_24h} />
                <UsageWindow title="All time" usage={data.ai_usage.all_time} />
              </div>
              <h3 className="mt-6 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                Top callers (24h)
              </h3>
              {data.ai_usage.top_subjects_24h.length ? (
                <table className="mt-2 w-full text-left text-sm">
                  <tbody>
                    {data.ai_usage.top_subjects_24h.map((item) => (
                      <tr key={item.subject} className="border-t">
                        <td className="truncate py-2 pr-2 font-mono text-xs">{item.subject}</td>
                        <td className="py-2 text-right text-muted-foreground">{item.calls} calls</td>
                        <td className="py-2 text-right text-muted-foreground">{item.tokens.toLocaleString()} tok</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">No AI calls in the last 24 hours.</p>
              )}
            </div>

            <div className="flex flex-col gap-4">
              <div className="rounded-lg border bg-card p-5">
                <h2 className="text-sm font-semibold">Active AI blocks</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Callers temporarily blocked by abuse detection. Remove a block to restore access immediately.
                </p>
                {data.ai_usage.active_blocks.length ? (
                  <ul className="mt-3 divide-y">
                    {data.ai_usage.active_blocks.map((block) => (
                      <li key={block.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                        <div className="min-w-0">
                          <p className="truncate font-mono text-xs">{block.subject}</p>
                          <p className="text-xs text-muted-foreground">
                            {label(block.reason)} · until {formatTimestamp(block.blocked_until)}
                          </p>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={unblock.isPending}
                          onClick={() => unblock.mutate(block.id)}
                        >
                          Unblock
                        </Button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm text-muted-foreground">No callers are blocked.</p>
                )}
                {unblock.error ? (
                  <p className="mt-2 text-sm text-destructive">
                    {unblock.error instanceof ApiError ? unblock.error.message : "Unblock failed."}
                  </p>
                ) : null}
              </div>

              <div className="rounded-lg border bg-card p-5">
                <h2 className="text-sm font-semibold">Services</h2>
                <ul className="mt-3 space-y-2 text-sm">
                  <ServiceRow label="AI explanations" on={data.services.ai_explanations} off="Rule-based fallback" />
                  <ServiceRow label="PAN verification" on={data.services.pan_verification} />
                  <ServiceRow label="GSTIN verification" on={data.services.gst_verification} />
                  <ServiceRow label="Google sign-in" on={data.services.google_sign_in} />
                  <li className="flex items-center justify-between">
                    <span>Google admin accounts</span>
                    <span className="text-muted-foreground">{data.services.google_admin_emails}</span>
                  </li>
                </ul>
              </div>
            </div>
          </section>

          <section className="rounded-lg border bg-card">
            <h2 className="px-5 pt-5 text-sm font-semibold">Recent activity</h2>
            {data.recent_activity.length ? (
              <div className="overflow-x-auto">
                <table className="mt-3 w-full min-w-[640px] text-left text-sm">
                  <thead className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-5 py-2 font-medium">File</th>
                      <th className="px-5 py-2 font-medium">Module</th>
                      <th className="px-5 py-2 font-medium">Result</th>
                      <th className="px-5 py-2 font-medium">Status</th>
                      <th className="px-5 py-2 font-medium">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_activity.map((item) => (
                      <tr key={`${item.module}-${item.id}`} className="border-t">
                        <td className="px-5 py-2.5">
                          <Link className="font-medium underline-offset-4 hover:underline" href={MODULE_LINKS[item.module](item.id)}>
                            {item.original_filename}
                          </Link>
                        </td>
                        <td className="px-5 py-2.5 text-muted-foreground">{MODULE_LABELS[item.module]}</td>
                        <td className="px-5 py-2.5">
                          {item.outcome ? <Badge variant={outcomeVariant(item.outcome)}>{label(item.outcome)}</Badge> : "—"}
                        </td>
                        <td className="px-5 py-2.5 capitalize text-muted-foreground">{label(item.status)}</td>
                        <td className="px-5 py-2.5 text-muted-foreground">{formatTimestamp(item.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="px-5 py-6 text-sm text-muted-foreground">No uploads yet.</p>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}

function WorkspaceLink({ href, icon: Icon, label: text }: { href: string; icon: typeof FileSearch; label: string }) {
  return (
    <Link href={href} className="inline-flex h-9 items-center gap-2 rounded-md border bg-background px-3 text-sm hover:bg-muted">
      <Icon className="h-4 w-4" />
      {text}
    </Link>
  );
}

function ModuleCard({ title, stats }: { title: string; stats: ModuleStats }) {
  const outcomes = Object.entries(stats.by_outcome).sort((a, b) => b[1] - a[1]);
  const failed = stats.by_status.FAILED ?? 0;
  const running = (stats.by_status.PROCESSING ?? 0) + (stats.by_status.PENDING ?? 0);
  return (
    <div className="rounded-lg border bg-card p-5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums">{stats.total}</p>
      <p className="text-xs text-muted-foreground">
        {running} running · {failed} failed
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {outcomes.length ? (
          outcomes.map(([key, count]) => (
            <Badge key={key} variant={outcomeVariant(key)}>
              {label(key)} {count}
            </Badge>
          ))
        ) : (
          <span className="text-xs text-muted-foreground">No completed results yet.</span>
        )}
      </div>
    </div>
  );
}

function UsageWindow({ title, usage }: { title: string; usage: AiUsageWindow }) {
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{usage.calls}</p>
      <p className="text-xs text-muted-foreground">
        {(usage.input_tokens + usage.output_tokens).toLocaleString()} tokens · {formatUsd(usage.estimated_cost_usd)}
      </p>
      <p className="text-xs text-muted-foreground">
        {usage.cached} cached · {usage.rate_limited} limited · {usage.failures} failed
      </p>
    </div>
  );
}

function ServiceRow({ label: text, on, off = "Not configured" }: { label: string; on: boolean; off?: string }) {
  return (
    <li className="flex items-center justify-between">
      <span>{text}</span>
      <Badge variant={on ? "success" : "muted"}>{on ? "Configured" : off}</Badge>
    </li>
  );
}
