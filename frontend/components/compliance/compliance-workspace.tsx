"use client";

import { ComplianceUpload } from "@/components/compliance/compliance-upload";
import { useAnalyzeCompliance } from "@/hooks/use-analyze-compliance";
import { ApiError } from "@/lib/api";

export function ComplianceWorkspace() {
  const mutation = useAnalyzeCompliance();
  const errorMessage =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? "Assessment failed. Confirm the API is running and the file is a supported certificate."
        : null;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
      <header>
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Government Bid Compliance</p>
        <h1 className="mt-2 text-xl font-semibold tracking-tight">Udyam certificate assessment</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Extract PAN and GSTIN, verify them through configured services, and run local certificate integrity
          analysis in parallel. Results are decision support, not legal approval.
        </p>
      </header>
      <ComplianceUpload isSubmitting={mutation.isPending} errorMessage={errorMessage} onAnalyze={(file) => mutation.mutate(file)} />
    </div>
  );
}
