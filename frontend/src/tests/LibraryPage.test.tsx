import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { withAuthenticatedAppFetch } from "./support/authSessionFetch";

function buildQueuedJob(overrides: Record<string, unknown> = {}) {
  return {
    id: 31,
    document_id: 7,
    voice_preset_id: "11",
    format: "wav",
    status: "queued",
    split_chapters: false,
    artifact_basename: "Alice Reader MVP",
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

describe("LibraryPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
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

    Object.defineProperty(window.HTMLMediaElement.prototype, "load", {
      configurable: true,
      value: vi.fn(),
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
    vi.unstubAllGlobals();
  });

  it("renders the library heading and routes new acquisitions into Discover", async () => {
    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Library",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Discover imports",
      }),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/documents");
    });
  });

  it("advertises supported upload formats in the Discover import flow", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Discover imports" }));
    expect(await screen.findByRole("heading", { name: "Discover" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Upload file" }));
    expect(await screen.findByLabelText("Upload document file")).toHaveAttribute(
      "accept",
      ".epub,.pdf,.txt,.md,.markdown,.html",
    );
  });

  it("loads imported document count from the api", async () => {
    fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: 1,
          title: "Sample Book",
          format: "epub",
          status: "ready",
        },
        {
          id: 2,
          title: "Notes",
          format: "txt",
          status: "imported",
        },
      ],
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("2 items imported")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/documents");
  });

  it("starts reading from the selected library spotlight", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => documents,
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 21,
            document_id: 7,
            current_chunk_index: 0,
            audio_url: "/api/playback/audio/21",
          }),
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions/21" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 21,
            document_id: 7,
            current_chunk_index: 0,
            audio_url: "/api/playback/audio/21",
          }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    const documents = [
      {
        id: 7,
        title: "Alice Reader MVP",
        format: "epub",
        status: "ready",
        cover_url: "/api/documents/7/cover",
        summary: "Imported and ready to read.",
        author: "Open Choice Reader",
        total_sections: 2,
        total_chunks: 2,
        estimated_duration_seconds: 12,
        current_chunk_index: null,
        progress_percent: 0,
        last_opened_at: null,
      },
    ];

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("1 items imported")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Alice Reader MVP" })).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Read now",
      }),
    );

    expect(await screen.findByRole("dialog", { name: "Confirm play" })).toBeInTheDocument();
    expect(screen.getByText("Start reading Alice Reader MVP?")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Confirm play",
      }),
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/playback/sessions", {
        body: JSON.stringify({ document_id: 7 }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });
    });

    expect(
      await screen.findByRole("heading", {
        name: "Reading progress",
      }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe("/reader/21");
    expect(await screen.findByText("Current chunk index: 0")).toBeInTheDocument();
  });

  it("lets Alice cancel the confirm-play modal without starting playback", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 21,
            document_id: 7,
            current_chunk_index: 0,
            audio_url: "/api/playback/audio/21",
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

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Read now",
      }),
    );

    expect(await screen.findByRole("dialog", { name: "Confirm play" })).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Cancel",
      }),
    );

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Confirm play" })).not.toBeInTheDocument();
    });
    expect(fetchMock).not.toHaveBeenCalledWith(
      "/api/playback/sessions",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(window.location.pathname).toBe("/");
  });

  it("opens a dedicated book detail surface from the library list", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
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

    render(<App />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: "View details",
      }),
    );

    expect(window.location.pathname).toBe("/books/7");
    expect(
      await screen.findByRole("heading", {
        name: "Alice Reader MVP",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("EPUB document")).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Export audiobook",
      }),
    ).toBeInTheDocument();
  });

  it("shows the backend error when starting reading fails", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions" && init?.method === "POST") {
        return Promise.resolve({
          ok: false,
          status: 503,
          json: async () => ({
            detail: "Playback service unavailable",
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

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Read now",
      }),
    );

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Confirm play",
      }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Playback service unavailable");
    expect(window.location.pathname).toBe("/");
  });

  it("surfaces backend upload errors from the Discover import flow", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [],
        });
      }

      if (typeof input === "string" && input === "/api/documents/import" && init?.method === "POST") {
        return Promise.resolve({
          ok: false,
          status: 422,
          json: async () => ({
            detail: "Unsupported import format 'html'",
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

    fireEvent.click(await screen.findByRole("button", { name: "Discover imports" }));
    expect(await screen.findByRole("heading", { name: "Discover" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Upload file" }));

    const fileInput = await screen.findByLabelText("Upload document file");
    const file = new File(["<p>html</p>"], "unsupported.html", {
      type: "text/html",
    });

    fireEvent.change(fileInput, {
      target: {
        files: [file],
      },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent("Unsupported import format 'html'");
  });

  it("queues an audiobook export with the existing preset and routes to jobs", async () => {
    const jobs = [buildQueuedJob()];

    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/voices/presets" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 11,
              name: "Warm Narrator",
              engine: "qwen3",
              transcript: null,
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/jobs/export" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => jobs[0],
        });
      }

      if (typeof input === "string" && input === "/api/jobs" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => jobs,
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Alice Reader MVP" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Export audiobook",
      }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Export audiobook",
      }),
    );

    const presetSelect = await screen.findByLabelText("Voice preset");
    expect(presetSelect).toHaveValue("11");
    expect(screen.getByLabelText("File label")).toHaveValue("Alice Reader MVP");

    fireEvent.change(screen.getByLabelText("File label"), {
      target: {
        value: "Alice Split Run",
      },
    });
    fireEvent.click(screen.getByLabelText("Split by chapter"));

    fireEvent.click(
      screen.getByRole("button", {
        name: "Queue audiobook export",
      }),
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/jobs/export", {
        body: JSON.stringify({
          document_id: 7,
          voice_preset_id: "11",
          clone_engine_id: "qwen3_clone_0_6b",
          format: "wav",
          split_chapters: true,
          artifact_basename: "Alice Split Run",
        }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });
    });

    expect(await screen.findByRole("heading", { name: "Export Queue" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/jobs");
    expect(await screen.findByText("Document 7")).toBeInTheDocument();
    expect(screen.getByText("Preset 11")).toBeInTheDocument();
  }, 10000);

  it("imports a new file from the watched inbox panel", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [],
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

      if (typeof input === "string" && input === "/api/documents/import-inbox" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: 12,
            title: "Inbox Title",
            format: "md",
            status: "uploaded",
            cover_url: "/api/documents/12/cover",
            summary: "First paragraph.",
            author: null,
            total_sections: 1,
            total_chunks: 1,
            estimated_duration_seconds: 6,
            current_chunk_index: null,
            progress_percent: 0,
            last_opened_at: null,
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

    fireEvent.click(await screen.findByRole("button", { name: "Review inbox" }));

    expect(await screen.findByText("incoming.md")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Import from inbox" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/documents/import-inbox", {
        body: JSON.stringify({ path: "incoming.md" }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
    });
  });

  it("refreshes an already imported inbox file through the inbox panel", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/documents/inbox" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              name: "updated.epub",
              path: "updated.epub",
              format: "epub",
              document_id: 7,
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/documents/7/reimport" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 7,
            title: "Alice Reader MVP",
            format: "epub",
            status: "uploaded",
            cover_url: "/api/documents/7/cover",
            summary: "Updated summary.",
            author: null,
            total_sections: 2,
            total_chunks: 2,
            estimated_duration_seconds: 12,
            current_chunk_index: null,
            progress_percent: 0,
            last_opened_at: null,
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

    fireEvent.click(await screen.findByRole("button", { name: "Review inbox" }));

    expect(await screen.findByText("updated.epub")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Refresh imported book" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/documents/7/reimport", {
        method: "POST",
      });
    });
  });

  it("tells Alice when no presets exist and points to the voices page", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/voices/presets" && !init) {
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

    render(<App />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Export audiobook",
      }),
    );

    expect(
      await screen.findByText("No saved cloned voices yet. Open Voices to create the first export narrator."),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Create first cloned voice",
      }),
    );

    expect(await screen.findByRole("heading", { name: "Voices" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/voices");
  });

  it("requires a preset selection before queueing and surfaces backend detail on failure", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/voices/presets" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 11,
              name: "Warm Narrator",
              engine: "qwen3",
              transcript: null,
            },
            {
              id: 12,
              name: "Bright Narrator",
              engine: "qwen3",
              transcript: null,
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/jobs/export" && init?.method === "POST") {
        return Promise.resolve({
          ok: false,
          status: 422,
          json: async () => ({
            detail: "Preset 12 cannot export audiobook jobs",
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

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Export audiobook",
      }),
    );

    const queueButton = await screen.findByRole("button", {
      name: "Queue audiobook export",
    });
    const presetSelect = screen.getByLabelText("Voice preset");

    expect(queueButton).toBeDisabled();
    expect(presetSelect).toHaveValue("");

    fireEvent.change(presetSelect, {
      target: {
        value: "12",
      },
    });

    expect(queueButton).toBeEnabled();

    fireEvent.click(queueButton);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Preset 12 cannot export audiobook jobs",
    );
    expect(window.location.pathname).toBe("/");
  }, 10000);

  it("surfaces preset load failures without pretending Alice has no saved presets", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/voices/presets" && !init) {
        return Promise.resolve({
          ok: false,
          status: 503,
          json: async () => ({
            detail: "Voice preset library unavailable",
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

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Export audiobook",
      }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("Voice preset library unavailable");
    expect(screen.queryByText("No saved voice presets yet.")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Go to Voices",
      }),
    ).not.toBeInTheDocument();
  });

  it("ignores stale preset responses when Alice switches export composers between documents", async () => {
    const firstPresetRequest = createDeferredValue<{
      json: () => Promise<
        Array<{
          engine: string;
          id: number;
          name: string;
          transcript: null;
        }>
      >;
      ok: boolean;
      status: number;
    }>();
    const secondPresetRequest = createDeferredValue<{
      json: () => Promise<
        Array<{
          engine: string;
          id: number;
          name: string;
          transcript: null;
        }>
      >;
      ok: boolean;
      status: number;
    }>();
    let voicePresetRequestCount = 0;

    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
            {
              id: 8,
              title: "Alice Reader Followup",
              format: "txt",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/voices/presets" && !init) {
        voicePresetRequestCount += 1;
        return voicePresetRequestCount === 1 ? firstPresetRequest.promise : secondPresetRequest.promise;
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Export audiobook",
      }),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Open spotlight for Alice Reader Followup",
      }),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Export audiobook",
      }),
    );

    secondPresetRequest.resolve({
      ok: true,
      status: 200,
      json: async () => [
        {
          id: 22,
          name: "Second Document Voice",
          engine: "qwen3",
          transcript: null,
        },
      ],
    });

    const presetSelect = await screen.findByLabelText("Voice preset");
    await waitFor(() => {
      expect(presetSelect).toHaveValue("22");
    });
    expect(screen.getByRole("option", { name: "Second Document Voice" })).toBeInTheDocument();

    firstPresetRequest.resolve({
      ok: true,
      status: 200,
      json: async () => [
        {
          id: 11,
          name: "First Document Voice",
          engine: "qwen3",
          transcript: null,
        },
      ],
    });

    await waitFor(() => {
      expect(presetSelect).toHaveValue("22");
    });
    expect(screen.queryByRole("option", { name: "First Document Voice" })).not.toBeInTheDocument();
  }, 10000);

  it("does not yank Alice to jobs when an older export request resolves after he switches documents", async () => {
    const queuedExportRequest = createDeferredValue<{
      json: () => Promise<{
        document_id: number;
        download_url: null;
        failure_detail: null;
        format: string;
        id: number;
        status: string;
        voice_preset_id: string;
      }>;
      ok: boolean;
      status: number;
    }>();

    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
            {
              id: 8,
              title: "Alice Reader Followup",
              format: "txt",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/voices/presets" && !init) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            {
              id: 11,
              name: "Warm Narrator",
              engine: "qwen3",
              transcript: null,
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/jobs/export" && init?.method === "POST") {
        return queuedExportRequest.promise;
      }

      if (typeof input === "string" && input === "/api/jobs" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 31,
              document_id: 7,
              voice_preset_id: "11",
              format: "wav",
              status: "queued",
              download_url: null,
              failure_detail: null,
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

    render(<App />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Export audiobook",
      }),
    );
    await waitFor(() => {
      expect(screen.getByLabelText("Voice preset")).toHaveValue("11");
    });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Queue audiobook export",
      }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Open spotlight for Alice Reader Followup",
      }),
    );
    fireEvent.click(
      screen.getByRole("button", {
        name: "Export audiobook",
      }),
    );
    await waitFor(() => {
      expect(screen.getByLabelText("Voice preset")).toHaveValue("11");
    });

    queuedExportRequest.resolve({
      ok: true,
      status: 201,
      json: async () => ({
        id: 31,
        document_id: 7,
        voice_preset_id: "11",
        format: "wav",
        status: "queued",
        download_url: null,
        failure_detail: null,
      }),
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/jobs");
    });

    expect(window.location.pathname).toBe("/");
    expect(screen.queryByRole("heading", { name: "Export Queue" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Alice Reader Followup" })).toBeInTheDocument();
  }, 15000);

  it("does not log stale-update warnings when export presets resolve after the library unmounts", async () => {
    const presetRequest = createDeferredValue<{
      json: () => Promise<
        Array<{
          engine: string;
          id: number;
          name: string;
          transcript: null;
        }>
      >;
      ok: boolean;
      status: number;
    }>();
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/voices/presets" && !init) {
        return presetRequest.promise;
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    const rendered = render(<App />);

    fireEvent.click(
      await screen.findByRole("button", {
        name: "Export audiobook",
      }),
    );

    rendered.unmount();

    await act(async () => {
      presetRequest.resolve({
        ok: true,
        status: 200,
        json: async () => [
          {
            id: 11,
            name: "Warm Narrator",
            engine: "qwen3",
            transcript: null,
          },
        ],
      });
      await Promise.resolve();
    });

    expect(consoleErrorSpy).not.toHaveBeenCalled();
    consoleErrorSpy.mockRestore();
  });

  it("keeps a selected spotlight panel in sync with the chosen shelf cover", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 1,
              title: "Brave New World",
              format: "epub",
              status: "ready",
              author: "Aldous Huxley",
              cover_url: "/api/documents/1/cover",
              summary: "A synthetic society.",
              total_sections: 10,
              progress_percent: 25,
            },
            {
              id: 2,
              title: "Animal Farm",
              format: "epub",
              status: "ready",
              author: "George Orwell",
              cover_url: "/api/documents/2/cover",
              summary: "A farm becomes a fable.",
              total_sections: 8,
              progress_percent: 0,
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

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Brave New World" })).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Open spotlight for Animal Farm",
      }),
    );

    expect(await screen.findByRole("heading", { name: "Animal Farm" })).toBeInTheDocument();
    expect(screen.getByText("A farm becomes a fable.")).toBeInTheDocument();
  });

  it("offers screenshot-inspired shelf controls including series collapsing", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 11,
              title: "Wool #1 - Holston",
              format: "epub",
              status: "ready",
              cover_url: "/api/documents/11/cover",
            },
            {
              id: 12,
              title: "Wool #2 - Proper Gauge",
              format: "epub",
              status: "ready",
              cover_url: "/api/documents/12/cover",
            },
            {
              id: 13,
              title: "The Prince",
              format: "pdf",
              status: "ready",
              cover_url: "/api/documents/13/cover",
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

    render(<App />);

    expect(await screen.findByLabelText("Collapse series")).not.toBeChecked();
    expect(screen.getByRole("combobox", { name: "Shelf view" })).toHaveValue("recommended");
    expect(screen.getByRole("button", { name: "Open spotlight for Wool #1 - Holston" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open spotlight for Wool #2 - Proper Gauge" })).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Collapse series"));

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Open spotlight for Wool #2 - Proper Gauge" })).not.toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Open spotlight for Wool #1 - Holston" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open spotlight for The Prince" })).toBeInTheDocument();
  });

  it("switches to spine mode and persists the library shelf preference", async () => {
    let settingsState = {
      default_live_voice_id: "builtin:piper:default",
      default_export_voice_id: "builtin:piper:default",
      fallback_voice_id: "builtin:piper:default",
      selected_clone_model_engine: "qwen3_clone_0_6b",
      active_theme_id: "mahogany-stacks",
      active_theme: {
        id: "mahogany-stacks",
        name: "Mahogany Stacks",
        description: "Deep wood stacks with low amber light.",
        source_kind: "house",
        source_label: "Open Choice Reader",
        source_reference: null,
        is_builtin: true,
        sort_order: 52,
        family: "showcase",
        preview_variant: "dark-cozy",
        background_asset_path: "/theme-assets/backgrounds/mahogany-stacks.svg",
        background_overlay_path: "/theme-assets/textures/warm-vignette.svg",
        shelf_asset_path: "/theme-assets/shelves/mahogany-shelf.svg",
        surface_texture_asset_path: "/theme-assets/textures/woodgrain-dark.svg",
        supports_mix_and_match: true,
        tokens: {
          "--color-bg": "#1b1410",
          "--color-accent": "#d7a24c",
        },
      },
      engine_statuses: [],
      host_runtime: {
        host_name: "Server",
        runtime_label: "Server GPU host",
        gpu_name: "NVIDIA GeForce RTX 3080",
        execution_summary: "This host is serving Open Choice Reader and performing audio generation here.",
      },
      clone_runtime: {
        engine: "qwen3_clone",
        model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        preset_count: 0,
        availability: "available",
        availability_detail: "Ready",
        usage_summary: "Saved cloned presets are used for audiobook export, not instant live reading.",
        execution_summary: "Cloned audiobook exports run on the connected Server host when the clone runtime is available.",
        available_models: [],
      },
      ui_theme: "mahogany-stacks",
      sidebar_width_px: 112,
      sidebar_mode: "compact",
      dock_position: "bottom",
      tooltips_enabled: true,
      default_playback_speed: 1.5,
      auto_pause_on_interrupt: true,
      library_view_mode: "cover",
      background_override_theme_id: null,
      shelf_override_theme_id: null,
    };

    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 1,
              title: "Brave New World",
              format: "epub",
              status: "ready",
              author: "Aldous Huxley",
              cover_url: "/api/documents/1/cover",
              progress_percent: 25,
            },
            {
              id: 2,
              title: "Animal Farm",
              format: "epub",
              status: "ready",
              author: "George Orwell",
              cover_url: "/api/documents/2/cover",
              progress_percent: 0,
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/settings" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => settingsState,
        });
      }

      if (typeof input === "string" && input === "/api/settings" && init?.method === "PUT") {
        settingsState = {
          ...settingsState,
          ...(JSON.parse(String(init.body ?? "{}")) as Record<string, unknown>),
        };
        return Promise.resolve({
          ok: true,
          json: async () => settingsState,
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("button", { name: "Open spotlight for Brave New World" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Spines-out shelf" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/settings",
        expect.objectContaining({
          method: "PUT",
        }),
      );
    });
    expect(await screen.findByText("Brave New World - Aldous Huxley")).toBeInTheDocument();
  });
});
