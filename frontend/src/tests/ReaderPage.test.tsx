import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { withAuthenticatedAppFetch } from "./support/authSessionFetch";

function buildPlaybackSession(overrides?: Partial<Record<string, unknown>>) {
  return {
    id: 1,
    document_id: 1,
    document_title: "Alice Reader MVP",
    document_author: "Alice",
    cover_url: "/api/documents/1/cover",
    current_chunk_index: 1,
    total_chunks: 4,
    audio_url: "/api/playback/audio/1",
    engine_name: "piper",
    voice_option_id: "builtin:piper:default",
    voice_model_name: null,
    playback_speed: 1.0,
    current_chunk_text: "Second sentence.",
    current_section_title: "Chapter One",
    section_chunks: [
      {
        chunk_index: 0,
        text: "First sentence.",
        is_current: false,
      },
      {
        chunk_index: 1,
        text: "Second sentence.",
        is_current: true,
      },
    ],
    ...overrides,
  };
}

describe("ReaderPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  let loadMock: ReturnType<typeof vi.fn>;
  let pauseMock: ReturnType<typeof vi.fn>;
  let playMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 1,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/documents/1" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 1,
            title: "Alice Reader MVP",
            format: "epub",
            status: "ready",
            author: "Alice",
            cover_url: "/api/documents/1/cover",
            total_sections: 1,
            total_chunks: 4,
            progress_percent: 25,
            sections: [
              {
                id: 1,
                position: 0,
                title: "Chapter One",
                chunk_start_index: 0,
                chunk_count: 2,
                preview_text: "First sentence.",
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
              description: "Local Piper voice.",
              availability: "available",
              availability_detail: "Piper is ready with 1 local voice.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
            },
            {
              id: "builtin:piper:second-reader",
              name: "Second Reader",
              voice_type: "built_in",
              engine: "piper",
              mode_label: "Fast reader",
              description: "Alternate local Piper voice.",
              availability: "available",
              availability_detail: "Piper is ready with 2 local voices.",
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
              usage_summary:
                "Saved cloned presets can be used for live reading and audiobook export on Server when the clone runtime is available.",
              execution_summary:
                "Live cloned reading and audiobook exports run on the connected Server host when the clone runtime is available.",
              available_models: [],
            },
            ui_theme: "ember",
            sidebar_width_px: 112,
            sidebar_mode: "expanded",
            dock_position: "bottom",
            tooltips_enabled: true,
            default_playback_speed: 1.55,
            auto_pause_on_interrupt: true,
          }),
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions/1" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => buildPlaybackSession(),
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions/1" && init?.method === "PATCH") {
        const payload = JSON.parse(String(init.body ?? "{}")) as {
          current_chunk_index?: number;
          playback_speed?: number;
          voice_option_id?: string;
        };

        if (payload.playback_speed) {
          return Promise.resolve({
            ok: true,
            json: async () =>
              buildPlaybackSession({
                playback_speed: payload.playback_speed,
                voice_option_id: payload.voice_option_id ?? "builtin:piper:default",
              }),
          });
        }

        if (payload.voice_option_id) {
          return Promise.resolve({
            ok: true,
            json: async () =>
              buildPlaybackSession({
                voice_option_id: payload.voice_option_id,
              }),
          });
        }

        return Promise.resolve({
          ok: true,
          json: async () =>
            buildPlaybackSession({
              current_chunk_index: 2,
              current_chunk_text: "Third sentence.",
              section_chunks: [
                {
                  chunk_index: 1,
                  text: "Second sentence.",
                  is_current: false,
                },
                {
                  chunk_index: 2,
                  text: "Third sentence.",
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

    playMock = vi.fn(function play(this: HTMLMediaElement) {
      this.dispatchEvent(new Event("play"));
      return Promise.resolve();
    });
    pauseMock = vi.fn(function pause(this: HTMLMediaElement) {
      this.dispatchEvent(new Event("pause"));
    });
    loadMock = vi.fn();

    Object.defineProperty(window.HTMLMediaElement.prototype, "load", {
      configurable: true,
      value: loadMock,
    });
    Object.defineProperty(window.HTMLMediaElement.prototype, "play", {
      configurable: true,
      value: playMock,
    });
    Object.defineProperty(window.HTMLMediaElement.prototype, "pause", {
      configurable: true,
      value: pauseMock,
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("loads persisted reader progress, current text, and active chunk highlight for the session", async () => {
    window.history.pushState({}, "", "/reader/1");

    const { container } = render(<App />);

    expect(await screen.findByRole("heading", { name: "Reading progress" })).toBeInTheDocument();
    expect(await screen.findByText("Narrator: Default | Engine: Piper | 1x playback with synced local progress.")).toBeInTheDocument();
    expect(screen.getByText("Built-in narrator | Live + Export | Piper is ready with 1 local voice.")).toBeInTheDocument();
    expect(await screen.findByText("Current chunk index: 1")).toBeInTheDocument();
    expect(screen.getByText("Chapter One")).toBeInTheDocument();
    expect(screen.getByText("Second sentence.").closest("[aria-current='true']")).not.toBeNull();
    expect(container.querySelector("audio")).toHaveAttribute(
      "src",
      "/api/playback/audio/1?chunk=1&voice=builtin%3Apiper%3Adefault",
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/playback/sessions/1");
    });
  });

  it("routes play and pause controls through the browser audio element", async () => {
    window.history.pushState({}, "", "/reader/1");

    render(<App />);

    const transport = await screen.findByLabelText("Transport controls");

    fireEvent.click(within(transport).getByRole("button", { name: "Play" }));

    await waitFor(() => {
      expect(playMock).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(within(transport).getByRole("button", { name: "Pause" }));

    await waitFor(() => {
      expect(pauseMock).toHaveBeenCalledTimes(1);
    });

    expect(await screen.findByRole("button", { name: "Play" })).toBeInTheDocument();
  });

  it("pauses playback when the page is backgrounded through a pagehide event", async () => {
    window.history.pushState({}, "", "/reader/1");

    render(<App />);

    const transport = await screen.findByLabelText("Transport controls");

    fireEvent.click(within(transport).getByRole("button", { name: "Play" }));

    await waitFor(() => {
      expect(playMock).toHaveBeenCalledTimes(1);
    });

    fireEvent(window, new Event("pagehide"));

    await waitFor(() => {
      expect(pauseMock).toHaveBeenCalledTimes(1);
    });
  });

  it("syncs progress updates through the playback session patch endpoint", async () => {
    window.history.pushState({}, "", "/reader/1");

    const { container } = render(<App />);

    expect(await screen.findByText("Current chunk index: 1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Next chunk" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/playback/sessions/1", {
        body: JSON.stringify({ current_chunk_index: 2 }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "PATCH",
      });
    });

    expect(await screen.findByText("Current chunk index: 2")).toBeInTheDocument();
    expect(screen.getByText("Third sentence.").closest("[aria-current='true']")).not.toBeNull();
    expect(container.querySelector("audio")).toHaveAttribute(
      "src",
      "/api/playback/audio/1?chunk=2&voice=builtin%3Apiper%3Adefault",
    );
  });

  it("does not advance past the final chunk", async () => {
    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/documents" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 1,
              title: "Alice Reader MVP",
              format: "epub",
              status: "ready",
            },
          ],
        });
      }

      if (typeof input === "string" && input === "/api/documents/1" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            id: 1,
            title: "Alice Reader MVP",
            format: "epub",
            status: "ready",
            author: "Alice",
            cover_url: "/api/documents/1/cover",
            total_sections: 1,
            total_chunks: 3,
            progress_percent: 100,
            sections: [
              {
                id: 1,
                position: 0,
                title: "Chapter One",
                chunk_start_index: 0,
                chunk_count: 3,
                preview_text: "First sentence.",
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
              description: "Local Piper voice.",
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
              usage_summary:
                "Saved cloned presets can be used for live reading and audiobook export on Server when the clone runtime is available.",
              execution_summary:
                "Live cloned reading and audiobook exports run on the connected Server host when the clone runtime is available.",
              available_models: [],
            },
            ui_theme: "ember",
            sidebar_width_px: 112,
            sidebar_mode: "expanded",
            dock_position: "bottom",
            tooltips_enabled: true,
            default_playback_speed: 1.55,
            auto_pause_on_interrupt: true,
          }),
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions/1" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () =>
            buildPlaybackSession({
              current_chunk_index: 2,
              total_chunks: 3,
              current_chunk_text: "Third sentence.",
              section_chunks: [
                {
                  chunk_index: 1,
                  text: "Second sentence.",
                  is_current: false,
                },
                {
                  chunk_index: 2,
                  text: "Third sentence.",
                  is_current: true,
                },
              ],
            }),
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions/1" && init?.method === "PATCH") {
        return Promise.resolve({
          ok: false,
          status: 422,
          json: async () => ({
            detail: "Chunk index 3 is out of range for playback session 1",
          }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);
    window.history.pushState({}, "", "/reader/1");

    render(<App />);

    const nextChunkButton = await screen.findByRole("button", { name: "Next chunk" });
    expect(await screen.findByText("Current chunk index: 2")).toBeInTheDocument();

    fireEvent.click(nextChunkButton);

    await waitFor(() => {
      expect(nextChunkButton).toBeDisabled();
    });

    expect(fetchMock).not.toHaveBeenCalledWith("/api/playback/sessions/1", {
      body: JSON.stringify({ current_chunk_index: 3 }),
      headers: {
        "Content-Type": "application/json",
      },
      method: "PATCH",
    });
    expect(screen.queryByText(/out of range/)).not.toBeInTheDocument();
    expect(screen.getByText("Current chunk index: 2")).toBeInTheDocument();
  });

  it("updates speed through the playback session patch endpoint", async () => {
    window.history.pushState({}, "", "/reader/1");

    render(<App />);

    expect(await screen.findByLabelText("Playback speed")).toHaveValue(1);
    expect(screen.getByLabelText("Playback speed")).toHaveAttribute("step", "0.05");

    fireEvent.change(screen.getByLabelText("Playback speed"), {
      target: { value: "1.55" },
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/playback/sessions/1", {
        body: JSON.stringify({ playback_speed: 1.55 }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "PATCH",
      });
    });

    expect(await screen.findByLabelText("Playback speed")).toHaveValue(1.55);
  });

  it("shows document progress and dual rewind controls in the reader transport", async () => {
    window.history.pushState({}, "", "/reader/1");

    render(<App />);

    expect((await screen.findAllByText("50% complete")).length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Document progress")).toHaveValue("1");
    expect(screen.getByRole("button", { name: "Jump back 5 seconds" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Jump back 30 seconds" })).toBeInTheDocument();
  });

  it("rewinds across chunk boundaries when the current chunk is too short", async () => {
    window.history.pushState({}, "", "/reader/1");

    const { container } = render(<App />);

    await screen.findByLabelText("Transport controls");
    const audio = container.querySelector("audio");
    expect(audio).not.toBeNull();

    Object.defineProperty(audio as HTMLAudioElement, "duration", {
      configurable: true,
      get: () => 10,
    });
    (audio as HTMLAudioElement).currentTime = 2;

    fireEvent.click(screen.getByRole("button", { name: "Jump back 5 seconds" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/playback/sessions/1", {
        body: JSON.stringify({ current_chunk_index: 0 }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "PATCH",
      });
    });
  });

  it("advances across chunk boundaries when a forward seek overflows the current chunk", async () => {
    window.history.pushState({}, "", "/reader/1");

    const { container } = render(<App />);

    await screen.findByLabelText("Transport controls");
    const audio = container.querySelector("audio");
    expect(audio).not.toBeNull();

    Object.defineProperty(audio as HTMLAudioElement, "duration", {
      configurable: true,
      get: () => 10,
    });
    (audio as HTMLAudioElement).currentTime = 8;

    fireEvent.click(screen.getByRole("button", { name: "Jump forward 5 seconds" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/playback/sessions/1", {
        body: JSON.stringify({ current_chunk_index: 2 }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "PATCH",
      });
    });
  });

  it("updates the live reading voice through the playback session patch endpoint", async () => {
    window.history.pushState({}, "", "/reader/1");

    render(<App />);

    expect(await screen.findByLabelText("Live reading voice")).toHaveValue("builtin:piper:default");
    expect(screen.getByText("Built-in narrator | Live + Export | Piper is ready with 1 local voice.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Live reading voice"), {
      target: { value: "builtin:piper:second-reader" },
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/playback/sessions/1", {
        body: JSON.stringify({ voice_option_id: "builtin:piper:second-reader" }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "PATCH",
      });
    });

    expect(await screen.findByLabelText("Live reading voice")).toHaveValue("builtin:piper:second-reader");
  });

  it("shows the active clone model and cloned narrator during live cloned reading", async () => {
    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
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
              description: "Local Piper voice.",
              availability: "available",
              availability_detail: "Piper is ready with 1 local voice.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
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
            host_runtime: {
              host_name: "Server",
              runtime_label: "Server GPU host",
              gpu_name: "NVIDIA GeForce RTX 3080",
              execution_summary: "This host is serving Open Choice Reader and performing audio generation here.",
            },
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
              available_models: [],
            },
            ui_theme: "ember",
            sidebar_width_px: 112,
            sidebar_mode: "expanded",
            dock_position: "bottom",
            tooltips_enabled: true,
            default_playback_speed: 1.55,
            auto_pause_on_interrupt: true,
          }),
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions/1" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () =>
            buildPlaybackSession({
              engine_name: "qwen3_clone_1_7b",
              voice_option_id: "preset:11",
              voice_model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);
    window.history.pushState({}, "", "/reader/1");

    render(<App />);

    expect(await screen.findByText(/Narrator: Warm Narrator \| Engine: Qwen3 Clone/)).toBeInTheDocument();
    expect(screen.getAllByText(/Qwen\/Qwen3-TTS-12Hz-1.7B-Base/).length).toBeGreaterThan(0);
  });

  it("keeps reader progress stable when the next progress update is rejected", async () => {
    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/playback/sessions/1" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => buildPlaybackSession(),
        });
      }

      if (typeof input === "string" && input === "/api/playback/sessions/1" && init?.method === "PATCH") {
        return Promise.resolve({
          ok: false,
          status: 422,
          json: async () => ({
            detail: "Chunk index 2 is out of range for playback session 1",
          }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);
    window.history.pushState({}, "", "/reader/1");

    render(<App />);

    expect(await screen.findByText("Current chunk index: 1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Next chunk" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/playback/sessions/1", {
        body: JSON.stringify({ current_chunk_index: 2 }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "PATCH",
      });
    });

    expect(screen.getByText("Current chunk index: 1")).toBeInTheDocument();
  });

  it("renders the dedicated book detail route", async () => {
    window.history.pushState({}, "", "/books/1");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Alice Reader MVP" })).toBeInTheDocument();
    expect(screen.getByText("25% complete")).toBeInTheDocument();
  });
});
