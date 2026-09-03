import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

type FetchResponse = {
  json: () => Promise<unknown>;
  ok: boolean;
  status?: number;
};

describe("SettingsPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  let settingsState: Record<string, unknown>;

  beforeEach(() => {
    settingsState = {
      default_live_voice_id: "builtin:kokoro:af-sarah",
      default_export_voice_id: "preset:11",
      fallback_voice_id: "builtin:piper:fast-reader",
      selected_clone_model_engine: "qwen3_clone_1_7b",
      active_theme_id: "ember",
      active_theme: {
        id: "ember",
        name: "Ember",
        description: "Warm shelves, amber highlights, and the original house look.",
        source_kind: "house",
        source_label: "Open Choice Reader",
        source_reference: null,
        is_builtin: true,
        sort_order: 10,
        tokens: {
          "--color-bg": "#151413",
          "--color-accent": "#d7a24c",
        },
      },
      engine_statuses: [
        {
          engine: "kokoro",
          display_name: "Natural readers",
          availability: "available",
          availability_detail: "Kokoro is ready with 6 built-in voices.",
          supports_live_reading: true,
          supports_export: true,
          engine_family: "kokoro",
          model_name: "Kokoro-82M ONNX",
          voice_count: 6,
        },
        {
          engine: "piper",
          display_name: "Fast fallback readers",
          availability: "available",
          availability_detail: "Piper is ready with 5 built-in voices.",
          supports_live_reading: true,
          supports_export: true,
          engine_family: "piper",
          model_name: null,
          voice_count: 5,
        },
        {
          engine: "qwen3_clone_0_6b",
          display_name: "Premium clone 0.6B",
          availability: "available",
          availability_detail: "Faster premium clone exports are ready.",
          supports_live_reading: false,
          supports_export: true,
          engine_family: "qwen3_clone",
          model_name: "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
          voice_count: 0,
        },
        {
          engine: "qwen3_clone_1_7b",
          display_name: "Premium clone 1.7B",
          availability: "available",
          availability_detail: "Highest-quality premium clone exports are ready.",
          supports_live_reading: false,
          supports_export: true,
          engine_family: "qwen3_clone",
          model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
          voice_count: 0,
        },
      ],
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
          {
            engine: "qwen3_clone_1_7b",
            display_name: "Premium clone 1.7B",
            model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            availability: "available",
            availability_detail: "Highest-quality premium clone exports are ready.",
          },
        ],
      },
      ui_theme: "ember",
      sidebar_width_px: 112,
      sidebar_mode: "expanded",
      dock_position: "bottom",
      tooltips_enabled: true,
      default_playback_speed: 1.55,
      live_narration_pace: 1.25,
      auto_pause_on_interrupt: true,
      library_view_mode: "cover",
      background_override_theme_id: null,
      shelf_override_theme_id: null,
    };

    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/voices/options") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            {
              id: "builtin:kokoro:af-sarah",
              name: "Sarah",
              voice_type: "built_in",
              engine: "kokoro",
              engine_family: "kokoro",
              mode_label: "Natural reader",
              description: "Higher-quality local Kokoro narrator for primary live reading.",
              availability: "available",
              availability_detail: "Kokoro is ready with 6 built-in voices.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
              model_name: "Kokoro-82M ONNX",
            },
            {
              id: "builtin:piper:fast-reader",
              name: "Fast Reader",
              voice_type: "built_in",
              engine: "piper",
              engine_family: "piper",
              mode_label: "Fast fallback",
              description: "Local Piper voice for quick read-aloud and fallback export.",
              availability: "available",
              availability_detail: "Piper is ready with 5 built-in voices.",
              supports_live_reading: true,
              supports_export: true,
              transcript_preview: null,
              model_name: null,
            },
            {
              id: "preset:11",
              name: "Alice Reader",
              voice_type: "cloned",
              engine: "qwen3_clone",
              engine_family: "qwen3_clone",
              mode_label: "Cloned voice",
              description: "Saved reference voice preset for premium audiobook export.",
              availability: "available",
              availability_detail: "Qwen3 clone exports are ready when a saved preset is selected.",
              supports_live_reading: false,
              supports_export: true,
              transcript_preview: "A calm, warm sample transcript.",
              model_name: "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            },
          ],
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/settings" && (!init || init.method === undefined)) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => settingsState,
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/settings" && init?.method === "PUT") {
        settingsState = {
          ...settingsState,
          ...(JSON.parse(String(init.body ?? "{}")) as Record<string, unknown>),
        };

        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => settingsState,
        } satisfies FetchResponse);
      }

      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      } satisfies FetchResponse);
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
    vi.unstubAllGlobals();
  });

  it("renders runtime status plus current narrator defaults without acting like the primary selection page", async () => {
    window.history.pushState({}, "", "/settings");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Manage narrators" })).toHaveAttribute("href", "/voices");
    expect(screen.getByRole("link", { name: "Manage themes" })).toHaveAttribute("href", "/themes");
    expect(screen.queryByLabelText("Default live reading voice")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save voice settings" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Color theme")).not.toBeInTheDocument();

    expect(screen.getByText("Sarah")).toBeInTheDocument();
    expect(screen.getByText("Fast Reader")).toBeInTheDocument();
    expect(screen.getAllByText("Alice Reader").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Premium clone 1.7B").length).toBeGreaterThan(0);
    expect(screen.getByText("Active theme")).toBeInTheDocument();
    expect(screen.getByText("Ember")).toBeInTheDocument();
    expect(screen.getAllByText("Qwen/Qwen3-TTS-12Hz-1.7B-Base").length).toBeGreaterThan(0);
  });

  it("hides operator-facing runtime sections from the consumer settings page", async () => {
    window.history.pushState({}, "", "/settings");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.queryByText("Connected Host")).not.toBeInTheDocument();
    expect(screen.queryByText("Clone Runtime")).not.toBeInTheDocument();
    expect(screen.queryByText("Operator Notes")).not.toBeInTheDocument();
    expect(screen.queryByText("Engine availability")).not.toBeInTheDocument();
  });

  it("renders reader ergonomics and playback preference controls", async () => {
    window.history.pushState({}, "", "/settings");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Sidebar width")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Sidebar layout")).toHaveValue("expanded");
    expect(screen.getByLabelText("Player position")).toHaveValue("bottom");
    expect(screen.getByLabelText("Default playback speed")).toHaveValue(1.55);
    expect(screen.getByLabelText("Narrator pace")).toHaveValue(1.25);
    expect(screen.getByLabelText("Show hover labels for player buttons")).toBeChecked();
    expect(screen.getByLabelText("Pause when Open Choice Reader is backgrounded or the browser reports a media interruption")).toBeChecked();
    expect(
      screen.getByText(/This is best-effort browser behavior\./i),
    ).toBeInTheDocument();
  });

  it("surfaces browser extension setup guidance and a downloadable bundle", async () => {
    window.history.pushState({}, "", "/settings");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Browser extension" })).toBeInTheDocument();
    expect(
      screen.getByText("Install the handoff bundle in Chrome, Edge, Brave, Arc, or another Chromium-based browser."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download Chromium-browser bundle" })).toHaveAttribute(
      "href",
      "/api/extension/chromium",
    );
    expect(screen.getByText("Right-click any page or selected text to import or read it immediately.")).toBeInTheDocument();
    expect(screen.getByText(/http:\/\/127\.0\.0\.1:8000/i)).toBeInTheDocument();
    expect(screen.getByText("Firefox and Safari do not currently have a packaged extension build.")).toBeInTheDocument();
  });

  it("applies saved reader preferences to the shell without requiring a manual reload", async () => {
    window.history.pushState({}, "", "/settings");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary" })).toHaveClass("sidebar-nav--expanded");

    fireEvent.change(screen.getByLabelText("Sidebar layout"), {
      target: { value: "icon" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save reader preferences" }));

    await waitFor(() => {
      expect(screen.getByRole("navigation", { name: "Primary" })).toHaveClass("sidebar-nav--icon");
    });
    expect(screen.getByText("Voice settings saved.")).toBeInTheDocument();
  });

  it("saves the narrator pace alongside the other reader preferences", async () => {
    window.history.pushState({}, "", "/settings");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Narrator pace"), {
      target: { value: "1.5" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save reader preferences" }));

    await waitFor(() => {
      expect(screen.getByText("Voice settings saved.")).toBeInTheDocument();
    });

    const settingsPut = fetchMock.mock.calls.find(
      ([input, init]) => input === "/api/settings" && (init as RequestInit | undefined)?.method === "PUT",
    );
    expect(settingsPut).toBeDefined();
    expect(JSON.parse(String((settingsPut?.[1] as RequestInit | undefined)?.body ?? "{}")).live_narration_pace).toBe(1.5);
  });

  it("lets the signed-in user change their password from settings", async () => {
    window.history.pushState({}, "", "/settings");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Current password"), {
      target: { value: "OpenChoice-Alice-2026!" },
    });
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "a-new-password-123" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "a-new-password-123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Update password" }));

    expect(await screen.findByText("Password updated.")).toBeInTheDocument();

    const changePasswordCall = fetchMock.mock.calls.find(([input]) => input === "/api/auth/change-password");
    expect(changePasswordCall).toBeDefined();
    expect(JSON.parse(String(changePasswordCall?.[1]?.body ?? "{}"))).toEqual({
      current_password: "OpenChoice-Alice-2026!",
      new_password: "a-new-password-123",
    });
  });

  it("rejects mismatched password confirmation without calling the API", async () => {
    window.history.pushState({}, "", "/settings");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Current password"), {
      target: { value: "OpenChoice-Alice-2026!" },
    });
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "new-password-1" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "different-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Update password" }));

    expect(await screen.findByText("New password and confirmation do not match.")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([input]) => input === "/api/auth/change-password")).toBe(false);
  });
});
