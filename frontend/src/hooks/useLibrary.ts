import { useEffect, useState } from "react";

import { listDocuments } from "../api/client";
import type { DocumentRecord } from "../api/types";

interface UseLibraryResult {
  documents: DocumentRecord[];
  isLoading: boolean;
  refresh: () => Promise<void>;
}

export function useLibrary(): UseLibraryResult {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  async function refresh() {
    setIsLoading(true);

    try {
      setDocuments(await listDocuments());
    } catch {
      setDocuments([]);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return {
    documents,
    isLoading,
    refresh,
  };
}
