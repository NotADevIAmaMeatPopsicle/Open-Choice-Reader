import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { refreshJobsCache, resetJobsCacheForTests } from "../hooks/useJobs";
import { withAuthenticatedAppFetch } from "./support/authSessionFetch";

function buildJob(overrides: Record<string, unknown> = {}) {
  return {
    id: 7,
    document_id: 3,
    voice_preset_id: "default",
    format: "wav",
    status: "queued",
    split_chapters: false,
    artifact_basename: "alice-reader-mvp",
    progress_percent: 0,
    status_detail: "Queued for export",
    download_url: null,
    failure_detail: null,
    artifacts: [],
    can_retry: false,
    can_cancel: true,
    ...overrides,
  };
}

function createDeferredValue<T>() {
  let resolve: (value: T) => void = () => undefined;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });

  return { promise, resolve };
}

describe("JobsPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    resetJobsCacheForTests();
    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/jobs") {
        return Promise.resolve({
          ok: true,
          json: async () => [buildJob()],
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    resetJobsCacheForTests();
    window.history.pushState({}, "", "/");
    vi.unstubAllGlobals();
  });

  it("summarizes queue health in Alice-facing language and keeps top-level navigation available", async () => {
    window.history.pushState({}, "", "/jobs");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/jobs") {
        return Promise.resolve({
          ok: true,
          json: async () => [
            buildJob({
              id: 6,
              document_id: 2,
              voice_preset_id: "10",
              status: "processing",
              progress_percent: 42,
              status_detail: "Rendering chunk 5 of 12",
            }),
            buildJob({
              id: 7,
              voice_preset_id: "11",
              status: "completed",
              artifact_basename: "alice-reader-mvp-nightly",
              progress_percent: 100,
              status_detail: "Export ready",
              can_cancel: false,
              artifacts: [
                {
                  artifact_id: "0",
                  download_url: "/api/jobs/7/download",
                  filename: "alice-reader-mvp-nightly.wav",
                  label: "Merged audiobook",
                  section_title: null,
                },
              ],
            }),
            buildJob({
              id: 8,
              document_id: 9,
              voice_preset_id: "12",
              status: "failed",
              split_chapters: true,
              artifact_basename: "alice-reader-failure",
              progress_percent: 58,
              failure_detail: "Preset audio generation timed out",
              can_retry: true,
              can_cancel: false,
            }),
            buildJob({
              id: 9,
              document_id: 10,
              voice_preset_id: "13",
              status: "queued",
            }),
          ],
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Export Queue" })).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/jobs");
    });

    expect(await screen.findByText(/4 exports tracked/i)).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Queue summary" })).toHaveTextContent("1queued up");
    expect(screen.getByRole("list", { name: "Queue summary" })).toHaveTextContent("1rendering now");
    expect(screen.getByRole("list", { name: "Queue summary" })).toHaveTextContent("1ready to download");
    expect(screen.getByRole("list", { name: "Queue summary" })).toHaveTextContent("1needs attention");
    expect(screen.getByText("Document 3")).toBeInTheDocument();
    expect(screen.getByText("Preset 11")).toBeInTheDocument();
    expect(screen.getAllByText("Ready to download").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Merged audiobook" })).toHaveAttribute(
      "href",
      "/api/jobs/7/download",
    );
    expect(screen.getByText("alice-reader-mvp-nightly.wav")).toBeInTheDocument();
    expect(screen.getByText("Document 9")).toBeInTheDocument();
    expect(screen.getByText("Preset 12")).toBeInTheDocument();
    expect(screen.getAllByText("Needs attention").length).toBeGreaterThan(0);
    expect(screen.getByText("Preset audio generation timed out")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "Library" }));

    expect(await screen.findByRole("heading", { name: "Library" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/");
  });

  it("shows a jobs load error instead of a fake empty queue state", async () => {
    window.history.pushState({}, "", "/jobs");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/jobs") {
        return Promise.resolve({
          ok: false,
          status: 503,
          json: async () => ({
            detail: "Jobs service offline",
          }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Jobs service offline");
    expect(screen.queryByText("No export jobs yet.")).not.toBeInTheDocument();
  });

  it("marks cached job history as stale when refresh fails after a warm load", async () => {
    window.history.pushState({}, "", "/jobs");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/jobs") {
        return Promise.resolve({
          ok: true,
          json: async () => [buildJob({ voice_preset_id: "11" })],
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    const firstRender = render(<App />);
    expect(await screen.findByText(/1 exports tracked/i)).toBeInTheDocument();
    expect(screen.getByText("Document 3")).toBeInTheDocument();

    firstRender.unmount();

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/jobs") {
        return Promise.resolve({
          ok: false,
          status: 503,
          json: async () => ({
            detail: "Jobs service offline",
          }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Jobs service offline. Showing last known queue.",
    );
    expect(screen.getByText("Document 3")).toBeInTheDocument();
    expect(screen.queryByText("No export jobs yet.")).not.toBeInTheDocument();
  });

  it("falls back to the response status when jobs errors do not return json", async () => {
    window.history.pushState({}, "", "/jobs");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/jobs") {
        return Promise.resolve({
          ok: false,
          status: 502,
          json: async () => {
            throw new SyntaxError("Unexpected token < in JSON");
          },
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Request failed with status 502");
  });

  it("does not log stale-update warnings when the jobs page unmounts mid-refresh", async () => {
    window.history.pushState({}, "", "/jobs");

    const pendingJobsRequest = createDeferredValue<{
      json: () => Promise<Array<Record<string, unknown>>>;
      ok: boolean;
      status: number;
    }>();
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/jobs") {
        return pendingJobsRequest.promise;
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    const rendered = render(<App />);
    rendered.unmount();

    await act(async () => {
      pendingJobsRequest.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      });
      await Promise.resolve();
    });

    expect(consoleErrorSpy).not.toHaveBeenCalled();
    consoleErrorSpy.mockRestore();
  });

  it("keeps newer job refresh results when overlapping requests resolve out of order", async () => {
    window.history.pushState({}, "", "/jobs");

    const firstJobsRequest = createDeferredValue<{
      json: () => Promise<Array<Record<string, unknown>>>;
      ok: boolean;
      status: number;
    }>();
    const secondJobsRequest = createDeferredValue<{
      json: () => Promise<Array<Record<string, unknown>>>;
      ok: boolean;
      status: number;
    }>();
    let requestCount = 0;

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/jobs") {
        requestCount += 1;
        return requestCount === 1 ? firstJobsRequest.promise : secondJobsRequest.promise;
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    void refreshJobsCache();

    secondJobsRequest.resolve({
      ok: true,
      status: 200,
      json: async () => [buildJob({ id: 8, document_id: 9, voice_preset_id: "12" })],
    });

    expect(await screen.findByText("Document 9")).toBeInTheDocument();

    firstJobsRequest.resolve({
      ok: true,
      status: 200,
      json: async () => [buildJob({ voice_preset_id: "11" })],
    });

    await waitFor(() => {
      expect(screen.getByText("Document 9")).toBeInTheDocument();
    });
    expect(screen.queryByText("Document 3")).not.toBeInTheDocument();
  });

  it("surfaces unknown backend job statuses instead of presenting them as queued", async () => {
    window.history.pushState({}, "", "/jobs");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL) => {
      if (typeof input === "string" && input === "/api/jobs") {
        return Promise.resolve({
          ok: true,
          json: async () => [buildJob({ id: 17, document_id: 7, voice_preset_id: "11", status: "waiting_on_gpu" })],
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText(/1 exports tracked/i)).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Queue summary" })).toHaveTextContent("1unexpected status");
    expect(screen.getByText("Unexpected status: waiting_on_gpu")).toBeInTheDocument();
    expect(screen.getByText("This export reported a new or unrecognized backend status.")).toBeInTheDocument();
    expect(screen.queryByText("Queued up")).not.toBeInTheDocument();
  });

  it("lets Alice cancel queued work and retry a failed export attempt", async () => {
    window.history.pushState({}, "", "/jobs");

    let jobs = [
      buildJob({
        id: 5,
        document_id: 2,
        voice_preset_id: "11",
        status: "queued",
        can_cancel: true,
      }),
      buildJob({
        id: 6,
        document_id: 3,
        voice_preset_id: "12",
        status: "failed",
        can_retry: true,
        can_cancel: false,
        failure_detail: "Qwen worker crashed",
      }),
    ];

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/jobs" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => jobs,
        });
      }

      if (typeof input === "string" && input === "/api/jobs/5/cancel" && init?.method === "POST") {
        jobs = [
          buildJob({
            id: 5,
            document_id: 2,
            voice_preset_id: "11",
            status: "canceled",
            can_retry: true,
            can_cancel: false,
            status_detail: "Canceled before processing",
          }),
          jobs[1],
        ];
        return Promise.resolve({
          ok: true,
          json: async () => jobs[0],
        });
      }

      if (typeof input === "string" && input === "/api/jobs/6/retry" && init?.method === "POST") {
        jobs = [
          jobs[0],
          jobs[1],
          buildJob({
            id: 9,
            document_id: 3,
            voice_preset_id: "12",
            status: "queued",
            can_cancel: true,
            can_retry: false,
          }),
        ];
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => jobs[2],
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("Document 2")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Cancel export" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/jobs/5/cancel", {
        method: "POST",
      });
    });
    expect(await screen.findByText("Canceled")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Retry export" })[1]!);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/jobs/6/retry", {
        method: "POST",
      });
    });
    expect(await screen.findByText("Job 9")).toBeInTheDocument();
  });
});
