"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useComplianceHistory } from "@/hooks/use-compliance-history";
import { ApiError } from "@/lib/api";
import { formatTimestamp } from "@/lib/utils";

const PAGE_SIZE = 20;

function variant(status: string | null) {
  if (status === "COMPLIANT") return "success" as const;
  if (status === "REVIEW_REQUIRED") return "warning" as const;
  if (status === "HIGH_RISK") return "danger" as const;
  return "muted" as const;
}

export function ComplianceHistoryView() {
  const [offset, setOffset] = useState(0);
  const query = useComplianceHistory(PAGE_SIZE, offset);
  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">Compliance history</h1>
        <p className="mt-1 text-sm text-muted-foreground">Saved Government Bid Compliance assessments from this workspace.</p>
      </header>
      {query.isLoading ? <div className="border bg-card px-5 py-8 text-sm text-muted-foreground">Loading history…</div> : null}
      {query.error ? (
        <div className="border border-destructive/30 bg-card px-5 py-8 text-sm text-destructive">
          {query.error instanceof ApiError ? query.error.message : "Unable to load history."}
        </div>
      ) : null}
      {query.data && items.length === 0 ? (
        <div className="border border-dashed bg-card px-5 py-10 text-center text-sm text-muted-foreground">No compliance assessments yet.</div>
      ) : null}
      {items.length ? (
        <div className="overflow-x-auto border bg-card">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Certificate</th>
                <th className="px-4 py-3 font-medium">Enterprise</th>
                <th className="px-4 py-3 font-medium">PAN</th>
                <th className="px-4 py-3 font-medium">GSTIN</th>
                <th className="px-4 py-3 font-medium">Integrity</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.compliance_id} className="border-t">
                  <td className="px-4 py-3">
                    <Link className="font-medium underline-offset-4 hover:underline" href={`/compliance/${item.compliance_id}`}>
                      {item.original_filename}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{item.enterprise_name ?? "—"}</td>
                  <td className="px-4 py-3">{item.pan_outcome ?? "—"}</td>
                  <td className="px-4 py-3">{item.gstin_outcome ?? "—"}</td>
                  <td className="px-4 py-3 text-muted-foreground">{item.integrity_level?.replaceAll("_", " ") ?? "—"}</td>
                  <td className="px-4 py-3">
                    {item.overall_status ? <Badge variant={variant(item.overall_status)}>{item.overall_status.replaceAll("_", " ")}</Badge> : "—"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{formatTimestamp(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {total > PAGE_SIZE ? (
        <div className="flex items-center justify-between text-sm">
          <p className="text-muted-foreground">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
          </p>
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset((v) => Math.max(0, v - PAGE_SIZE))}>
              Previous
            </Button>
            <Button type="button" variant="outline" size="sm" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset((v) => v + PAGE_SIZE)}>
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
