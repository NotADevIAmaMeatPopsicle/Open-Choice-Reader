import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { resetJobsCacheForTests } from "../hooks/useJobs";

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

describe("BookPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    resetJobsCacheForTests();
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
  });

  afterEach(() => {
    resetJobsCacheForTests();
    window.history.pushState({}, "", "/");
    vi.unstubAllGlobals();
  });

  it("queues an audiobook export from the dedicated book detail route", async () => {
    window.history.pushState({}, "", "/books/7");

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
          json: async () => buildQueuedJob(),
        });
      }

      if (typeof input === "string" && input === "/api/settings" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            default_live_voice_id: "builtin:piper:default",
            default_export_voice_id: "preset:11",
            fallback_voice_id: "builtin:piper:default",
            selected_clone_model_engine: "qwen3_clone_1_7b",
            engine_statuses: [],
            clone_runtime: {
              engine: "qwen3_clone",
              model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
              preset_count: 1,
              availability: "available",
              availability_detail: "Qwen3 clone exports are ready when a saved preset is selected.",
              usage_summary:
                "Saved cloned presets can be used for live reading and audiobook export on Server when the clone runtime is available.",
              execution_summary:
                "Live cloned reading and audiobook exports run on the connected Server host when the clone runtime is available.",
              available_models: [
                {
                  engine: "qwen3_clone_0_6b",
                  display_name: "Premium clone 0.6B",
                  model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                  availability: "available",
                  availability_detail: "Faster premium clone exports are ready.",
                },
                {
                  engine: "qwen3_clone_1_7b",
                  display_name: "Premium clone 1.7B",
                  model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                  availability: "available",
                  availability_detail: "Highest-quality premium clone exports are ready.",
                },
              ],
            },
          }),
        });
      }

      if (typeof input === "string" && input === "/api/jobs" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [buildQueuedJob()],
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Alice Reader MVP",
      }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Export audiobook",
      }),
    );

    expect(await screen.findByText("Export narrator")).toBeInTheDocument();
    expect(screen.getByText("Premium model: Premium clone 1.7B")).toBeInTheDocument();
    expect(await screen.findByLabelText("Voice preset")).toHaveValue("11");
    expect(screen.getByLabelText("File label")).toHaveValue("Alice Reader MVP");

    fireEvent.change(screen.getByLabelText("File label"), {
      target: {
        value: "Alice Nightly",
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
          clone_engine_id: "qwen3_clone_1_7b",
          format: "wav",
          split_chapters: true,
          artifact_basename: "Alice Nightly",
        }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });
    });

    expect(await screen.findByRole("heading", { name: "Export Queue" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/jobs");
    expect(screen.getByRole("list", { name: "Queue summary" })).toHaveTextContent("1queued up");
  });

  it("lets a saved cloned preset drive live reading when the Server clone runtime is available", async () => {
    window.history.pushState({}, "", "/books/7");

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

      if (typeof input === "string" && input === "/api/documents/7" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 7,
            title: "Alice Reader MVP",
            format: "epub",
            status: "ready",
            author: "Alice",
            cover_url: "/api/documents/7/cover",
            summary: "A guided MVP walkthrough.",
            total_sections: 1,
            total_chunks: 1,
            estimated_duration_seconds: 12,
            current_chunk_index: null,
            progress_percent: 0,
            last_opened_at: null,
            sections: [
              {
                id: 21,
                position: 0,
                title: "Chapter One",
                chunk_start_index: 0,
                chunk_count: 1,
                preview_text: "First section opening.",
              },
            ],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/voices/options" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: "builtin:piper:default",
              name: "Default",
              voice_type: "built_in",
              engine: "piper",
              engine_family: "piper",
              mode_label: "Fast reader",
              description: "Local Piper voice for quick read-aloud and fallback export.",
              availability: "available",
              availability_detail: "Piper is ready with 1 local voice.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
              model_name: null,
            },
            {
              id: "preset:11",
              name: "Warm Narrator",
              voice_type: "cloned",
              engine: "qwen3_clone",
              engine_family: "qwen3_clone",
              mode_label: "Cloned voice",
              description: "Saved reference voice preset for premium live reading and audiobook export.",
              availability: "available",
              availability_detail:
                "Qwen3 clone live reading and exports are ready when a saved preset is selected.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: "Warm sample transcript.",
              model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/settings" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            default_live_voice_id: "preset:11",
            default_export_voice_id: "preset:11",
            fallback_voice_id: "builtin:piper:default",
            selected_clone_model_engine: "qwen3_clone_1_7b",
            engine_statuses: [],
            clone_runtime: {
              engine: "qwen3_clone",
              model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
              preset_count: 1,
              availability: "available",
              availability_detail:
                "Qwen3 clone live reading and exports are ready when a saved preset is selected.",
              usage_summary:
                "Saved cloned presets can be used for live reading and audiobook export on Server when the clone runtime is available.",
              execution_summary:
                "Live cloned reading and audiobook exports run on the connected Server host when the clone runtime is available.",
              available_models: [
                {
                  engine: "qwen3_clone_1_7b",
                  display_name: "Premium clone 1.7B",
                  model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
                  availability: "available",
                  availability_detail:
                    "Qwen3 clone live reading and exports are ready when a saved preset is selected.",
                },
              ],
            },
          }),
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: 44,
            document_id: 7,
            current_chunk_index: 0,
            total_chunks: 1,
            audio_url: "/api/playback/audio/44",
            engine_name: "qwen3_clone_1_7b",
            voice_option_id: "preset:11",
            voice_model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            playback_speed: 1,
            current_chunk_text: "First section opening.",
            current_section_title: "Chapter One",
            section_chunks: [
              {
                chunk_index: 0,
                text: "First section opening.",
                is_current: true,
              },
            ],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions/44" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 44,
            document_id: 7,
            current_chunk_index: 0,
            total_chunks: 1,
            audio_url: "/api/playback/audio/44",
            engine_name: "qwen3_clone_1_7b",
            voice_option_id: "preset:11",
            voice_model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            playback_speed: 1,
            current_chunk_text: "First section opening.",
            current_section_title: "Chapter One",
            section_chunks: [
              {
                chunk_index: 0,
                text: "First section opening.",
                is_current: true,
              },
            ],
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

    expect(await screen.findByLabelText("Live reading voice")).toHaveValue("preset:11");
    const clonedVoiceContext = screen.getByLabelText("Book voice context");
    expect(within(clonedVoiceContext).getAllByText("Warm Narrator")[0]).toBeInTheDocument();
    expect(within(clonedVoiceContext).getByText(/Qwen\/Qwen3-TTS-12Hz-1.7B-Base/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Read now" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/playback/sessions", {
        body: JSON.stringify({
          document_id: 7,
          start_section_id: undefined,
          voice_option_id: "preset:11",
        }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });
    });
  });

  it("renders chapters and starts reading from a chosen section with the selected live voice", async () => {
    window.history.pushState({}, "", "/books/7");

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

      if (typeof input === "string" && input === "/api/documents/7" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 7,
            title: "Alice Reader MVP",
            format: "epub",
            status: "ready",
            author: "Alice",
            cover_url: "/api/documents/7/cover",
            summary: "A guided MVP walkthrough.",
            total_sections: 2,
            total_chunks: 2,
            estimated_duration_seconds: 12,
            current_chunk_index: null,
            progress_percent: 0,
            last_opened_at: null,
            sections: [
              {
                id: 21,
                position: 0,
                title: "Chapter One",
                chunk_start_index: 0,
                chunk_count: 1,
                preview_text: "First section opening.",
              },
              {
                id: 22,
                position: 1,
                title: "Chapter Two",
                chunk_start_index: 1,
                chunk_count: 1,
                preview_text: "Second section opening.",
              },
            ],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/voices/options" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: "builtin:piper:default",
              name: "Default",
              voice_type: "built_in",
              engine: "piper",
              mode_label: "Fast reader",
              description: "Local Piper voice for quick read-aloud and fallback export.",
              availability: "available",
              availability_detail: "Piper is ready with 1 local voice.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/settings" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            default_live_voice_id: "builtin:piper:default",
            default_export_voice_id: "builtin:piper:default",
            fallback_voice_id: "builtin:piper:default",
            selected_clone_model_engine: "qwen3_clone_0_6b",
            engine_statuses: [],
            clone_runtime: {
              engine: "qwen3_clone",
              model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
              preset_count: 0,
              availability: "available",
              availability_detail: "Qwen3 clone exports are ready when a saved preset is selected.",
              usage_summary: "Saved cloned presets are used for audiobook export, not instant live reading.",
              execution_summary: "Cloned audiobook exports run on the connected Server host when the clone runtime is available.",
              available_models: [
                {
                  engine: "qwen3_clone_0_6b",
                  display_name: "Premium clone 0.6B",
                  model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                  availability: "available",
                  availability_detail: "Faster premium clone exports are ready.",
                },
              ],
            },
          }),
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: 44,
            document_id: 7,
            current_chunk_index: 1,
            audio_url: "/api/playback/audio/44",
            voice_option_id: "builtin:piper:default",
          }),
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions/44" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 44,
            document_id: 7,
            current_chunk_index: 1,
            audio_url: "/api/playback/audio/44",
            voice_option_id: "builtin:piper:default",
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

    expect(await screen.findByRole("heading", { name: "Alice Reader MVP" })).toBeInTheDocument();
    expect(await screen.findByText("Chapter One")).toBeInTheDocument();
    expect(screen.getByText("Chapter Two")).toBeInTheDocument();
    expect(screen.getAllByText("Current narrator").length).toBeGreaterThan(0);
    const voiceContext = screen.getByLabelText("Book voice context");
    expect(
      within(voiceContext).getByText((_, node) => node?.textContent === "Engine: Piper • Live + Export"),
    ).toBeInTheDocument();
    expect(within(voiceContext).getByText("Piper is ready with 1 local voice.")).toBeInTheDocument();
    expect(screen.getByText(/Global defaults and the premium clone model live in Voices\./)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Manage voices" })).toBeInTheDocument();
    expect(screen.getByLabelText("Live reading voice")).toHaveValue("builtin:piper:default");

    fireEvent.click(screen.getByRole("button", { name: "Read from Chapter Two" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/playback/sessions", {
        body: JSON.stringify({
          document_id: 7,
          start_section_id: 22,
          voice_option_id: "builtin:piper:default",
        }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });
    });
  });

  it("keeps export available for a freshly uploaded document", async () => {
    window.history.pushState({}, "", "/books/7");

    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 7,
              title: "Alice Reader MVP",
              format: "epub",
              status: "uploaded",
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
          json: async () => buildQueuedJob(),
        });
      }

      if (typeof input === "string" && input === "/api/settings" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            default_live_voice_id: "builtin:piper:default",
            default_export_voice_id: "preset:11",
            fallback_voice_id: "builtin:piper:default",
            selected_clone_model_engine: "qwen3_clone_0_6b",
            engine_statuses: [],
            clone_runtime: {
              engine: "qwen3_clone",
              model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
              preset_count: 1,
              availability: "available",
              availability_detail: "Qwen3 clone exports are ready when a saved preset is selected.",
              usage_summary: "Saved cloned presets are used for audiobook export, not instant live reading.",
              execution_summary: "Cloned audiobook exports run on the connected Server host when the clone runtime is available.",
              available_models: [
                {
                  engine: "qwen3_clone_0_6b",
                  display_name: "Premium clone 0.6B",
                  model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                  availability: "available",
                  availability_detail: "Faster premium clone exports are ready.",
                },
              ],
            },
          }),
        });
      }

      if (typeof input === "string" && input === "/api/jobs" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [buildQueuedJob()],
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const exportButton = await screen.findByRole("button", {
      name: "Export audiobook",
    });
    expect(exportButton).toBeEnabled();
    expect(screen.getByRole("button", { name: "Read now" })).toBeEnabled();
    expect(screen.getByText("Ready to read or export")).toBeInTheDocument();
    expect(screen.queryByText("Imported and waiting for final processing")).not.toBeInTheDocument();

    fireEvent.click(exportButton);

    expect(await screen.findByLabelText("Voice preset")).toHaveValue("11");
    expect(screen.getByLabelText("File label")).toHaveValue("Alice Reader MVP");

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
          split_chapters: false,
          artifact_basename: "Alice Reader MVP",
        }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });
    });
  });

  it("does not allow a second export submission while the first queue request is still in flight", async () => {
    window.history.pushState({}, "", "/books/7");

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
        return queuedExportRequest.promise;
      }

      if (typeof input === "string" && input === "/api/settings" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            default_live_voice_id: "builtin:piper:default",
            default_export_voice_id: "preset:11",
            fallback_voice_id: "builtin:piper:default",
            selected_clone_model_engine: "qwen3_clone_0_6b",
            engine_statuses: [],
            clone_runtime: {
              engine: "qwen3_clone",
              model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
              preset_count: 1,
              availability: "available",
              availability_detail: "Qwen3 clone exports are ready when a saved preset is selected.",
              usage_summary: "Saved cloned presets are used for audiobook export, not instant live reading.",
              execution_summary: "Cloned audiobook exports run on the connected Server host when the clone runtime is available.",
              available_models: [
                {
                  engine: "qwen3_clone_0_6b",
                  display_name: "Premium clone 0.6B",
                  model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
                  availability: "available",
                  availability_detail: "Faster premium clone exports are ready.",
                },
              ],
            },
          }),
        });
      }

      if (typeof input === "string" && input === "/api/jobs" && !init) {
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

    fireEvent.click(await screen.findByRole("button", { name: "Export audiobook" }));

    const queueButton = await screen.findByRole("button", {
      name: "Queue audiobook export",
    });

    fireEvent.click(queueButton);

    expect(await screen.findByRole("button", { name: "Queueing export..." })).toBeDisabled();

    expect(screen.getByRole("button", { name: "Export audiobook" })).toBeDisabled();
    expect(await screen.findByLabelText("Voice preset")).toHaveValue("11");
    expect(screen.queryByRole("button", { name: "Queue audiobook export" })).not.toBeInTheDocument();

    const jobExportCallsBeforeResolve = fetchMock.mock.calls.filter(
      ([input, init]) =>
        input === "/api/jobs/export" &&
        typeof init === "object" &&
        init !== null &&
        "method" in init &&
        init.method === "POST",
    );

    expect(jobExportCallsBeforeResolve).toHaveLength(1);

    queuedExportRequest.resolve({
      ok: true,
      status: 201,
      json: async () => buildQueuedJob(),
    });

    expect(await screen.findByRole("heading", { name: "Export Queue" })).toBeInTheDocument();
  });

  it("does not misdiagnose a library load failure as a missing document", async () => {
    window.history.pushState({}, "", "/books/7");

    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: false,
          status: 503,
          json: async () => ({
            detail: "Document library unavailable",
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

    expect(await screen.findByRole("heading", { name: "Document unavailable" })).toBeInTheDocument();
    expect(screen.getByText("We couldn't load the library details for this document right now.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Document not found" })).not.toBeInTheDocument();
  });

  it("lets the reader disable and re-enable bookmark tracking for a document", async () => {
    window.history.pushState({}, "", "/books/7");

    let bookmarkEnabled = true;

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
              author: "Open Choice Reader",
              cover_url: "/api/documents/7/cover",
              summary: "A guided MVP walkthrough.",
              total_sections: 2,
              total_chunks: 2,
              estimated_duration_seconds: 12,
              current_chunk_index: bookmarkEnabled ? 1 : null,
              progress_percent: bookmarkEnabled ? 50 : 0,
              bookmark_enabled: bookmarkEnabled,
              is_finished: false,
              finished_at: null,
              last_opened_at: bookmarkEnabled ? "2026-05-08T01:00:00Z" : null,
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/documents/7" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 7,
            title: "Alice Reader MVP",
            format: "epub",
            status: "ready",
            author: "Open Choice Reader",
            cover_url: "/api/documents/7/cover",
            summary: "A guided MVP walkthrough.",
            total_sections: 2,
            total_chunks: 2,
            estimated_duration_seconds: 12,
            current_chunk_index: bookmarkEnabled ? 1 : null,
            progress_percent: bookmarkEnabled ? 50 : 0,
            bookmark_enabled: bookmarkEnabled,
            is_finished: false,
            finished_at: null,
            last_opened_at: bookmarkEnabled ? "2026-05-08T01:00:00Z" : null,
            sections: [],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/voices/options" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: "builtin:piper:default",
              name: "Default",
              voice_type: "built_in",
              engine: "piper",
              mode_label: "Fast reader",
              description: "Local Piper voice for quick read-aloud and fallback export.",
              availability: "available",
              availability_detail: "Piper is ready with 1 local voice.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/settings" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            default_live_voice_id: "builtin:piper:default",
            default_export_voice_id: "builtin:piper:default",
            fallback_voice_id: "builtin:piper:default",
            selected_clone_model_engine: "qwen3_clone_0_6b",
            engine_statuses: [],
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
          }),
        });
      }

      if (typeof input === "string" && input === "/api/documents/7/bookmark" && init?.method === "PATCH") {
        bookmarkEnabled = JSON.parse(String(init.body)).enabled;
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 7,
            title: "Alice Reader MVP",
            format: "epub",
            status: "ready",
            author: "Open Choice Reader",
            cover_url: "/api/documents/7/cover",
            summary: "A guided MVP walkthrough.",
            total_sections: 2,
            total_chunks: 2,
            estimated_duration_seconds: 12,
            current_chunk_index: bookmarkEnabled ? 1 : null,
            progress_percent: bookmarkEnabled ? 50 : 0,
            bookmark_enabled: bookmarkEnabled,
            is_finished: false,
            finished_at: null,
            last_opened_at: bookmarkEnabled ? "2026-05-08T01:00:00Z" : null,
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

    expect(await screen.findByRole("heading", { name: "Alice Reader MVP" })).toBeInTheDocument();
    expect(screen.getByText("Resume saved at 50% complete")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Disable bookmark" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/documents/7/bookmark", {
        body: JSON.stringify({ enabled: false }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "PATCH",
      });
    });

    expect((await screen.findAllByText("Bookmark off")).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Enable bookmark" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/documents/7/bookmark", {
        body: JSON.stringify({ enabled: true }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "PATCH",
      });
    });
  });

  it("lets the reader mark a document finished and clear that state later", async () => {
    window.history.pushState({}, "", "/books/7");

    let isFinished = false;

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
              author: "Open Choice Reader",
              cover_url: "/api/documents/7/cover",
              summary: "A guided MVP walkthrough.",
              total_sections: 2,
              total_chunks: 2,
              estimated_duration_seconds: 12,
              current_chunk_index: isFinished ? null : 1,
              progress_percent: isFinished ? 100 : 50,
              bookmark_enabled: true,
              is_finished: isFinished,
              finished_at: isFinished ? "2026-05-08T02:00:00Z" : null,
              last_opened_at: isFinished ? null : "2026-05-08T01:00:00Z",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/documents/7" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 7,
            title: "Alice Reader MVP",
            format: "epub",
            status: "ready",
            author: "Open Choice Reader",
            cover_url: "/api/documents/7/cover",
            summary: "A guided MVP walkthrough.",
            total_sections: 2,
            total_chunks: 2,
            estimated_duration_seconds: 12,
            current_chunk_index: isFinished ? null : 1,
            progress_percent: isFinished ? 100 : 50,
            bookmark_enabled: true,
            is_finished: isFinished,
            finished_at: isFinished ? "2026-05-08T02:00:00Z" : null,
            last_opened_at: isFinished ? null : "2026-05-08T01:00:00Z",
            sections: [],
          }),
        });
      }

      if (typeof input === "string" && input === "/api/voices/options" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: "builtin:piper:default",
              name: "Default",
              voice_type: "built_in",
              engine: "piper",
              mode_label: "Fast reader",
              description: "Local Piper voice for quick read-aloud and fallback export.",
              availability: "available",
              availability_detail: "Piper is ready with 1 local voice.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/settings" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            default_live_voice_id: "builtin:piper:default",
            default_export_voice_id: "builtin:piper:default",
            fallback_voice_id: "builtin:piper:default",
            selected_clone_model_engine: "qwen3_clone_0_6b",
            engine_statuses: [],
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
          }),
        });
      }

      if (typeof input === "string" && input === "/api/documents/7/finished" && init?.method === "POST") {
        isFinished = true;
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 7,
            title: "Alice Reader MVP",
            format: "epub",
            status: "ready",
            author: "Open Choice Reader",
            cover_url: "/api/documents/7/cover",
            summary: "A guided MVP walkthrough.",
            total_sections: 2,
            total_chunks: 2,
            estimated_duration_seconds: 12,
            current_chunk_index: null,
            progress_percent: 100,
            bookmark_enabled: true,
            is_finished: true,
            finished_at: "2026-05-08T02:00:00Z",
            last_opened_at: null,
          }),
        });
      }

      if (typeof input === "string" && input === "/api/documents/7/finished" && init?.method === "DELETE") {
        isFinished = false;
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 7,
            title: "Alice Reader MVP",
            format: "epub",
            status: "ready",
            author: "Open Choice Reader",
            cover_url: "/api/documents/7/cover",
            summary: "A guided MVP walkthrough.",
            total_sections: 2,
            total_chunks: 2,
            estimated_duration_seconds: 12,
            current_chunk_index: null,
            progress_percent: 0,
            bookmark_enabled: true,
            is_finished: false,
            finished_at: null,
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

    expect(await screen.findByRole("heading", { name: "Alice Reader MVP" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Mark finished" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/documents/7/finished", {
        method: "POST",
      });
    });

    expect((await screen.findAllByText("Finished")).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Mark unfinished" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/documents/7/finished", {
        method: "DELETE",
      });
    });
  });

  it("removes the document after an explicit confirmation", async () => {
    window.history.pushState({}, "", "/books/7");

    render(<App />);

    expect(await screen.findByRole("button", { name: "Remove from library" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Remove from library" }));

    const dialog = await screen.findByRole("dialog", { name: "Confirm removal" });
    expect(within(dialog).getByText(/Permanently remove "Alice Reader MVP"/)).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: "Remove book" }));

    await waitFor(() => {
      const deleteCall = fetchMock.mock.calls.find(
        ([input, init]) =>
          input === "/api/documents/7" && (init as RequestInit | undefined)?.method === "DELETE",
      );
      expect(deleteCall).toBeDefined();
    });

    expect(await screen.findByRole("heading", { name: "Library" })).toBeInTheDocument();
  });
});
