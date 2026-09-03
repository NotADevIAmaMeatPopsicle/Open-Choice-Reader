import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

describe("HomePage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents/summary" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            continue_reading: [
              {
                id: 3,
                title: "Brave New World",
                format: "epub",
                status: "ready",
                author: "Aldous Huxley",
                cover_url: "/api/documents/3/cover",
                summary: "A dystopian future",
                total_sections: 10,
                total_chunks: 100,
                estimated_duration_seconds: 600,
                current_chunk_index: 40,
                progress_percent: 40,
                last_opened_at: "2026-05-08T01:00:00Z",
              },
            ],
            recent_documents: [],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/issues" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            total_count: 2,
            counts_by_severity: { error: 1, warning: 1 },
            items: [
              {
                id: "job-failure-7",
                issue_type: "export_failure",
                severity: "error",
                title: "Export failed for Brave New World",
                detail: "Worker crashed",
                action_label: "Open jobs",
                action_path: "/jobs",
                document_id: 3,
              },
            ],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/documents/inbox" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              name: "incoming.md",
              path: "incoming.md",
              format: "md",
              document_id: null,
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [],
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
    window.history.pushState({}, "", "/");
    vi.unstubAllGlobals();
  });

  it("shows continue-reading shelves plus issue and inbox summary widgets", async () => {
    window.history.pushState({}, "", "/home");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Home" })).toBeInTheDocument();
    expect(await screen.findByText("Brave New World")).toBeInTheDocument();
    expect(screen.getByText("2 issues need attention")).toBeInTheDocument();
    expect(screen.getByText("1 file waiting in the inbox")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open issues" }));

    expect(await screen.findByRole("heading", { name: "Issues" })).toBeInTheDocument();
  });
});
