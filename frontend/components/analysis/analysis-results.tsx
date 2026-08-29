import Link from "next/link";

import { DocumentIntelligenceSection } from "@/components/analysis/document-intelligence-section";
import { DocumentOverview } from "@/components/analysis/document-overview";
import { ExplanationGate } from "@/components/analysis/explanation-gate";
import { MetadataPanel } from "@/components/analysis/metadata-panel";
import { PreprocessingPanel } from "@/components/analysis/preprocessing-panel";
import { forensicKeyFindings, RiskAssessmentSection } from "@/components/analysis/risk-assessment-section";
import { VisualForensicsSection } from "@/components/analysis/visual-forensics-section";
import { DetailedAnalysis, KeyFindings } from "@/components/results/key-findings";
import type { AnalysisResponse } from "@/types/analysis";

export function AnalysisResults({
  analysis,
  showDetailLink = false,
}: {
  analysis: AnalysisResponse;
  showDetailLink?: boolean;
}) {
  const regionCount = analysis.copy_move
    ? analysis.copy_move.pages.reduce((total, page) => total + page.regions.length, 0)
    : null;
  return (
    <div className="space-y-4">
      {showDetailLink ? (
        <p className="text-sm text-muted-foreground">
          Analysis ID{" "}
          <Link className="font-mono text-foreground underline-offset-4 hover:underline" href={`/analysis/${analysis.analysis_id}`}>
            {analysis.analysis_id}
          </Link>
        </p>
      ) : null}
      {analysis.fusion ? <KeyFindings items={forensicKeyFindings(analysis.fusion, regionCount)} /> : null}
      <DocumentOverview analysis={analysis} />
      {analysis.fusion ? <RiskAssessmentSection analysisId={analysis.analysis_id} result={analysis.fusion} /> : null}
      {analysis.fusion ? (
        <DetailedAnalysis>
          <p className="text-sm leading-relaxed">{analysis.fusion.assessment_summary}</p>
          <p className="text-sm text-muted-foreground">{analysis.fusion.corroboration.description}</p>
          {analysis.fusion.limitations.length ? (
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {analysis.fusion.limitations.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          ) : null}
          <ExplanationGate analysisId={analysis.analysis_id} explanation={analysis.explanation} status={analysis.status} />
        </DetailedAnalysis>
      ) : (
        <ExplanationGate analysisId={analysis.analysis_id} explanation={analysis.explanation} status={analysis.status} />
      )}
      <details className="rounded-lg border bg-card p-5">
        <summary className="cursor-pointer text-sm font-semibold">Technical evidence</summary>
        <p className="mt-1 text-sm text-muted-foreground">
          Inspect preprocessing, metadata, visual forensics, and document intelligence for this analysis.
        </p>
        <div className="mt-4 space-y-4">
          {analysis.preprocessing ? <PreprocessingPanel result={analysis.preprocessing} /> : null}
          {analysis.metadata_forensics ? <MetadataPanel result={analysis.metadata_forensics} /> : null}
          {analysis.ela || analysis.copy_move ? <VisualForensicsSection analysis={analysis} /> : null}
          {analysis.document_intelligence ? (
            <DocumentIntelligenceSection analysisId={analysis.analysis_id} result={analysis.document_intelligence} />
          ) : null}
        </div>
      </details>
    </div>
  );
}
