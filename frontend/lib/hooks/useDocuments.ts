import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/lib/api/client";
import type { Document, DocumentUploadRequest } from "@/types/documents";

interface DocumentApiRow {
  id: number;
  public_id: string;
  title: string;
  category: string | null;
  metadata: { size_bytes?: number; filename?: string };
  uploaded_by: number;
  original_filename: string;
  media_type: string;
  ingestion_status: Document["ingestion_status"];
  ingestion_error?: string | null;
  created_at: string;
}

function mapDocument(row: DocumentApiRow): Document {
  return {
    ...row,
    file_type: row.original_filename.split(".").pop() || "file",
    file_size: row.metadata?.size_bytes || 0,
  };
}

export function useDocuments() {
  return useQuery({
    queryKey: ["documents"],
    queryFn: async () => {
      const response = await apiClient.get<{
        documents: DocumentApiRow[];
        count: number;
      }>("/api/documents/");
      return response.data.documents.map(mapDocument);
    },
    refetchInterval: (query) => {
      const documents = query.state.data;
      return documents?.some((item) =>
        ["pending", "processing"].includes(item.ingestion_status),
      )
        ? 2_000
        : false;
    },
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: DocumentUploadRequest) => {
      const body = new FormData();
      body.append("file", payload.file);
      body.append("title", payload.title);
      if (payload.category) body.append("category", payload.category);
      return (await apiClient.post("/api/documents/upload", body)).data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (documentId: number) => {
      await apiClient.delete(`/api/documents/${documentId}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });
}

export function useCategories() {
  return useQuery({
    queryKey: ["document-categories"],
    queryFn: async () => {
      const response = await apiClient.get<{
        categories: Array<{ name: string; count: number }>;
      }>("/api/documents/categories/list");
      return response.data.categories.map((item) => item.name);
    },
  });
}
