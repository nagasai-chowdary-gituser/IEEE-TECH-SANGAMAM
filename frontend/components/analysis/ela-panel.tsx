import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EvidenceViewer } from "@/components/analysis/evidence-viewer";
import type { ElaForensicsResult } from "@/types/analysis";

export function ElaPanel({ analysisId, result }: { analysisId: string; result: ElaForensicsResult }) {
  const page = result.pages[0];
  const evidence = result.pages.flatMap((item) => item.evidence);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>Error Level Analysis</CardTitle>
            <CardDescription>
              JPEG recompression residual map. Bright areas indicate inconsistency, not confirmed tampering.
            </CardDescription>
          </div>
          <Badge variant={result.flagged ? "warning" : "muted"}>{result.analysis_quality} quality</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {result.module_error ? <p className="text-sm text-destructive">{result.module_error}</p> : null}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric label="Suspicion" value={String(result.suspicion_score)} />
          <Metric label="Confidence" value={result.confidence.toFixed(2)} />
          <Metric label="Mean error" value={page ? page.metrics.mean_error.toFixed(2) : "—"} />
          <Metric label="High-error ratio" value={page ? page.metrics.high_error_ratio.toFixed(4) : "—"} />
        </div>
        <p className="text-sm leading-6">{result.summary}</p>
        {result.pages.length > 1 ? (
          <p className="text-xs text-muted-foreground">{result.pages.length} pages analyzed independently.</p>
        ) : null}
        <EvidenceViewer
          analysisId={analysisId}
          evidence={evidence}
          emptyLabel="No ELA visualization is available for this document."
        />
        {page?.limitations.length ? (
          <ul className="list-disc space-y-1 pl-4 text-xs text-muted-foreground">
            {page.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background px-3 py-3">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 font-semibold tabular-nums">{value}</p>
    </div>
  );
}
