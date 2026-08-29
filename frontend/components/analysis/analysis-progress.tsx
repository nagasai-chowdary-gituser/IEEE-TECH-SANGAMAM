const STAGES = [
  { id: "securing_document", label: "Securing document" },
  { id: "preprocessing", label: "Preprocessing" },
  { id: "metadata_analysis", label: "Metadata analysis" },
  { id: "visual_forensics", label: "Visual forensics" },
  { id: "document_intelligence", label: "Document intelligence" },
  { id: "evidence_fusion", label: "Evidence fusion" },
  { id: "preparing_explanation", label: "Preparing explanation" },
  { id: "complete", label: "Complete" },
] as const;

export function AnalysisProgress({
  stage,
  status,
  errorMessage,
}: {
  stage: string | null;
  status: string;
  errorMessage: string | null;
}) {
  const currentIndex = Math.max(
    0,
    STAGES.findIndex((item) => item.id === stage),
  );
  return (
    <section className="rounded-lg border bg-card p-5">
      <h2 className="text-sm font-semibold tracking-tight">Analysis progress</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Stages reflect the live pipeline. Timing percentages are not estimated.
      </p>
      <ol className="mt-4 space-y-2">
        {STAGES.filter((item) => item.id !== "complete").map((item, index) => {
          const done = status === "COMPLETE" || index < currentIndex;
          const active = status === "PROCESSING" && item.id === stage;
          return (
            <li key={item.id} className="flex items-center gap-2 text-sm">
              <span
                className={
                  active
                    ? "h-2 w-2 rounded-full bg-warning"
                    : done
                      ? "h-2 w-2 rounded-full bg-success"
                      : "h-2 w-2 rounded-full bg-muted-foreground/30"
                }
              />
              <span className={active ? "font-medium" : "text-muted-foreground"}>{item.label}</span>
              {active ? <span className="text-xs text-muted-foreground">in progress</span> : null}
            </li>
          );
        })}
      </ol>
      {status === "FAILED" ? (
        <p className="mt-3 text-sm text-destructive">{errorMessage || "Analysis failed."}</p>
      ) : null}
    </section>
  );
}
