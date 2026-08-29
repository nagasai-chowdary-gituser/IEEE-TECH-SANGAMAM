import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatBytes, formatDocumentType } from "@/lib/utils";
import type { AnalysisResponse } from "@/types/analysis";

function statusVariant(status: AnalysisResponse["status"]) {
  if (status === "FAILED") return "danger" as const;
  if (status === "PARTIAL_COMPLETE" || status === "COMPLETE") return "success" as const;
  if (status === "PROCESSING") return "warning" as const;
  return "muted" as const;
}

export function DocumentOverview({ analysis }: { analysis: AnalysisResponse }) {
  const pageCount = analysis.preprocessing?.page_count ?? "—";
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <CardTitle>Document overview</CardTitle>
        <Badge variant={statusVariant(analysis.status)}>{analysis.status.replaceAll("_", " ")}</Badge>
      </CardHeader>
      <CardContent>
        {analysis.layers_completed ? (
          <p className="mb-4 text-sm text-muted-foreground">{analysis.layers_completed}</p>
        ) : null}
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Filename</dt>
            <dd className="mt-1 break-all text-sm">{analysis.document.original_filename}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Document type</dt>
            <dd className="mt-1 text-sm">{formatDocumentType(analysis.document.document_type)}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Page count</dt>
            <dd className="mt-1 text-sm">{pageCount}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">SHA-256</dt>
            <dd className="mt-1 font-mono text-sm">{analysis.document.sha256_short ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">File type</dt>
            <dd className="mt-1 text-sm uppercase">{analysis.document.file_type ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Size</dt>
            <dd className="mt-1 text-sm">{formatBytes(analysis.document.file_size)}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
