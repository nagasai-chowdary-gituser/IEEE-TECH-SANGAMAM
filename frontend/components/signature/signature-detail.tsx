"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { RegionPicker } from "@/components/signature/region-picker";
import { SignatureResults } from "@/components/signature/signature-results";
import { buttonVariants } from "@/components/ui/button";
import { useSignatureComparison } from "@/hooks/use-signature-comparison";
import { ApiError, getSignatureArtifactUrl, getSignatureReportUrl, setSignatureRegion } from "@/lib/api";
import { cn } from "@/lib/utils";

const STAGES = [
  { id: "securing_document", label: "Preparing document" },
  { id: "preprocessing_document", label: "Analyzing document structure" },
  { id: "visual_forensics", label: "Running visual forensic checks" },
  { id: "extracting_text", label: "Extracting text and layout" },
  { id: "checking_suspicious_regions", label: "Checking suspicious regions" },
  { id: "detecting_signatures", label: "Detecting signature regions" },
  { id: "analyzing_signature_integrity", label: "Analyzing signature integrity" },
  { id: "comparing_reference", label: "Comparing reference signature" },
  { id: "fusing_evidence", label: "Fusing evidence" },
  { id: "awaiting_region", label: "Awaiting signature confirmation" },
];

export function SignatureDetail({ comparisonId }: { comparisonId: string }) {
  const query = useSignatureComparison(comparisonId);
  const queryClient = useQueryClient();
  const result = query.data;
  const region = useMutation({
    mutationFn: (box: { page_number: number; x: number; y: number; width: number; height: number }) =>
      setSignatureRegion(comparisonId, box),
    onSuccess: (data) => {
      queryClient.setQueryData(["signature-comparison", comparisonId], data);
    },
  });
  const processing = result?.status === "PROCESSING" || result?.status === "PENDING";
  const showCompareStage = Boolean(result?.reference_id);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-muted-foreground">
            <Link href="/signatures" className="hover:underline">
              New certificate analysis
            </Link>
            <span className="mx-2">/</span>
            <span className="font-mono">{comparisonId}</span>
          </p>
          <h1 className="mt-2 text-xl font-semibold tracking-tight">Certificate analysis</h1>
        </div>
        <div className="flex gap-2">
          <Link href="/signatures" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
            New analysis
          </Link>
          {result && result.status !== "PROCESSING" && result.status !== "PENDING" ? (
            <a href={getSignatureReportUrl(comparisonId)} className={cn(buttonVariants({ size: "sm" }))} target="_blank" rel="noreferrer">
              Download report
            </a>
          ) : null}
        </div>
      </header>
      {query.isLoading ? <div className="border bg-card px-5 py-8 text-sm text-muted-foreground">Loading analysis…</div> : null}
      {query.error ? (
        <div className="border border-destructive/30 bg-card px-5 py-8 text-sm text-destructive">
          {query.error instanceof ApiError ? query.error.message : "Unable to load this analysis."}
        </div>
      ) : null}
      {processing ? (
        <section className="border bg-card p-5">
          <h2 className="text-sm font-semibold">Progress</h2>
          <ol className="mt-3 space-y-2 text-sm">
            {STAGES.filter((item) => item.id !== "comparing_reference" || showCompareStage).map((item) => (
              <li key={item.id} className={item.id === result?.pipeline_stage ? "font-medium" : "text-muted-foreground"}>
                {item.label}
              </li>
            ))}
          </ol>
        </section>
      ) : null}
      {result?.certificate && result.status !== "PROCESSING" ? <SignatureResults result={result} /> : null}
      {result?.status === "NEEDS_REGION" ? (
        <RegionPicker
          imageUrl={getSignatureArtifactUrl(comparisonId, "page-preview")}
          candidates={result.candidates}
          pending={region.isPending}
          onSelect={(box) => region.mutate(box)}
        />
      ) : null}
      {region.error ? (
        <p className="text-sm text-destructive">{region.error instanceof ApiError ? region.error.message : "Region could not be applied."}</p>
      ) : null}
    </div>
  );
}
