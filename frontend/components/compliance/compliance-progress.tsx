const STAGES = [
  { id: "securing_certificate", label: "Securing certificate" },
  { id: "extracting_certificate", label: "Extracting certificate information" },
  { id: "validating_identifiers", label: "Validating PAN and GSTIN format" },
  { id: "verifying_parallel", label: "PAN, GSTIN, and integrity analysis in parallel" },
  { id: "aggregating_compliance", label: "Aggregating compliance evidence" },
  { id: "complete", label: "Complete" },
];

export function ComplianceProgress({
  stage,
  status,
  pan,
  gst,
  forensic,
  errorMessage,
}: {
  stage: string | null;
  status: string;
  pan: string | null;
  gst: string | null;
  forensic: string | null;
  errorMessage: string | null;
}) {
  const current = STAGES.findIndex((item) => item.id === stage);
  return (
    <section className="border bg-card p-5">
      <h2 className="text-sm font-semibold">Assessment progress</h2>
      <p className="mt-1 text-sm text-muted-foreground">Stages follow the live workflow. Percentages are not estimated.</p>
      <ol className="mt-4 space-y-2 text-sm">
        {STAGES.filter((item) => item.id !== "complete").map((item, index) => {
          const done = status === "COMPLETE" || index < current;
          const active = status === "PROCESSING" && item.id === stage;
          return (
            <li key={item.id} className="flex items-center gap-2">
              <span className={active ? "h-2 w-2 rounded-full bg-blue-600" : done ? "h-2 w-2 rounded-full bg-success" : "h-2 w-2 rounded-full bg-muted-foreground/30"} />
              <span className={active ? "font-medium" : "text-muted-foreground"}>{item.label}</span>
            </li>
          );
        })}
      </ol>
      {stage === "verifying_parallel" ? (
        <dl className="mt-4 grid grid-cols-1 gap-2 text-xs sm:grid-cols-3">
          <div className="border px-3 py-2">PAN {pan ?? "running"}</div>
          <div className="border px-3 py-2">GSTIN {gst ?? "running"}</div>
          <div className="border px-3 py-2">Integrity {forensic ?? "running"}</div>
        </dl>
      ) : null}
      {status === "FAILED" ? <p className="mt-3 text-sm text-destructive">{errorMessage || "Assessment failed."}</p> : null}
    </section>
  );
}
