import Link from "next/link";

import { ExplanationGate } from "@/components/analysis/explanation-gate";
import { DetailedAnalysis, KeyFindings, type KeyFindingItem } from "@/components/results/key-findings";
import { CertificateOverlay } from "@/components/signature/certificate-overlay";
import { Badge } from "@/components/ui/badge";
import { getSignatureArtifactUrl } from "@/lib/api";
import type { CertificateIntegrityAssessment, SignatureComparisonResponse, StreamAssessment } from "@/types/signature";

function statusVariant(status: string) {
  if (status.includes("CLEAR") || status.includes("NO_SIGNIFICANT") || status.includes("HIGH_REFERENCE") || status.includes("LOW_MANIPULATION")) return "success" as const;
  if (status.includes("HIGH_MANIPULATION") || status.includes("POTENTIAL_MISMATCH") || status.includes("ELEVATED")) return "danger" as const;
  if (status.includes("REVIEW") || status.includes("MODERATE") || status.includes("AWAITING")) return "warning" as const;
  return "muted" as const;
}

function pretty(status: string) {
  return status.replaceAll("_", " ");
}

function streamTone(status: string): KeyFindingItem["tone"] {
  if (status.includes("CLEAR") || status.includes("NO_SIGNIFICANT") || status.includes("HIGH_REFERENCE") || status.includes("LOW_MANIPULATION")) return "success";
  if (status.includes("HIGH_MANIPULATION") || status.includes("POTENTIAL_MISMATCH") || status.includes("ELEVATED")) return "danger";
  if (status.includes("REVIEW") || status.includes("MODERATE") || status.includes("AWAITING")) return "warning";
  return "muted";
}

function certificateKeyFindings(cert: CertificateIntegrityAssessment): KeyFindingItem[] {
  const suspicious = cert.overlay_regions.find((item) => item.kind === "copy_move" || item.kind === "text" || item.kind === "suspicious");
  const top = cert.top_findings[0];
  const items: KeyFindingItem[] = [
    {
      label: "Overall certificate integrity",
      value: pretty(cert.overall_status),
      badge: cert.overall_status,
      tone: streamTone(cert.overall_status),
    },
    {
      label: "Document content integrity",
      value: pretty(cert.document_content.status),
      detail: cert.document_content.findings[0],
      badge: cert.document_content.status,
      tone: streamTone(cert.document_content.status),
    },
    {
      label: "Signature integrity",
      value: pretty(cert.signature_integrity.status),
      detail: cert.signature_integrity.findings[0],
      badge: cert.signature_integrity.status,
      tone: streamTone(cert.signature_integrity.status),
    },
  ];
  if (cert.reference_comparison) {
    items.push({
      label: "Reference signature comparison",
      value: pretty(cert.reference_comparison.status),
      detail: cert.reference_comparison.findings[0],
      badge: cert.reference_comparison.status,
      tone: streamTone(cert.reference_comparison.status),
    });
  }
  items.push({
    label: "Top suspicious region / finding",
    value: suspicious ? `${suspicious.label}: ${suspicious.explanation}` : top ? top.finding : "No localized suspicious region was recorded.",
    tone: suspicious || (top && top.strength === "high") ? "warning" : "muted",
  });
  items.push({
    label: "Recommended action",
    value: cert.recommended_action,
  });
  return items;
}

function StreamCard({ title, question, stream }: { title: string; question: string; stream: StreamAssessment }) {
  return (
    <section className="border bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          <p className="mt-1 text-xs text-muted-foreground">{question}</p>
        </div>
        <Badge variant={statusVariant(stream.status)}>{pretty(stream.status)}</Badge>
      </div>
      {stream.findings.length ? (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {stream.findings.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">{stream.summary}</p>
      )}
      {stream.confidence != null ? (
        <p className="mt-3 text-xs text-muted-foreground">Confidence {Math.round(stream.confidence * 100)}%</p>
      ) : null}
      {stream.limitations.length ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
          {stream.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function EvidenceImage({ src, label }: { src: string; label: string }) {
  return (
    <figure className="border bg-background p-2">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={label} className="max-h-40 w-full object-contain" />
      <figcaption className="mt-2 text-[11px] uppercase tracking-wide text-muted-foreground">{label}</figcaption>
    </figure>
  );
}

export function SignatureResults({ result }: { result: SignatureComparisonResponse }) {
  const cert = result.certificate;
  const id = result.comparison_id;
  if (!cert) {
    return (
      <div className="border bg-card p-5 text-sm text-muted-foreground">
        Full certificate assessment is not available on this saved record. Run a new analysis to generate the Certificate Analyzer output.
      </div>
    );
  }
  return (
    <div className="space-y-5">
      <KeyFindings items={certificateKeyFindings(cert)} />

      <section className="border bg-card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold">Certificate integrity</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Confidence {Math.round(cert.confidence * 100)}% · coverage {Math.round(cert.analysis_coverage * 100)}%
            </p>
          </div>
          <Badge variant={statusVariant(cert.overall_status)}>{pretty(cert.overall_status)}</Badge>
        </div>
      </section>

      <section className="border bg-card p-5">
        <h3 className="text-sm font-semibold">Document overview</h3>
        <p className="mt-1 text-sm text-muted-foreground">{result.original_filename}</p>
        {result.artifacts.page_preview ? (
          <div className="mt-4">
            <CertificateOverlay imageUrl={getSignatureArtifactUrl(id, "page-preview")} regions={cert.overlay_regions} />
          </div>
        ) : null}
        {cert.extracted_fields.length ? (
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            {cert.extracted_fields.map((field) => (
              <div key={field.field_id}>
                <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{field.label}</dt>
                <dd className="mt-1">{field.value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="mt-3 text-xs text-muted-foreground">No structured certificate fields were extracted. Fields are shown only when OCR actually detected them.</p>
        )}
      </section>

      <StreamCard
        title="Document content integrity"
        question="Does the full certificate contain forensic evidence consistent with digital alteration or manipulation?"
        stream={cert.document_content}
      />
      <StreamCard
        title="Signature integrity"
        question="Does the signature region contain forensic evidence consistent with digital insertion or manipulation?"
        stream={cert.signature_integrity}
      />
      {cert.reference_comparison ? (
        <section className="border bg-card p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold">Reference signature comparison</h3>
              <p className="mt-1 text-xs text-muted-foreground">How similar is the certificate signature to the authorized reference supplied for comparison?</p>
            </div>
            <Badge variant={statusVariant(cert.reference_comparison.status)}>{pretty(cert.reference_comparison.status)}</Badge>
          </div>
          {result.fusion ? (
            <p className="mt-3 text-xs text-muted-foreground">Technical similarity {result.fusion.similarity_score}/100. This does not establish signer identity.</p>
          ) : null}
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {result.artifacts.document_signature ? (
              <EvidenceImage src={getSignatureArtifactUrl(id, "document-signature")} label="Certificate signature" />
            ) : null}
            {result.artifacts.reference_normalized ? (
              <EvidenceImage src={getSignatureArtifactUrl(id, "reference-normalized")} label="Normalized reference" />
            ) : null}
            {result.artifacts.overlay ? <EvidenceImage src={getSignatureArtifactUrl(id, "overlay")} label="Overlay" /> : null}
          </div>
        </section>
      ) : (
        <section className="border bg-card p-5">
          <h3 className="text-sm font-semibold">Reference signature comparison</h3>
          <p className="mt-3 text-sm text-muted-foreground">Not requested for this analysis.</p>
        </section>
      )}

      {result.artifacts.document_signature && !cert.reference_comparison ? (
        <section className="border bg-card p-5">
          <h3 className="text-sm font-semibold">Signature evidence</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <EvidenceImage src={getSignatureArtifactUrl(id, "document-signature")} label="Confirmed signature crop" />
            {result.artifacts.document_normalized ? (
              <EvidenceImage src={getSignatureArtifactUrl(id, "document-normalized")} label="Normalized signature" />
            ) : null}
          </div>
        </section>
      ) : null}

      <section className="border bg-card p-5">
        <h3 className="text-sm font-semibold">Top findings</h3>
        <ol className="mt-3 space-y-2 text-sm">
          {cert.top_findings.map((item) => (
            <li key={`${item.rank}-${item.stream}`}>
              <span className="font-medium">
                {item.rank}. {pretty(item.stream)} — {item.strength} evidence.
              </span>{" "}
              <span className="text-muted-foreground">{item.finding}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="border bg-card p-5">
        <h3 className="text-sm font-semibold">Limitations</h3>
        <p className="mt-1 text-xs text-muted-foreground">Completed: {cert.completed_checks.join(", ") || "—"}</p>
        <p className="mt-1 text-xs text-muted-foreground">Unavailable: {cert.unavailable_checks.join(", ") || "None recorded"}</p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {cert.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      {result.forensic_analysis_id ? (
        <div className="space-y-3">
          <DetailedAnalysis>
            <p className="text-sm leading-relaxed">{cert.summary}</p>
            <p className="text-sm text-muted-foreground">{cert.recommended_action}</p>
            <ExplanationGate analysisId={result.forensic_analysis_id} explanation={null} status={result.forensic_status === "COMPLETE" ? "COMPLETE" : "PROCESSING"} />
          </DetailedAnalysis>
          <Link className="text-sm underline-offset-4 hover:underline" href={`/analysis/${result.forensic_analysis_id}`}>
            Open linked forensic analysis
          </Link>
        </div>
      ) : (
        <DetailedAnalysis>
          <p className="text-sm leading-relaxed">{cert.summary}</p>
          <p className="text-sm text-muted-foreground">{cert.recommended_action}</p>
        </DetailedAnalysis>
      )}
    </div>
  );
}
