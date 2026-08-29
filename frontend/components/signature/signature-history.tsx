"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useSignatureHistory } from "@/hooks/use-signature-history";
import { ApiError } from "@/lib/api";
import { formatTimestamp } from "@/lib/utils";

const PAGE_SIZE = 20;

export function SignatureHistoryView() {
  const [offset, setOffset] = useState(0);
  const query = useSignatureHistory(PAGE_SIZE, offset);
  const items = query.data?.items ?? [];
  const total = query.data?.total ?? 0;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">Certificate history</h1>
        <p className="mt-1 text-sm text-muted-foreground">Saved full-certificate analyses from this workspace.</p>
      </header>
      {query.isLoading ? <div className="border bg-card px-5 py-8 text-sm text-muted-foreground">Loading history…</div> : null}
      {query.error ? (
        <div className="border border-destructive/30 bg-card px-5 py-8 text-sm text-destructive">
          {query.error instanceof ApiError ? query.error.message : "Unable to load history."}
        </div>
      ) : null}
      {query.data && items.length === 0 ? (
        <div className="border border-dashed bg-card px-5 py-10 text-center text-sm text-muted-foreground">No certificate analyses yet.</div>
      ) : null}
      {items.length ? (
        <div className="overflow-x-auto border bg-card">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-medium">Certificate</th>
                <th className="px-4 py-3 font-medium">Reference</th>
                <th className="px-4 py-3 font-medium">Integrity</th>
                <th className="px-4 py-3 font-medium">Manipulation</th>
                <th className="px-4 py-3 font-medium">Final</th>
                <th className="px-4 py-3 font-medium">Originality</th>
                <th className="px-4 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.comparison_id} className="border-t">
                  <td className="px-4 py-3">
                    <Link className="font-medium underline-offset-4 hover:underline" href={`/signatures/${item.comparison_id}`}>
                      {item.original_filename}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{item.reference_label ?? "—"}</td>
                  <td className="px-4 py-3">
                    {item.certificate_status ? <Badge variant="outline">{item.certificate_status.replaceAll("_", " ")}</Badge> : item.overall_status ? <Badge variant="outline">{item.overall_status.replaceAll("_", " ")}</Badge> : "—"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{item.tamper_level?.replaceAll("_", " ") ?? "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs">{item.final_score != null ? `${item.final_score}` : "—"}</td>
                  <td className="px-4 py-3 text-xs">
                    {item.originality_verdict ? item.originality_verdict.replaceAll("_", " ") : "—"}
                    {item.originality_score != null ? <span className="ml-1 font-mono text-muted-foreground">{item.originality_score}</span> : null}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{formatTimestamp(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {total > PAGE_SIZE ? (
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset((v) => Math.max(0, v - PAGE_SIZE))}>
            Previous
          </Button>
          <Button type="button" variant="outline" size="sm" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset((v) => v + PAGE_SIZE)}>
            Next
          </Button>
        </div>
      ) : null}
    </div>
  );
}
