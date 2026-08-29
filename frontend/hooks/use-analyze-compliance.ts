import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { analyzeCompliance } from "@/lib/api";
import type { ComplianceResponse } from "@/types/compliance";

export function useAnalyzeCompliance() {
  const queryClient = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: (file: File) => analyzeCompliance(file),
    onSuccess: (data: ComplianceResponse) => {
      queryClient.setQueryData(["compliance", data.compliance_id], data);
      void queryClient.invalidateQueries({ queryKey: ["compliance-list"] });
      router.push(`/compliance/${data.compliance_id}`);
    },
  });
}
