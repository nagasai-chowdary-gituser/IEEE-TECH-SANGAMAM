import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { MetadataForensicsResult, MetadataSignal } from "@/types/analysis";

function severityVariant(severity: MetadataSignal["severity"]) {
  if (severity === "high") return "danger" as const;
  if (severity === "medium") return "warning" as const;
  return "muted" as const;
}

function derivedStatus(result: MetadataForensicsResult): string {
  if (result.flagged) return "Flagged for review";
  if (result.suspicion_score === 0) return "No metadata signals";
  if (result.suspicion_score < 20) return "Low metadata suspicion";
  return "Contextual signals present";
}

export function MetadataPanel({ result }: { result: MetadataForensicsResult }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>Metadata forensics</CardTitle>
            <CardDescription>
              Evidence from embedded metadata only. This layer does not prove forgery.
            </CardDescription>
          </div>
          <Badge variant={result.flagged ? "warning" : "success"}>{derivedStatus(result)}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div className="rounded-md border bg-background px-3 py-3">
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Suspicion</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{result.suspicion_score}</p>
            <p className="text-xs text-muted-foreground">0–100</p>
          </div>
          <div className="rounded-md border bg-background px-3 py-3">
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Confidence</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{result.confidence.toFixed(2)}</p>
            <p className="text-xs text-muted-foreground">0.00–1.00</p>
          </div>
          <div className="rounded-md border bg-background px-3 py-3">
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Signals</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{result.signals.length}</p>
            <p className="text-xs text-muted-foreground">distinct findings</p>
          </div>
        </div>

        <p className="text-sm leading-6 text-foreground/90">{result.summary}</p>

        {result.signals.length === 0 ? (
          <p className="text-sm text-muted-foreground">No metadata signals were generated for this file.</p>
        ) : (
          <ul className="space-y-3">
            {result.signals.map((signal) => (
              <li key={signal.id} className="rounded-md border px-3 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={severityVariant(signal.severity)}>{signal.severity}</Badge>
                  <span className="text-sm font-medium">{signal.finding}</span>
                  <span className="ml-auto font-mono text-xs text-muted-foreground">
                    +{signal.score_impact}
                  </span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{signal.detail}</p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
