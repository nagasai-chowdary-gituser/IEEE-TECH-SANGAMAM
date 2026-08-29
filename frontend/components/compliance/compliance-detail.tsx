"use client";

import Link from "next/link";

import { ComplianceProgress } from "@/components/compliance/compliance-progress";
import { ComplianceResults } from "@/components/compliance/compliance-results";
import { buttonVariants } from "@/components/ui/button";
import { useCompliance } from "@/hooks/use-compliance";
import { ApiError, getComplianceReportUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

export function ComplianceDetail({ complianceId }: { complianceId: string }) {
  const query = useCompliance(complianceId);
  const result = query.data;
  const processing = result?.status === "PROCESSING" || result?.status === "PENDING";

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-muted-foreground">
            <Link href="/compliance" className="hover:underline">
              New assessment
            </Link>
            <span className="mx-2">/</span>
            <span className="font-mono">{complianceId}</span>
          </p>
          <h1 className="mt-2 text-xl font-semibold tracking-tight">Compliance assessment</h1>
        </div>
        <div className="flex gap-2">
          <Link href="/compliance" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
            New assessment
          </Link>
          {result?.status === "COMPLETE" ? (
            <a href={getComplianceReportUrl(complianceId)} className={cn(buttonVariants({ size: "sm" }))} target="_blank" rel="noreferrer">
              Download report
            </a>
          ) : null}
        </div>
      </header>
      {query.isLoading ? <div className="border bg-card px-5 py-8 text-sm text-muted-foreground">Loading assessment…</div> : null}
      {query.error ? (
        <div className="border border-destructive/30 bg-card px-5 py-8 text-sm text-destructive">
          {query.error instanceof ApiError ? query.error.message : "Unable to load this assessment."}
        </div>
      ) : null}
      {result && processing ? (
        <ComplianceProgress
          stage={result.pipeline_stage}
          status={result.status}
          pan={result.pan?.outcome ?? null}
          gst={result.gstin?.outcome ?? null}
          forensic={result.forensic_status ?? null}
          errorMessage={result.error_message}
        />
      ) : null}
      {result && result.status === "FAILED" ? (
        <ComplianceProgress
          stage={result.pipeline_stage}
          status={result.status}
          pan={result.pan?.outcome ?? null}
          gst={result.gstin?.outcome ?? null}
          forensic={result.forensic_status ?? null}
          errorMessage={result.error_message}
        />
      ) : null}
      {result ? <ComplianceResults result={result} /> : null}
    </div>
  );
}
