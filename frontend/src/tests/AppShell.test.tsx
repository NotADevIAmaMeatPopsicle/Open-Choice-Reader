import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

function buildPlaybackSession(overrides?: Partial<Record<string, unknown>>) {
  return {
    id: 9,
    document_id: 1,
    document_title: "Alice Reader MVP",
    document_author: "Alice",
    cover_url: "/api/documents/1/cover",
    current_chunk_index: 1,
    total_chunks: 4,
    audio_url: "/api/playback/audio/9",
    voice_option_id: "builtin:piper:default",
    playback_speed: 1.55,
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

describe("AppShell", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    let settingsState = {
      default_live_voice_id: "builtin:piper:default",
      default_export_voice_id: "builtin:piper:default",
      fallback_voice_id: "builtin:piper:default",
      selected_clone_model_engine: "qwen3_clone_0_6b",
      active_theme_id: "ocean",
      active_theme: {
        id: "ocean",
        name: "Ocean",
        description: "Cool blue shelving with a brighter media-center accent palette.",
        source_kind: "house",
        source_label: "Open Choice Reader",
        source_reference: null,
        is_builtin: true,
        sort_order: 20,
        family: "house",
        preview_variant: "standard",
        background_asset_path: null,
        background_overlay_path: null,
        shelf_asset_path: null,
        surface_texture_asset_path: null,
        supports_mix_and_match: true,
        tokens: {
          "--color-bg": "#10171c",
          "--color-accent": "#5bc0d1",
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
        usage_summary:
          "Saved cloned presets can be used for live reading and audiobook export on Server when the clone runtime is available.",
        execution_summary:
          "Live cloned reading and audiobook exports run on the connected Server host when the clone runtime is available.",
        available_models: [],
      },
      ui_theme: "ocean",
      sidebar_width_px: 92,
      sidebar_mode: "compact",
      dock_position: "top-center",
      tooltips_enabled: true,
      default_playback_speed: 1.55,
      auto_pause_on_interrupt: true,
      library_view_mode: "cover",
      background_override_theme_id: null,
      shelf_override_theme_id: null,
    };

    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
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

      if (typeof input === "string" && input === "/api/playback/sessions/9" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => buildPlaybackSession(),
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
              description: "Local Piper voice.",
              availability: "available",
              availability_detail: "Piper is ready with 1 local voice.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
              model_name: null,
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

    Object.defineProperty(window.HTMLMediaElement.prototype, "load", {
      configurable: true,
      value: vi.fn(),
    });
    Object.defineProperty(window.HTMLMediaElement.prototype, "play", {
      configurable: true,
      value: vi.fn().mockResolvedValue(undefined),
    });
    Object.defineProperty(window.HTMLMediaElement.prototype, "pause", {
      configurable: true,
      value: vi.fn(),
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("renders the library navigation shell and empty persistent dock", async () => {
    window.history.pushState({}, "", "/home");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Home" })).toBeInTheDocument();
    await waitFor(() => expect(document.documentElement).toHaveAttribute("data-theme", "ocean"));
    expect(document.documentElement.style.getPropertyValue("--color-bg")).toBe("#10171c");
    expect(document.documentElement.style.getPropertyValue("--color-accent")).toBe("#5bc0d1");
    expect(screen.getByRole("navigation", { name: "Primary" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Library" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Series" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Collections" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Issues" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Themes" })).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: "Search library" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open export queue" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open settings" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Local host" })).toBeInTheDocument();
    expect(screen.getByLabelText("Now playing dock")).toBeInTheDocument();
    expect(screen.getByText("Nothing playing yet")).toBeInTheDocument();
  });

  it("places Settings and Voices directly below Library in the left rail", async () => {
    window.history.pushState({}, "", "/home");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Home" })).toBeInTheDocument();

    const links = screen
      .getByRole("navigation", { name: "Primary" })
      .querySelectorAll<HTMLAnchorElement>(".sidebar-nav__link");
    const labels = Array.from(links).map((link) => link.textContent?.trim() ?? "");

    expect(labels).toEqual([
      "Home",
      "Discover",
      "Library",
      "Settings",
      "Voices",
      "Friends",
      "Series",
      "Collections",
      "Issues",
      "Jobs",
      "Themes",
      "Admin",
    ]);
  });

  it("hydrates the persistent dock from the stored playback session and can reopen the reader", async () => {
    window.localStorage.setItem("open-choice-reader:active-session-id", "9");
    window.history.pushState({}, "", "/home");
    const windowOpenSpy = vi.spyOn(window, "open").mockImplementation(() => null);

    render(<App />);

    expect(await screen.findByText("Alice Reader MVP")).toBeInTheDocument();
    expect(screen.getByText("Chunk 2 of 4")).toBeInTheDocument();
    expect(screen.getByText("Narrator: Default | Engine: Piper")).toBeInTheDocument();
    expect(screen.getByText("50% complete")).toBeInTheDocument();
    expect(screen.getByLabelText("Listening progress")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resume reader" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Jump back 5 seconds" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Jump back 30 seconds" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Jump forward 5 seconds" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Jump forward 30 seconds" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Decrease playback speed" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Increase playback speed" })).toBeInTheDocument();
    expect(screen.getByText("1.55x")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pop out player" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open current book" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open jobs queue" })).toBeInTheDocument();
    expect(screen.getByLabelText("Player volume")).toHaveAttribute("title", "85% Volume");

    fireEvent.click(screen.getByRole("button", { name: "Pop out player" }));

    expect(windowOpenSpy).toHaveBeenCalledWith(
      "/player/9?popout=1",
      "open-choice-reader-player-9",
      expect.stringContaining("width=820"),
    );

    fireEvent.click(screen.getByRole("button", { name: "Open current book" }));

    await waitFor(() => {
      expect(window.location.pathname).toBe("/books/1");
    });

    windowOpenSpy.mockRestore();
  });

  it("uses the global search field to filter library cards", async () => {
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
              summary: "A dystopian future",
              total_sections: 10,
              total_chunks: 100,
              estimated_duration_seconds: 600,
              current_chunk_index: 12,
              progress_percent: 12,
              last_opened_at: "2026-05-08T01:00:00Z",
            },
            {
              id: 2,
              title: "Animal Farm",
              format: "epub",
              status: "ready",
              author: "George Orwell",
              cover_url: "/api/documents/2/cover",
              summary: "A political fable",
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

    render(<App />);

    expect(await screen.findByRole("button", { name: "Open spotlight for Brave New World" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open spotlight for Animal Farm" })).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: "Search library" }), {
      target: { value: "animal" },
    });

    expect(screen.queryByRole("button", { name: "Open spotlight for Brave New World" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open spotlight for Animal Farm" })).toBeInTheDocument();
  });

  it("shows an issue badge in the navigation when Alice has open issues", async () => {
    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/issues" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            total_count: 3,
            counts_by_severity: { error: 2, warning: 1 },
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

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    vi.stubGlobal("fetch", fetchMock);
    window.history.pushState({}, "", "/home");

    render(<App />);

    expect(await screen.findByLabelText("3 issues need attention")).toBeInTheDocument();
  });

  it("shows a sidebar toggle and saves icon-only mode when the rail is collapsed", async () => {
    window.history.pushState({}, "", "/home");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Home" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /collapse sidebar/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /collapse sidebar/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/settings",
        expect.objectContaining({
          method: "PUT",
        }),
      );
    });
    expect(screen.getByRole("navigation", { name: "Primary" })).toHaveClass("sidebar-nav--icon");
  });

  it("marks the shell as light appearance when a light theme is active and the rail is collapsed", async () => {
    window.history.pushState({}, "", "/home");

    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
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

      if (typeof input === "string" && input === "/api/playback/sessions/9" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => buildPlaybackSession(),
        });
      }

      if (typeof input === "string" && input === "/api/voices/options" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => [],
        });
      }

      if (typeof input === "string" && input === "/api/settings" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            default_live_voice_id: "builtin:kokoro:heart",
            default_export_voice_id: "preset:warm-narrator",
            fallback_voice_id: "builtin:kokoro:heart",
            selected_clone_model_engine: "qwen3_clone_0_6b",
            active_theme_id: "sunlit-reading-room",
            active_theme: {
              id: "sunlit-reading-room",
              name: "Sunlit Reading Room",
              description: "Warm vellum surfaces and bright reading-room contrast.",
              source_kind: "showcase",
              source_label: "Open Choice Reader",
              source_reference: null,
              is_builtin: true,
              sort_order: 101,
              family: "showcase",
              preview_variant: "light-airy",
              background_asset_path: null,
              background_overlay_path: null,
              shelf_asset_path: null,
              surface_texture_asset_path: null,
              supports_mix_and_match: true,
              tokens: {
                "--color-bg": "#f7efe2",
                "--color-panel": "rgba(255, 250, 242, 0.94)",
                "--color-accent": "#c88b33",
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
              preset_count: 1,
              availability: "available",
              availability_detail: "Ready",
              usage_summary: "Saved cloned presets are used for audiobook export, not instant live reading.",
              execution_summary:
                "Cloned audiobook exports run on the connected Server host when the clone runtime is available.",
              available_models: [],
            },
            ui_theme: "sunlit-reading-room",
            sidebar_width_px: 112,
            sidebar_mode: "icon",
            dock_position: "bottom",
            tooltips_enabled: true,
            default_playback_speed: 1.5,
            auto_pause_on_interrupt: true,
            library_view_mode: "cover",
            background_override_theme_id: null,
            shelf_override_theme_id: null,
          }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => [],
      });
    });

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Home" })).toBeInTheDocument();
    await waitFor(() => expect(document.documentElement).toHaveAttribute("data-theme-appearance", "light"));
    expect(document.querySelector(".app-shell")).toHaveClass("app-shell--appearance-light");
    expect(screen.getByRole("navigation", { name: "Primary" })).toHaveClass("sidebar-nav--icon");
  });

  it("treats a legacy compact rail setting as the fully expanded rail", async () => {
    window.history.pushState({}, "", "/home");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Home" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary" })).toHaveClass("sidebar-nav--expanded");
    expect(document.querySelector(".app-shell")).toHaveClass("app-shell--sidebar-expanded");
  });
});
