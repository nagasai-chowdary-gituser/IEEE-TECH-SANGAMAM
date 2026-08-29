import { AnalysisDetail } from "@/components/analysis/analysis-detail";

export default async function AnalysisPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <AnalysisDetail analysisId={id} />;
}
