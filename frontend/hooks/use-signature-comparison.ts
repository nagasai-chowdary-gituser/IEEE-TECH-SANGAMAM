import { useQuery } from "@tanstack/react-query";

import { getSignatureComparison } from "@/lib/api";

export function useSignatureComparison(id: string) {
  return useQuery({
    queryKey: ["signature-comparison", id],
    queryFn: () => getSignatureComparison(id),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "PROCESSING" || status === "PENDING" ? 800 : false;
    },
  });
}
