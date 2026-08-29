import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PreprocessingResult } from "@/types/analysis";
import { formatDocumentType } from "@/lib/utils";

export function PreprocessingPanel({ result }: { result: PreprocessingResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Preprocessing</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Classification</dt>
            <dd className="mt-1 text-sm">{formatDocumentType(result.document_type)}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Pages rendered</dt>
            <dd className="mt-1 text-sm">{result.page_count}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Image format</dt>
            <dd className="mt-1 text-sm">{result.image_format ?? "—"}</dd>
          </div>
        </dl>
        <div>
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Rendered pages</p>
          <ul className="mt-2 grid gap-2 sm:grid-cols-2">
            {result.pages.map((page) => (
              <li key={page.page_number} className="rounded-md border px-3 py-2 text-sm">
                Page {page.page_number} · {page.width} × {page.height} px
              </li>
            ))}
          </ul>
        </div>
        {result.processing_notes.length > 0 ? (
          <div>
            <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Notes</p>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-muted-foreground">
              {result.processing_notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
