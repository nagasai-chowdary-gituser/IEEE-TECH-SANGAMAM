import Link from "next/link";

import { EvidenceViewer } from "@/components/analysis/evidence-viewer";
import { type KeyFindingItem } from "@/components/results/key-findings";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getArtifactUrl } from "@/lib/api";
import type { FusionLayerContribution, FusionResult, FusionTopFinding } from "@/types/analysis";

const RISK_LABEL: Record<FusionResult["risk_level"], string> = {
  LOW: "Low Manipulation Risk",
  MODERATE: "Moderate Manipulation Risk",
  ELEVATED: "Elevated Manipulation Risk",
  HIGH: "High Manipulation Risk",
  INCONCLUSIVE: "Inconclusive Assessment",
};

const ACTION_LABEL: Record<FusionResult["recommended_action"], string> = {
  NO_ADDITIONAL_ACTION: "No additional action",
  MANUAL_REVIEW_RECOMMENDED: "Manual review recommended",
  PRIORITY_MANUAL_REVIEW: "Priority manual review",
  REANALYZE_WITH_HIGHER_QUALITY_SOURCE: "Reanalyze with a higher-quality source",
};

const LAYER_LABEL: Record<FusionLayerContribution["layer"], string> = {
  metadata: "Metadata",
  ela: "ELA",
  copy_move: "Copy-Move",
  document_intelligence: "Document Intelligence",
};

function riskTone(level: FusionResult["risk_level"]): KeyFindingItem["tone"] {
  if (level === "LOW") return "success";
  if (level === "MODERATE") return "warning";
  if (level === "ELEVATED" || level === "HIGH") return "danger";
  return "muted";
}

export function forensicKeyFindings(result: FusionResult, regionCount: number | null): KeyFindingItem[] {
  const top = result.top_findings[0];
  const items: KeyFindingItem[] = [
    {
      label: "Most important finding",
      value: RISK_LABEL[result.risk_level],
      badge: result.risk_level,
      tone: riskTone(result.risk_level),
    },
    {
      label: "Evidence detected",
      value: top ? top.finding : "No ranked forensic finding was recorded.",
      detail: top ? `${LAYER_LABEL[top.layer]} · ${top.severity} severity · confidence ${percent(top.confidence)}` : undefined,
      tone: top?.severity === "high" ? "danger" : top?.severity === "medium" ? "warning" : "muted",
    },
    {
      label: "Risk / status",
      value: `${RISK_LABEL[result.risk_level]} · score ${result.overall_risk_score}/100`,
      badge: result.risk_level,
      tone: riskTone(result.risk_level),
    },
    {
      label: "Confidence / coverage",
      value: `Confidence ${percent(result.assessment_confidence)} · coverage ${percent(result.analysis_coverage)}`,
    },
    {
      label: "Recommended action",
      value: ACTION_LABEL[result.recommended_action],
    },
  ];
  if (regionCount != null) {
    items.splice(2, 0, {
      label: "Suspicious regions",
      value: `${regionCount} duplicated-region match${regionCount === 1 ? "" : "es"} recorded by copy-move analysis`,
      tone: regionCount > 0 ? "warning" : "muted",
    });
  }
  return items;
}

function riskVariant(level: FusionResult["risk_level"]) {
  if (level === "LOW") return "success" as const;
  if (level === "MODERATE") return "warning" as const;
  if (level === "ELEVATED" || level === "HIGH") return "danger" as const;
  return "muted" as const;
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function statusLabel(row: FusionLayerContribution) {
  if (row.status === "failed") return "Analysis failed";
  if (row.status === "unavailable") return "Analysis unavailable";
  if (row.status === "limited") return "Limited analysis";
  if (row.raw_score < 32 && row.effective_contribution < 22) return "No meaningful evidence found";
  return "Meaningful evidence found";
}

export function RiskAssessmentSection({
  analysisId,
  result,
}: {
  analysisId: string;
  result: FusionResult;
}) {
  return (
    <section className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Risk assessment</CardTitle>
              <CardDescription className="mt-1 max-w-2xl">
                Forensic risk assessment based on available digital evidence. This is not legal proof of
                forgery or authenticity and does not verify signer identity.
              </CardDescription>
            </div>
            <Badge variant={riskVariant(result.risk_level)}>{RISK_LABEL[result.risk_level]}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Metric label="Overall risk score" value={String(result.overall_risk_score)} />
            <Metric label="Assessment confidence" value={percent(result.assessment_confidence)} />
            <Metric label="Analysis coverage" value={percent(result.analysis_coverage)} />
            <Metric label="Recommended action" value={ACTION_LABEL[result.recommended_action]} />
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Evidence contribution</CardTitle>
          <CardDescription>How each completed layer influenced the assessment. This is not a pie chart of authenticity.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="pb-2 pr-3 font-medium">Layer</th>
                <th className="pb-2 pr-3 font-medium">Raw score</th>
                <th className="pb-2 pr-3 font-medium">Reliability</th>
                <th className="pb-2 pr-3 font-medium">Effective</th>
                <th className="pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {result.layer_contributions.map((row) => (
                <tr key={row.layer} className="border-t align-top">
                  <td className="py-3 pr-3">
                    <div className="font-medium">{LAYER_LABEL[row.layer]}</div>
                    <p className="mt-1 text-xs text-muted-foreground">{row.summary}</p>
                  </td>
                  <td className="py-3 pr-3 font-mono">{row.raw_score}</td>
                  <td className="py-3 pr-3 font-mono">{row.reliability.toFixed(2)}</td>
                  <td className="py-3 pr-3 font-mono">{row.effective_contribution.toFixed(1)}</td>
                  <td className="py-3">
                    <Badge variant={row.status === "available" ? "outline" : "muted"}>{statusLabel(row)}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {result.top_findings.length ? (
        <Card>
          <CardHeader>
            <CardTitle>Top findings</CardTitle>
            <CardDescription>Ranked from recorded evidence only. Empty when no finding exists.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {result.top_findings.map((finding) => (
              <FindingRow key={`${finding.rank}-${finding.layer}`} analysisId={analysisId} finding={finding} />
            ))}
          </CardContent>
        </Card>
      ) : null}

      {result.limitations.length ? (
        <Card>
          <CardHeader>
            <CardTitle>Limitations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {result.limitations.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-sm">{value}</dd>
    </div>
  );
}

function FindingRow({ analysisId, finding }: { analysisId: string; finding: FusionTopFinding }) {
  return (
    <div className="rounded-md border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">#{finding.rank}</span>
        <span className="text-sm font-medium">{LAYER_LABEL[finding.layer]}</span>
        <Badge variant={finding.severity === "high" ? "danger" : finding.severity === "medium" ? "warning" : "muted"}>
          {finding.severity}
        </Badge>
        <span className="text-xs text-muted-foreground">Confidence {percent(finding.confidence)}</span>
      </div>
      <p className="mt-2 text-sm">{finding.finding}</p>
      {finding.evidence_reference ? (
        <div className="mt-3 space-y-2">
          <Link
            className="text-xs underline-offset-4 hover:underline"
            href={getArtifactUrl(analysisId, finding.evidence_reference)}
            target="_blank"
          >
            Inspect evidence ({finding.evidence_reference})
          </Link>
          <EvidenceViewer
            analysisId={analysisId}
            evidence={[
              {
                type: "fusion_evidence",
                artifact_id: finding.evidence_reference,
                description: finding.finding,
              },
            ]}
            emptyLabel="No evidence image is available for this finding."
          />
        </div>
      ) : null}
    </div>
  );
}
