import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EvidenceViewer } from "@/components/analysis/evidence-viewer";
import type { CopyMoveForensicsResult } from "@/types/analysis";

export function CopyMovePanel({ analysisId, result }: { analysisId: string; result: CopyMoveForensicsResult }) {
  const page = result.pages[0];
  const evidence = result.pages.flatMap((item) => item.evidence);
  const regions = result.pages.flatMap((item) => item.regions.map((region) => ({ page: item.page_number, region })));

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>Copy-move analysis</CardTitle>
            <CardDescription>
              Feature matching with geometric verification. Repeated letters and templates are filtered.
            </CardDescription>
          </div>
          <Badge variant={result.flagged ? "warning" : "muted"}>
            {regions.length ? `${regions.length} region pair(s)` : "No strong clone evidence"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {result.module_error ? <p className="text-sm text-destructive">{result.module_error}</p> : null}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric label="Suspicion" value={String(result.suspicion_score)} />
          <Metric label="Confidence" value={result.confidence.toFixed(2)} />
          <Metric label="Verified matches" value={page ? String(page.metrics.geometrically_verified_matches) : "—"} />
          <Metric label="Clusters" value={page ? String(page.metrics.suspicious_clusters) : "—"} />
        </div>
        <p className="text-sm leading-6">{result.summary}</p>
        {regions.length ? (
          <ul className="space-y-2">
            {regions.map(({ page: pageNumber, region }) => (
              <li key={`${pageNumber}-${region.region_id}`} className="rounded-md border px-3 py-2 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">Page {pageNumber}</Badge>
                  <span className="font-medium">{region.region_id}</span>
                  <Badge variant={region.evidence_strength === "high" ? "warning" : "muted"}>{region.evidence_strength}</Badge>
                </div>
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  source {region.source_bbox.x},{region.source_bbox.y} {region.source_bbox.width}×{region.source_bbox.height}
                  {" → "}
                  match {region.matched_bbox.x},{region.matched_bbox.y} {region.matched_bbox.width}×{region.matched_bbox.height}
                  {" · "}conf {region.match_confidence.toFixed(2)}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No strong duplicated-region evidence was detected.</p>
        )}
        <EvidenceViewer
          analysisId={analysisId}
          evidence={evidence}
          emptyLabel="No copy-move overlay is shown because no verified region pair was stored."
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
