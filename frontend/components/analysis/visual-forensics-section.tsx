import { CopyMovePanel } from "@/components/analysis/copy-move-panel";
import { ElaPanel } from "@/components/analysis/ela-panel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalysisResponse } from "@/types/analysis";

export function VisualForensicsSection({ analysis }: { analysis: AnalysisResponse }) {
  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold tracking-tight">Visual forensics</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Independent ELA and copy-move modules. These are suspicion signals, not a forgery verdict.
        </p>
      </div>
      {analysis.ela ? <ElaPanel analysisId={analysis.analysis_id} result={analysis.ela} /> : null}
      {analysis.copy_move ? <CopyMovePanel analysisId={analysis.analysis_id} result={analysis.copy_move} /> : null}
      <Card>
        <CardHeader>
          <CardTitle>Analysis limitations</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>{analysis.layers_completed}</p>
          <p>{analysis.pipeline_message}</p>
          <p>
            Visual modules remain independent evidence sources. Overall interpretation is the risk assessment, not a legal authenticity verdict.
          </p>
        </CardContent>
      </Card>
    </section>
  );
}
