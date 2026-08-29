"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAnalysisHistory } from "@/hooks/use-analysis-history";
import { ApiError } from "@/lib/api";
import { formatDocumentType, formatTimestamp } from "@/lib/utils";
import { useState } from "react";

const PAGE_SIZE = 20;

function riskVariant(level: string | null) {
  if (level === "LOW") return "success" as const;
  if (level === "MODERATE") return "warning" as const;
  if (level === "ELEVATED" || level === "HIGH") return "danger" as const;
  return "muted" as const;
}

export function HistoryView() {
  const [offset, setOffset] = useState(0);
  const query = useAnalysisHistory(PAGE_SIZE, offset);
  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">Analysis history</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Saved forensic analyses from this workspace.{" "}
          <Link href="/signatures/history" className="underline-offset-4 hover:underline">
            Certificate analysis history
          </Link>{" "}
          and{" "}
          <Link href="/compliance/history" className="underline-offset-4 hover:underline">
            bid compliance history
          </Link>{" "}
          are listed in their modules.
        </p>
      </header>
      {query.isLoading ? (
        <div className="rounded-lg border bg-card px-5 py-8 text-sm text-muted-foreground">Loading history…</div>
      ) : null}
      {query.error ? (
        <div className="rounded-lg border border-destructive/30 bg-card px-5 py-8 text-sm text-destructive">
          {query.error instanceof ApiError ? query.error.message : "Unable to load analysis history."}
        </div>
      ) : null}
      {query.data && items.length === 0 ? (
        <div className="rounded-lg border border-dashed bg-card px-5 py-10 text-center text-sm text-muted-foreground">
          No analyses yet. Start a new analysis to populate this list.
        </div>
      ) : null}
      {items.length ? (
        <div className="overflow-x-auto rounded-lg border bg-card">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Filename</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Risk</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.analysis_id} className="border-t">
                  <td className="px-4 py-3">
                    <Link className="font-medium underline-offset-4 hover:underline" href={`/analysis/${item.analysis_id}`}>
                      {item.original_filename}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{formatDocumentType(item.document_type)}</td>
                  <td className="px-4 py-3">
                    {item.risk_level ? <Badge variant={riskVariant(item.risk_level)}>{item.risk_level}</Badge> : "—"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{item.status.replaceAll("_", " ")}</td>
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
            <Button type="button" variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}>
              Previous
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset((value) => value + PAGE_SIZE)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
