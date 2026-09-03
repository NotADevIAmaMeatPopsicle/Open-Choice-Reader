import { useEffect, useState } from "react";

import { getFriendsSummary } from "../api/client";
import type { FriendsSummaryRecord } from "../api/types";

const EMPTY_SUMMARY: FriendsSummaryRecord = {
  pending_friend_requests: 0,
  pending_shares: 0,
};

export function useFriendsSummary(): FriendsSummaryRecord {
  const [summary, setSummary] = useState<FriendsSummaryRecord>(EMPTY_SUMMARY);

  useEffect(() => {
    let isCurrent = true;

    void getFriendsSummary()
      .then((nextSummary) => {
        if (isCurrent) {
          setSummary(nextSummary);
        }
      })
      .catch(() => {
        // The badge is decorative; the Friends page itself surfaces load errors.
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  return summary;
}
