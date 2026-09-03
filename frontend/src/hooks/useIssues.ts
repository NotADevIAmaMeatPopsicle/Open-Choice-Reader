import { useEffect, useState } from "react";

import { getIssueSummary } from "../api/client";
import type { IssueSummaryRecord } from "../api/types";

const EMPTY_ISSUES: IssueSummaryRecord = {
  total_count: 0,
  counts_by_severity: {},
  items: [],
};

function normalizeIssueSummary(value: unknown): IssueSummaryRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return EMPTY_ISSUES;
  }

  const candidate = value as Partial<IssueSummaryRecord>;

  return {
    total_count: typeof candidate.total_count === "number" ? candidate.total_count : 0,
    counts_by_severity:
      candidate.counts_by_severity && typeof candidate.counts_by_severity === "object"
        ? candidate.counts_by_severity
        : {},
    items: Array.isArray(candidate.items) ? candidate.items : [],
  };
}

export function useIssues() {
  const [summary, setSummary] = useState<IssueSummaryRecord>(EMPTY_ISSUES);
  const [isLoading, setIsLoading] = useState(false);

  async function refresh() {
    setIsLoading(true);

    try {
      setSummary(normalizeIssueSummary(await getIssueSummary()));
    } catch {
      setSummary(EMPTY_ISSUES);
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
