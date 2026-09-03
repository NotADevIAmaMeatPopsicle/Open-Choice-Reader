import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { withAuthenticatedAppFetch } from "./support/authSessionFetch";

describe("DiscoverPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/issues" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            total_count: 0,
            counts_by_severity: {},
            items: [],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/documents/summary" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            continue_reading: [],
            recent_documents: [],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [],
        });
      }

      if (typeof input === "string" && input === "/api/catalogs/gutenberg/top?limit=12" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: "84",
              source: "gutenberg",
              source_name: "Project Gutenberg",
              title: "Frankenstein",
              author: "Mary Shelley",
              summary: "A scientist creates a monster.",
              cover_url: "https://example.test/frankenstein.jpg",
              detail_url: "https://www.gutenberg.org/ebooks/84",
              download_format: "epub",
              language: "en",
              importable: true,
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

  it("renders Discover in the shell and loads the default catalog shelf", async () => {
    window.history.pushState({}, "", "/discover");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Discover" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Discover" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Catalogs" })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByText("Frankenstein")).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/catalogs/gutenberg/top?limit=12");
    });
  });

  it("supports catalog import, direct URL import, pasted text import, and html-capable upload mode", async () => {
    window.history.pushState({}, "", "/discover");

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/issues" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            total_count: 0,
            counts_by_severity: {},
            items: [],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/documents/summary" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            continue_reading: [],
            recent_documents: [],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [],
        });
      }

      if (typeof input === "string" && input === "/api/catalogs/gutenberg/top?limit=12" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: "84",
              source: "gutenberg",
              source_name: "Project Gutenberg",
              title: "Frankenstein",
              author: "Mary Shelley",
              summary: "A scientist creates a monster.",
              cover_url: "https://example.test/frankenstein.jpg",
              detail_url: "https://www.gutenberg.org/ebooks/84",
              download_format: "epub",
              language: "en",
              importable: true,
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/catalogs/import" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: 37,
            title: "Frankenstein",
            format: "epub",
            status: "uploaded",
            author: "Mary Shelley",
            cover_url: "/api/documents/37/cover",
            summary: "A scientist creates a monster.",
            total_sections: 12,
            total_chunks: 120,
            estimated_duration_seconds: 720,
            current_chunk_index: null,
            progress_percent: 0,
            last_opened_at: null,
            source_provider: "gutenberg",
            source_provider_name: "Project Gutenberg",
            source_provider_url: "https://www.gutenberg.org/ebooks/84",
            source_url: null,
            source_site_name: null,
            import_mode: null,
          }),
        });
      }

      if (typeof input === "string" && input === "/api/documents/37" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 37,
            title: "Frankenstein",
            format: "epub",
            status: "uploaded",
            author: "Mary Shelley",
            cover_url: "/api/documents/37/cover",
            summary: "A scientist creates a monster.",
            total_sections: 12,
            total_chunks: 120,
            estimated_duration_seconds: 720,
            current_chunk_index: null,
            progress_percent: 0,
            last_opened_at: null,
            source_provider: "gutenberg",
            source_provider_name: "Project Gutenberg",
            source_provider_url: "https://www.gutenberg.org/ebooks/84",
            source_url: null,
            source_site_name: null,
            import_mode: null,
            sections: [],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/catalogs/import-url" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: 38,
            title: "Imported article",
            format: "html",
            status: "uploaded",
            author: "Web Writer",
            cover_url: "/api/documents/38/cover",
            summary: "Readable article body.",
            total_sections: 1,
            total_chunks: 3,
            estimated_duration_seconds: 18,
            current_chunk_index: null,
            progress_percent: 0,
            last_opened_at: null,
            source_provider: "web",
            source_provider_name: "Article import",
            source_provider_url: "https://example.test/article",
            source_url: "https://example.test/article",
            source_site_name: "example.test",
            import_mode: "article_url",
          }),
        });
      }

      if (typeof input === "string" && input === "/api/documents/38" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 38,
            title: "Imported article",
            format: "html",
            status: "uploaded",
            author: "Web Writer",
            cover_url: "/api/documents/38/cover",
            summary: "Readable article body.",
            total_sections: 1,
            total_chunks: 3,
            estimated_duration_seconds: 18,
            current_chunk_index: null,
            progress_percent: 0,
            last_opened_at: null,
            source_provider: "web",
            source_provider_name: "Article import",
            source_provider_url: "https://example.test/article",
            source_url: "https://example.test/article",
            source_site_name: "example.test",
            import_mode: "article_url",
            sections: [],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/catalogs/import-text" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: 39,
            title: "Saved clipping",
            format: "md",
            status: "uploaded",
            author: "Casey Example",
            cover_url: "/api/documents/39/cover",
            summary: "Pasted body text.",
            total_sections: 1,
            total_chunks: 2,
            estimated_duration_seconds: 12,
            current_chunk_index: null,
            progress_percent: 0,
            last_opened_at: null,
            source_provider: "manual",
            source_provider_name: "Pasted text",
            source_provider_url: "https://notes.example.test/item",
            source_url: "https://notes.example.test/item",
            source_site_name: "notes.example.test",
            import_mode: "pasted_text",
          }),
        });
      }

      if (typeof input === "string" && input === "/api/documents/39" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 39,
            title: "Saved clipping",
            format: "md",
            status: "uploaded",
            author: "Casey Example",
            cover_url: "/api/documents/39/cover",
            summary: "Pasted body text.",
            total_sections: 1,
            total_chunks: 2,
            estimated_duration_seconds: 12,
            current_chunk_index: null,
            progress_percent: 0,
            last_opened_at: null,
            source_provider: "manual",
            source_provider_name: "Pasted text",
            source_provider_url: "https://notes.example.test/item",
            source_url: "https://notes.example.test/item",
            source_site_name: "notes.example.test",
            import_mode: "pasted_text",
            sections: [],
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

    expect(await screen.findByRole("heading", { name: "Discover" })).toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: "Import Frankenstein" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/catalogs/import", {
        body: JSON.stringify({ source: "gutenberg", catalog_id: "84" }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
    });
    expect(await screen.findByRole("heading", { name: "Frankenstein" })).toBeInTheDocument();

    window.history.pushState({}, "", "/discover");
    fireEvent.popState(window);

    expect(await screen.findByRole("button", { name: "From URL" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "From URL" }));
    fireEvent.change(screen.getByLabelText("Document or article URL"), {
      target: { value: "https://example.test/article" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Import from URL" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/catalogs/import-url", {
        body: JSON.stringify({ url: "https://example.test/article" }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
    });
    expect(await screen.findByRole("heading", { name: "Imported article" })).toBeInTheDocument();

    window.history.pushState({}, "", "/discover");
    fireEvent.popState(window);

    fireEvent.click(screen.getByRole("button", { name: "Paste text" }));
    fireEvent.change(screen.getByLabelText("Title"), {
      target: { value: "Saved clipping" },
    });
    fireEvent.change(screen.getByLabelText("Author"), {
      target: { value: "Casey Example" },
    });
    fireEvent.change(screen.getByLabelText("Source URL"), {
      target: { value: "https://notes.example.test/item" },
    });
    fireEvent.change(screen.getByLabelText("Body text"), {
      target: { value: "Pasted body text." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Import pasted text" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/catalogs/import-text", {
        body: JSON.stringify({
          title: "Saved clipping",
          author: "Casey Example",
          source_url: "https://notes.example.test/item",
          body: "Pasted body text.",
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
    });
    expect(await screen.findByRole("heading", { name: "Saved clipping" })).toBeInTheDocument();

    window.history.pushState({}, "", "/discover");
    fireEvent.popState(window);

    fireEvent.click(screen.getByRole("button", { name: "Upload file" }));
    expect(await screen.findByLabelText("Upload document file")).toHaveAttribute(
      "accept",
      ".epub,.pdf,.txt,.md,.markdown,.html",
    );
  });
});
