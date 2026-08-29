"use client";

import { UploadPanel } from "@/components/analysis/upload-panel";
import { AnalysisEmptyState } from "@/components/analysis/analysis-empty-state";
import { useAnalyzeDocument } from "@/hooks/use-analyze-document";
import { ApiError } from "@/lib/api";

export function AnalysisWorkspace() {
  const mutation = useAnalyzeDocument();
  const errorMessage =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.error
        ? "Analysis failed. Check that the API is running and the file is a supported PDF or image."
        : null;

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight">New analysis</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload a document to run hashing, metadata forensics, visual forensics, document intelligence, and
          explainable risk assessment. The product does not verify signer identity or legal authenticity.
        </p>
      </header>
      <UploadPanel
        isSubmitting={mutation.isPending}
        errorMessage={errorMessage}
        onAnalyze={(file) => mutation.mutate(file)}
      />
      {mutation.isPending ? (
        <div className="rounded-lg border bg-card px-5 py-8 text-sm text-muted-foreground">
          Uploading and securing the document. You will be moved to the analysis page so you can watch live pipeline stages.
        </div>
      ) : null}
      {!mutation.isPending && !mutation.data ? <AnalysisEmptyState /> : null}
    </div>
  );
}
