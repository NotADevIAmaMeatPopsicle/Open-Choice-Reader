import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { withAuthenticatedAppFetch } from "./support/authSessionFetch";

describe("IssuesPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
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
              {
                id: "engine-warning-piper",
                issue_type: "engine_warning",
                severity: "warning",
                title: "Fast reader is degraded",
                detail: "Piper binary missing",
                action_label: "Open settings",
                action_path: "/settings",
                document_id: null,
              },
            ],
          }),
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

  it("renders actionable issue cards and navigates to the recovery route", async () => {
    window.history.pushState({}, "", "/issues");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Issues" })).toBeInTheDocument();
    expect(await screen.findByText("Export failed for Brave New World")).toBeInTheDocument();
    expect(await screen.findByText("Fast reader is degraded")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open jobs" }));

    expect(await screen.findByRole("heading", { name: "Export Queue" })).toBeInTheDocument();
  });
});
