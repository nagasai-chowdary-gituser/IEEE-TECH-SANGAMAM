import { useQuery } from "@tanstack/react-query";

import { listCompliance } from "@/lib/api";

export function useComplianceHistory(limit: number, offset: number) {
  return useQuery({
    queryKey: ["compliance-list", limit, offset],
    queryFn: () => listCompliance(limit, offset),
  });
}
