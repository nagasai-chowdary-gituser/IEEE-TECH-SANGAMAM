import { ComplianceDetail } from "@/components/compliance/compliance-detail";

export default async function ComplianceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ComplianceDetail complianceId={id} />;
}
