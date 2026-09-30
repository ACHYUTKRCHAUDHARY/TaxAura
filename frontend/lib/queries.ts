"use client";
import { useQuery } from "@tanstack/react-query";
import { api, Document } from "./api";
import { useUser } from "@/components/workspace";
export function useDocuments() {
  const user = useUser();
  return useQuery({
    queryKey: ["documents", user.id],
    queryFn: ({ signal }) => api<Document[]>("/documents", { signal }),
    refetchInterval: (query) =>
      query.state.data?.some((doc) =>
        ["QUEUED", "PROCESSING"].includes(doc.processing_status),
      )
        ? 3000
        : false,
  });
}
