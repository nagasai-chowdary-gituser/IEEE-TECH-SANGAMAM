import Link from "next/link";

import { DetailedAnalysis, KeyFindings, type KeyFindingItem } from "@/components/results/key-findings";
import { Badge } from "@/components/ui/badge";
import { formatBytes, formatTimestamp } from "@/lib/utils";
import type { ComplianceResponse, IdentifierVerification } from "@/types/compliance";

const STATUS_LABEL: Record<string, string> = {
  COMPLIANT: "Compliant",
  REVIEW_REQUIRED: "Review required",
  HIGH_RISK: "High risk",
  INCONCLUSIVE: "Inconclusive",
};

function statusVariant(status: string | null) {
  if (status === "COMPLIANT") return "success" as const;
  if (status === "REVIEW_REQUIRED") return "warning" as const;
  if (status === "HIGH_RISK") return "danger" as const;
  return "muted" as const;
}

function outcomeLabel(outcome: string | null | undefined) {
  switch (outcome) {
    case "passed":
      return "Verified through configured service";
    case "failed":
      return "Not verified by configured service";
    case "unavailable":
      return "Verification service unavailable";
    case "not_extracted":
      return "Not extracted";
    case "format_invalid":
      return "Format invalid";
    case "skipped":
      return "Skipped";
    case "error":
      return "Response unusable";
    default:
      return "Pending";
  }
}

function outcomeTone(outcome: string | null | undefined): KeyFindingItem["tone"] {
  if (outcome === "passed") return "success";
  if (outcome === "failed") return "danger";
  if (outcome === "unavailable" || outcome === "error" || outcome === "format_invalid") return "warning";
  return "muted";
}

function integrityTone(level: string | undefined): KeyFindingItem["tone"] {
  if (!level) return "muted";
  if (level.includes("NO_MEANINGFUL") || level.includes("LOW")) return "success";
  if (level.includes("HIGH") || level.includes("ELEVATED")) return "danger";
  if (level.includes("MODERATE") || level.includes("REVIEW")) return "warning";
  return "muted";
}

function complianceKeyFindings(result: ComplianceResponse): KeyFindingItem[] {
  const overall = result.overall_status ?? result.aggregation?.overall_status ?? null;
  const pan = result.pan;
  const gstin = result.gstin;
  const integrity = result.integrity;
  const items: KeyFindingItem[] = [
    {
      label: "PAN verification",
      value: outcomeLabel(pan?.outcome),
      detail: pan?.extracted_value ? `Extracted ${pan.extracted_value}` : "No PAN extracted",
      badge: pan?.outcome ?? "pending",
      tone: outcomeTone(pan?.outcome),
    },
    {
      label: "GSTIN verification",
      value: outcomeLabel(gstin?.outcome),
      detail: gstin?.extracted_value ? `Extracted ${gstin.extracted_value}` : "No GSTIN extracted",
      badge: gstin?.outcome ?? "pending",
      tone: outcomeTone(gstin?.outcome),
    },
    {
      label: "Certificate manipulation",
      value: integrity ? integrity.level.replaceAll("_", " ") : "Integrity analysis has not finished",
      detail: integrity?.top_findings[0],
      badge: integrity?.level,
      tone: integrityTone(integrity?.level),
    },
    {
      label: "Final compliance status",
      value: overall ? STATUS_LABEL[overall] ?? overall : "Pending",
      badge: overall ?? undefined,
      tone: overall === "COMPLIANT" ? "success" : overall === "HIGH_RISK" ? "danger" : overall === "REVIEW_REQUIRED" ? "warning" : "muted",
    },
  ];
  if (result.aggregation?.recommended_action) {
    items.push({
      label: "Recommended action",
      value: result.aggregation.recommended_action,
    });
  }
  return items;
}

function IdentifierCard({ title, item }: { title: string; item: IdentifierVerification | null }) {
  return (
    <section className="border bg-card p-5">
      <h3 className="text-sm font-semibold">{title}</h3>
      <dl className="mt-4 space-y-3 text-sm">
        <Row label="Extracted value" value={item?.extracted_value ?? "Not extracted"} mono />
        <Row label="Format" value={item?.format_status ?? "—"} />
        <Row label="Verification" value={outcomeLabel(item?.outcome)} />
        <Row label="Timestamp" value={item?.verified_at ? formatTimestamp(item.verified_at) : "—"} />
      </dl>
      {item?.details && Object.keys(item.details).length ? (
        <dl className="mt-4 space-y-1 text-xs text-muted-foreground">
          {Object.entries(item.details).map(([key, value]) => (
            <div key={key}>
              {key}: {String(value)}
            </div>
          ))}
        </dl>
      ) : null}
      {item?.limitation ? <p className="mt-3 text-sm text-muted-foreground">{item.limitation}</p> : null}
    </section>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className={mono ? "mt-1 font-mono text-sm" : "mt-1 text-sm"}>{value}</dd>
    </div>
  );
}

export function ComplianceResults({ result }: { result: ComplianceResponse }) {
  const overall = result.overall_status ?? result.aggregation?.overall_status ?? null;
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="space-y-5">
        <KeyFindings items={complianceKeyFindings(result)} />
        <section className="border bg-card p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">Compliance assessment</h2>
              <p className="mt-1 text-sm text-muted-foreground">Deterministic aggregation of identifier verification and certificate integrity.</p>
            </div>
            {overall ? <Badge variant={statusVariant(overall)}>{STATUS_LABEL[overall] ?? overall}</Badge> : null}
          </div>
          {result.aggregation ? (
            <p className="mt-3 text-xs text-muted-foreground">
              Concern score {result.aggregation.compliance_risk_score} / 100 · 0 means no meaningful concern detected
            </p>
          ) : (
            <p className="mt-4 text-sm text-muted-foreground">Assessment will appear when aggregation finishes.</p>
          )}
        </section>
        <IdentifierCard title="PAN verification" item={result.pan} />
        <IdentifierCard title="GSTIN verification" item={result.gstin} />
        <section className="border bg-card p-5">
          <h3 className="text-sm font-semibold">Certificate integrity</h3>
          {result.integrity ? (
            <div className="mt-4 space-y-3 text-sm">
              <p>{result.integrity.level.replaceAll("_", " ")}</p>
              <p className="text-muted-foreground">{result.integrity.summary}</p>
              {result.integrity.top_findings.length ? (
                <ul className="list-disc space-y-1 pl-5">
                  {result.integrity.top_findings.map((finding) => (
                    <li key={finding}>{finding}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground">No ranked forensic findings were recorded.</p>
              )}
              {result.forensic_analysis_id ? (
                <Link className="inline-block text-sm underline-offset-4 hover:underline" href={`/analysis/${result.forensic_analysis_id}`}>
                  Inspect forensic evidence
                </Link>
              ) : null}
              {result.integrity.limitations.length ? (
                <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                  {result.integrity.limitations.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : (
            <p className="mt-4 text-sm text-muted-foreground">Integrity analysis has not finished.</p>
          )}
        </section>
        {result.aggregation?.limitations.length ? (
          <section className="border bg-card p-5">
            <h3 className="text-sm font-semibold">Limitations</h3>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {result.aggregation.limitations.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </section>
        ) : null}
        {result.aggregation ? (
          <DetailedAnalysis>
            <p className="text-sm leading-relaxed">{result.aggregation.assessment_summary}</p>
            <p className="text-sm text-muted-foreground">{result.aggregation.recommended_action}</p>
            {result.integrity?.summary ? <p className="text-sm text-muted-foreground">{result.integrity.summary}</p> : null}
          </DetailedAnalysis>
        ) : null}
      </div>
      <aside className="space-y-4 lg:sticky lg:top-4">
        <section className="border bg-card p-5">
          <h3 className="text-sm font-semibold">Certificate</h3>
          <dl className="mt-4 space-y-3 text-sm">
            <Row label="Filename" value={result.original_filename} />
            <Row label="Type" value={(result.file_type ?? "—").toUpperCase()} />
            <Row label="Size" value={formatBytes(result.file_size)} />
            <Row label="Fingerprint" value={result.sha256_short ?? "—"} mono />
            <Row label="Enterprise" value={result.certificate_fields?.enterprise_name ?? "—"} />
            <Row label="Udyam no." value={result.certificate_fields?.udyam_number ?? "—"} mono />
          </dl>
        </section>
        <section className="border bg-card p-5">
          <h3 className="text-sm font-semibold">Check status</h3>
          <ul className="mt-3 space-y-2 text-sm">
            <li>PAN · {outcomeLabel(result.pan?.outcome)}</li>
            <li>GSTIN · {outcomeLabel(result.gstin?.outcome)}</li>
            <li>Integrity · {result.integrity?.level.replaceAll("_", " ") ?? "Pending"}</li>
          </ul>
        </section>
      </aside>
    </div>
  );
}
