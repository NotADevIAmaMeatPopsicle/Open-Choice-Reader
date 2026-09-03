import { useEffect, useState } from "react";

import { getDocumentSummary } from "../api/client";
import type { DocumentSummaryRecord } from "../api/types";

const EMPTY_SUMMARY: DocumentSummaryRecord = {
  continue_reading: [],
  recent_documents: [],
};

export function useHomeSummary() {
  const [summary, setSummary] = useState<DocumentSummaryRecord>(EMPTY_SUMMARY);
  const [isLoading, setIsLoading] = useState(false);

  async function refresh() {
    setIsLoading(true);

    try {
      setSummary(await getDocumentSummary());
    } catch {
      setSummary(EMPTY_SUMMARY);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return {
    summary,
    isLoading,
    refresh,
  };
}
