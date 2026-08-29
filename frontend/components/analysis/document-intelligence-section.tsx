"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EvidenceViewer } from "@/components/analysis/evidence-viewer";
import type { DocumentIntelligenceResult, LogicalCheck } from "@/types/analysis";

function checkVariant(result: LogicalCheck["result"]) {
  if (result === "fail") return "danger" as const;
  if (result === "warning") return "warning" as const;
  if (result === "pass") return "success" as const;
  return "muted" as const;
}

function checkLabel(result: LogicalCheck["result"]) {
  if (result === "insufficient_data") return "Could not evaluate";
  if (result === "not_applicable") return "Not applicable";
  return result;
}

export function DocumentIntelligenceSection({
  analysisId,
  result,
}: {
  analysisId: string;
  result: DocumentIntelligenceResult;
}) {
  const pages = result.extraction.pages;
  const [pageNumber, setPageNumber] = useState(pages[0]?.page_number ?? 1);
  const page = useMemo(
    () => pages.find((item) => item.page_number === pageNumber) ?? pages[0],
    [pages, pageNumber],
  );
  const highlightEvidence = result.logical_checks
    .filter((check) => check.artifact_id)
    .map((check) => ({
      type: "di_highlight",
      artifact_id: check.artifact_id as string,
      description: check.explanation,
    }));

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold tracking-tight">Document intelligence</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Internal consistency analysis of extracted text and fields. This is not external registry verification
          and not a final authenticity decision.
        </p>
      </div>
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle>Text extraction</CardTitle>
              <CardDescription>
                {page ? `${page.source.replace("_", " ")} · ${page.quality} quality` : "No pages"}
              </CardDescription>
            </div>
            <Badge variant={result.extraction.overall_quality === "failed" ? "warning" : "muted"}>
              {result.extraction.overall_quality}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="Source" value={page?.source.replace("_", " ") ?? "—"} />
            <Metric label="Confidence" value={result.extraction.overall_confidence.toFixed(2)} />
            <Metric label="Pages" value={String(pages.length)} />
            <Metric label="Class" value={result.classification.document_class.replace("_", " ")} />
          </div>
          {pages.length > 1 ? (
            <div className="flex flex-wrap gap-2">
              {pages.map((item) => (
                <button
                  key={item.page_number}
                  type="button"
                  className={`rounded border px-2 py-1 text-xs ${item.page_number === page?.page_number ? "bg-muted font-medium" : ""}`}
                  onClick={() => setPageNumber(item.page_number)}
                >
                  Page {item.page_number}
                </button>
              ))}
            </div>
          ) : null}
          <div className="max-h-64 overflow-auto rounded-md border bg-background p-3 font-mono text-xs leading-5 whitespace-pre-wrap">
            {page?.text?.trim() ? page.text : "No text was extracted for this page."}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Structured fields</CardTitle>
          <CardDescription>Only values that were actually extracted are shown.</CardDescription>
        </CardHeader>
        <CardContent>
          {result.fields.length === 0 ? (
            <p className="text-sm text-muted-foreground">No structured fields were confidently identified.</p>
          ) : (
            <ul className="space-y-2">
              {result.fields.map((field) => (
                <li key={field.field_id} className="rounded-md border px-3 py-2 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{field.field_type.replaceAll("_", " ")}</span>
                    <span>{field.value}</span>
                    <span className="ml-auto font-mono text-xs text-muted-foreground">
                      p{field.page_number ?? "—"} · {field.confidence.toFixed(2)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle>Logical consistency</CardTitle>
              <CardDescription>{result.summary}</CardDescription>
            </div>
            <Badge variant={result.flagged ? "warning" : "muted"}>{result.suspicion_score}/100</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {result.logical_checks.length === 0 ? (
            <p className="text-sm text-muted-foreground">No consistency checks were produced.</p>
          ) : (
            <ul className="space-y-2">
              {result.logical_checks.map((check) => (
                <li key={check.check_id} className="rounded-md border px-3 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={checkVariant(check.result)}>{checkLabel(check.result)}</Badge>
                    <span className="text-sm font-medium">{check.check_id.replaceAll("_", " ")}</span>
                    <span className="text-[11px] uppercase text-muted-foreground">{check.severity}</span>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{check.explanation}</p>
                  {check.evidence.expected != null || check.evidence.observed != null ? (
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      expected {String(check.evidence.expected ?? "—")} · observed {String(check.evidence.observed ?? "—")}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          {highlightEvidence.length ? (
            <EvidenceViewer
              analysisId={analysisId}
              evidence={highlightEvidence}
              emptyLabel="No field location overlay is available."
            />
          ) : (
            <p className="text-xs text-muted-foreground">
              Findings without a reliable bounding box are listed above without a fabricated location overlay.
            </p>
          )}
        </CardContent>
      </Card>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-background px-3 py-3">
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
