import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";
import type {
  QueryHistory,
  QueryRequest,
  QueryResponse,
} from "@/types/documents";

export function useSubmitQuery() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: QueryRequest) =>
      (await apiClient.post<QueryResponse>("/api/query/", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["query-history"] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}

export function useQueryHistory() {
  return useQuery({
    queryKey: ["query-history"],
    queryFn: async () =>
      (
        await apiClient.get<{ history: QueryHistory[] }>(
          "/api/query/history?limit=50",
        )
      ).data.history,
  });
}
