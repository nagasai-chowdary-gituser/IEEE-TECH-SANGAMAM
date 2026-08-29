import { useQuery } from "@tanstack/react-query";

import { listSignatureComparisons } from "@/lib/api";

export function useSignatureHistory(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ["signature-history", limit, offset],
    queryFn: () => listSignatureComparisons(limit, offset),
  });
}
