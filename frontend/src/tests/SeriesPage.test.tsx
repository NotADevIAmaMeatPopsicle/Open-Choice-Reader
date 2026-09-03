import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

describe("SeriesPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 1,
              title: "Wool #1 - Holston",
              format: "epub",
              status: "ready",
              author: "Hugh Howey",
              cover_url: "/api/documents/1/cover",
              summary: "Part one",
              total_sections: 12,
              total_chunks: 120,
              estimated_duration_seconds: 720,
              current_chunk_index: null,
              progress_percent: 0,
              last_opened_at: null,
            },
            {
              id: 2,
              title: "Wool #2 - Proper Gauge",
              format: "epub",
              status: "ready",
              author: "Hugh Howey",
              cover_url: "/api/documents/2/cover",
              summary: "Part two",
              total_sections: 12,
              total_chunks: 120,
              estimated_duration_seconds: 720,
              current_chunk_index: null,
              progress_percent: 0,
              last_opened_at: null,
            },
            {
              id: 3,
              title: "Standalone Novel",
              format: "epub",
              status: "ready",
              author: "Someone Else",
              cover_url: "/api/documents/3/cover",
              summary: "No series",
              total_sections: 8,
              total_chunks: 80,
              estimated_duration_seconds: 480,
              current_chunk_index: null,
              progress_percent: 0,
              last_opened_at: null,
            },
          ],
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

  it("groups multi-book series and opens a title from the group", async () => {
    window.history.pushState({}, "", "/series");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Series" })).toBeInTheDocument();
    expect(await screen.findByText("Wool")).toBeInTheDocument();
    expect(screen.getByText("2 books")).toBeInTheDocument();
    expect(screen.queryByText("Standalone Novel")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open Wool #2 - Proper Gauge" }));

    expect(await screen.findByRole("heading", { name: "Wool #2 - Proper Gauge" })).toBeInTheDocument();
  });
});
