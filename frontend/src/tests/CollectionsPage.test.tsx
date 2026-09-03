import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

type TestCollectionDocument = {
  id: number;
  title: string;
  author: string | null;
  cover_url: string;
  progress_percent: number;
};

type TestCollection = {
  id: number;
  name: string;
  description: string | null;
  document_count: number;
  documents: TestCollectionDocument[];
};

describe("CollectionsPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    let collections: TestCollection[] = [
      {
        id: 1,
        name: "Favorites",
        description: "Alice's keepers",
        document_count: 0,
        documents: [],
      },
    ];

    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/collections" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => collections,
        });
      }

      if (typeof input === "string" && input === "/api/collections" && init?.method === "POST") {
        collections = [
          ...collections,
          {
            id: 2,
            name: "Night Queue",
            description: null,
            document_count: 0,
            documents: [],
          },
        ];
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => collections[1],
        });
      }

      if (typeof input === "string" && input === "/api/collections/1/documents" && init?.method === "POST") {
        collections = [
          {
            id: 1,
            name: "Favorites",
            description: "Alice's keepers",
            document_count: 1,
            documents: [
              {
                id: 7,
                title: "Alice Reader MVP",
                author: null,
                cover_url: "/api/documents/7/cover",
                progress_percent: 0,
              },
            ],
          },
          collections[1] ?? {
            id: 2,
            name: "Night Queue",
            description: null,
            document_count: 0,
            documents: [],
          },
        ];
        return Promise.resolve({
          ok: true,
          json: async () => collections[0],
        });
      }

      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
              author: null,
              cover_url: "/api/documents/7/cover",
              summary: "A walkthrough.",
              total_sections: 2,
              total_chunks: 2,
              estimated_duration_seconds: 12,
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

  it("creates manual collections and adds a book to one of them", async () => {
    window.history.pushState({}, "", "/collections");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Collections" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Collection name"), {
      target: { value: "Night Queue" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create collection" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/collections", {
        body: JSON.stringify({ name: "Night Queue", description: "" }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
    });

    fireEvent.change(screen.getByLabelText("Add book to Favorites"), {
      target: { value: "7" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add to Favorites" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/collections/1/documents", {
        body: JSON.stringify({ document_id: 7 }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
    });

    expect(await screen.findByText("Alice Reader MVP")).toBeInTheDocument();
  });
});
