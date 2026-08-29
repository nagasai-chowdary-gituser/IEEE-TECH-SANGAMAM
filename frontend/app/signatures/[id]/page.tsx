import { SignatureDetail } from "@/components/signature/signature-detail";

export default async function SignatureComparisonPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SignatureDetail comparisonId={id} />;
}
