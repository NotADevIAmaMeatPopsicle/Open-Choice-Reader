import { useEffect, useRef, useState } from "react";

import { cancelExportJob, listJobs, retryExportJob } from "../api/client";
import type { JobRecord } from "../api/types";

interface UseJobsResult {
  actionError: string | null;
  cancelJob: (jobId: number) => Promise<void>;
  error: string | null;
  isMutatingJobId: number | null;
  jobs: JobRecord[];
  isLoading: boolean;
  refresh: () => Promise<void>;
  retryJob: (jobId: number) => Promise<void>;
}

const ACTIVE_JOB_STATUSES = new Set(["queued", "processing", "cancel_requested"]);
const JOBS_POLL_INTERVAL_MS = 4000;

let cachedJobs: JobRecord[] = [];
let hasLoadedJobs = false;
let latestJobsRequestId = 0;
let jobsPollIntervalId: ReturnType<typeof setInterval> | null = null;

const listeners = new Set<(jobs: JobRecord[]) => void>();

function syncJobsPolling() {
  const shouldPoll = listeners.size > 0 && cachedJobs.some((job) => ACTIVE_JOB_STATUSES.has(job.status));

  if (shouldPoll && jobsPollIntervalId === null) {
    jobsPollIntervalId = setInterval(() => {
      if (document.hidden) {
        return;
      }
      void refreshJobsCache().catch(() => {
        // Polling is best effort; the queue refreshes again on the next tick or interaction.
      });
    }, JOBS_POLL_INTERVAL_MS);
  } else if (!shouldPoll && jobsPollIntervalId !== null) {
    clearInterval(jobsPollIntervalId);
    jobsPollIntervalId = null;
  }
}

function publishJobs(nextJobs: JobRecord[]) {
  cachedJobs = nextJobs;
  hasLoadedJobs = true;
  listeners.forEach((listener) => {
    listener(nextJobs);
  });
  syncJobsPolling();
}

export async function refreshJobsCache(): Promise<JobRecord[]> {
  const requestId = latestJobsRequestId + 1;
  latestJobsRequestId = requestId;
  const jobs = await listJobs();
  if (requestId === latestJobsRequestId) {
    publishJobs(jobs);
  }
  return jobs;
}

export function resetJobsCacheForTests() {
  cachedJobs = [];
  hasLoadedJobs = false;
  latestJobsRequestId = 0;
  if (jobsPollIntervalId !== null) {
    clearInterval(jobsPollIntervalId);
    jobsPollIntervalId = null;
  }
  listeners.clear();
}

export function useJobs(): UseJobsResult {
  const [actionError, setActionError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isMutatingJobId, setIsMutatingJobId] = useState<number | null>(null);
  const [jobs, setJobs] = useState<JobRecord[]>(cachedJobs);
  const [isLoading, setIsLoading] = useState(!hasLoadedJobs);
  const isMountedRef = useRef(true);

  async function refresh() {
    const hasCachedJobHistory = hasLoadedJobs && cachedJobs.length > 0;
    if (isMountedRef.current) {
      setIsLoading(true);
      setError(null);
    }

    try {
      await refreshJobsCache();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load export jobs";
      if (isMountedRef.current) {
        setError(hasCachedJobHistory ? `${message}. Showing last known queue.` : message);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }

  async function runMutation(jobId: number, action: "cancel" | "retry") {
    if (isMountedRef.current) {
      setActionError(null);
      setIsMutatingJobId(jobId);
    }

    try {
      if (action === "cancel") {
        await cancelExportJob(jobId);
      } else {
        await retryExportJob(jobId);
      }
      await refreshJobsCache();
    } catch (error) {
      if (isMountedRef.current) {
        setActionError(error instanceof Error ? error.message : "Unable to update export job");
      }
    } finally {
      if (isMountedRef.current) {
        setIsMutatingJobId(null);
      }
    }
  }

  useEffect(() => {
    isMountedRef.current = true;
    listeners.add(setJobs);
    syncJobsPolling();
    return () => {
      isMountedRef.current = false;
      listeners.delete(setJobs);
      syncJobsPolling();
    };
  }, []);

  useEffect(() => {
    void refresh();
  }, []);

  return {
    actionError,
    cancelJob: async (jobId: number) => {
      await runMutation(jobId, "cancel");
    },
    error,
    isMutatingJobId,
    jobs,
    isLoading,
    refresh,
    retryJob: async (jobId: number) => {
      await runMutation(jobId, "retry");
    },
  };
}
