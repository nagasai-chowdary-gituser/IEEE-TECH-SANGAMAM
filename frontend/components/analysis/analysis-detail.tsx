"use client";

import Link from "next/link";
import { useState } from "react";

import { AnalysisAssistant } from "@/components/analysis/analysis-assistant";
import { AnalysisProgress } from "@/components/analysis/analysis-progress";
import { AnalysisResults } from "@/components/analysis/analysis-results";
import { Button, buttonVariants } from "@/components/ui/button";
import { useAnalysis } from "@/hooks/use-analysis";
import { ApiError, getReportUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

export function AnalysisDetail({ analysisId }: { analysisId: string }) {
  const query = useAnalysis(analysisId);
  const [assistantWidth, setAssistantWidth] = useState(34);
  const [assistantOpen, setAssistantOpen] = useState(true);
  const analysis = query.data;
  const processing = analysis?.status === "PROCESSING" || analysis?.status === "PENDING";

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-muted-foreground">
            <Link href="/forensics" className="hover:underline">
              New analysis
            </Link>
            <span className="mx-2">/</span>
            <Link href="/history" className="hover:underline">
              History
            </Link>
            <span className="mx-2">/</span>
            <span className="font-mono">{analysisId}</span>
          </p>
          <h1 className="mt-2 text-xl font-semibold tracking-tight">Analysis</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Manipulation risk assessment based on available digital evidence. Not legal proof, signer identity
            verification, or registry confirmation.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/forensics" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
            New analysis
          </Link>
          {analysis?.status === "COMPLETE" ? (
            <a
              href={getReportUrl(analysisId)}
              target="_blank"
              rel="noreferrer"
              className={cn(buttonVariants({ size: "sm" }))}
            >
              Download report
            </a>
          ) : null}
          <Button type="button" variant="outline" size="sm" className="lg:hidden" onClick={() => setAssistantOpen((value) => !value)}>
            {assistantOpen ? "Hide assistant" : "Show assistant"}
          </Button>
        </div>
      </header>

      {query.isLoading ? (
        <div className="rounded-lg border bg-card px-5 py-8 text-sm text-muted-foreground">Loading analysis…</div>
      ) : null}
      {query.error ? (
        <div className="rounded-lg border border-destructive/30 bg-card px-5 py-8 text-sm text-destructive">
          {query.error instanceof ApiError ? query.error.message : "Unable to load this analysis."}
        </div>
      ) : null}

      {analysis ? (
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
          <div className="min-w-0 flex-1 space-y-4">
            {processing || analysis.status === "FAILED" ? (
              <AnalysisProgress
                stage={analysis.pipeline_stage}
                status={analysis.status}
                errorMessage={analysis.error_message}
              />
            ) : null}
            <AnalysisResults analysis={analysis} />
          </div>
          {assistantOpen ? (
            <>
              <div
                className="hidden w-1 shrink-0 cursor-col-resize bg-border lg:block"
                onMouseDown={(event) => {
                  event.preventDefault();
                  const startX = event.clientX;
                  const startWidth = assistantWidth;
                  function onMove(move: MouseEvent) {
                    const delta = ((startX - move.clientX) / window.innerWidth) * 100;
                    setAssistantWidth(Math.min(48, Math.max(24, startWidth + delta)));
                  }
                  function onUp() {
                    window.removeEventListener("mousemove", onMove);
                    window.removeEventListener("mouseup", onUp);
                  }
                  window.addEventListener("mousemove", onMove);
                  window.addEventListener("mouseup", onUp);
                }}
                aria-hidden
              />
              <div className="w-full lg:sticky lg:top-4" style={{ flexBasis: `${assistantWidth}%`, maxWidth: 460 }}>
                <AnalysisAssistant analysis={analysis} />
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
