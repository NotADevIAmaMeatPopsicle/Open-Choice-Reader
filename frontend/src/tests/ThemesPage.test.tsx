import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { withAuthenticatedAppFetch } from "./support/authSessionFetch";

type FetchResponse = {
  json: () => Promise<unknown>;
  ok: boolean;
  status?: number;
};

type ThemeImportResponse = {
  report: {
    detected_variable_count: number;
    fallback_tokens: Array<{ reason: string; target_token: string }>;
    ignored_variables: string[];
    mapped_variables: Array<{ source_variable: string; target_token: string }>;
  };
  theme: ReturnType<typeof buildTheme>;
};

function buildTheme(id: string, overrides: Record<string, unknown> = {}) {
  const baseThemes: Record<string, Record<string, unknown>> = {
    ember: {
      id: "ember",
      name: "Ember",
      description: "Warm shelves, amber highlights, and the original house look.",
      source_kind: "house",
      source_label: "Open Choice Reader",
      source_reference: null,
      is_builtin: true,
      sort_order: 10,
      family: "house",
      preview_variant: "standard",
      background_asset_path: null,
      background_overlay_path: null,
      shelf_asset_path: null,
      surface_texture_asset_path: null,
      supports_mix_and_match: true,
      tokens: {
        "--color-bg": "#151413",
        "--color-accent": "#d7a24c",
        "--color-panel": "rgba(25, 24, 23, 0.94)",
      },
    },
    ocean: {
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
        "--color-panel": "rgba(18, 28, 34, 0.94)",
      },
    },
    forest: {
      id: "forest",
      name: "Forest",
      description: "Deep green shelves with a softer natural accent range.",
      source_kind: "house",
      source_label: "Open Choice Reader",
      source_reference: null,
      is_builtin: true,
      sort_order: 30,
      family: "house",
      preview_variant: "standard",
      background_asset_path: null,
      background_overlay_path: null,
      shelf_asset_path: null,
      surface_texture_asset_path: null,
      supports_mix_and_match: true,
      tokens: {
        "--color-bg": "#131814",
        "--color-accent": "#93c572",
        "--color-panel": "rgba(23, 30, 24, 0.95)",
      },
    },
    "midnight-ink": {
      id: "midnight-ink",
      name: "Midnight Ink",
      description: "Reading-focused contrast with a crisp ink-blue accent.",
      source_kind: "inspired",
      source_label: "Reading-focused",
      source_reference: null,
      is_builtin: true,
      sort_order: 40,
      family: "reader_focused",
      preview_variant: "standard",
      background_asset_path: null,
      background_overlay_path: null,
      shelf_asset_path: null,
      surface_texture_asset_path: null,
      supports_mix_and_match: true,
      tokens: {
        "--color-bg": "#0f1319",
        "--color-accent": "#72b7ff",
        "--color-panel": "rgba(18, 23, 31, 0.94)",
      },
    },
    "projector-noir": {
      id: "projector-noir",
      name: "Projector Noir",
      description: "Cinema darkness with a luminous cyan cue.",
      source_kind: "inspired",
      source_label: "Cinema-focused",
      source_reference: null,
      is_builtin: true,
      sort_order: 70,
      family: "cinema_focused",
      preview_variant: "standard",
      background_asset_path: null,
      background_overlay_path: null,
      shelf_asset_path: null,
      surface_texture_asset_path: null,
      supports_mix_and_match: true,
      tokens: {
        "--color-bg": "#0a0e17",
        "--color-accent": "#66d4ff",
        "--color-panel": "rgba(13, 18, 29, 0.95)",
      },
    },
    "signal-mint": {
      id: "signal-mint",
      name: "Signal Mint",
      description: "Mint contrast with a cleaner player-app silhouette.",
      source_kind: "inspired",
      source_label: "Player-focused",
      source_reference: null,
      is_builtin: true,
      sort_order: 100,
      family: "player_focused",
      preview_variant: "standard",
      background_asset_path: null,
      background_overlay_path: null,
      shelf_asset_path: null,
      surface_texture_asset_path: null,
      supports_mix_and_match: true,
      tokens: {
        "--color-bg": "#111517",
        "--color-accent": "#5fd7b3",
        "--color-panel": "rgba(18, 24, 27, 0.94)",
      },
    },
    "sunlit-reading-room": {
      id: "sunlit-reading-room",
      name: "Sunlit Reading Room",
      description: "Bright cream paper, pale oak shelves, and a calmer daytime glow.",
      source_kind: "showcase",
      source_label: "Showcase pack",
      source_reference: null,
      is_builtin: true,
      sort_order: 130,
      family: "showcase",
      preview_variant: "light-airy",
      background_asset_path: "/theme-assets/backgrounds/sunlit-reading-room.svg",
      background_overlay_path: "/theme-assets/textures/paper-glow-light.svg",
      shelf_asset_path: "/theme-assets/shelves/sunlit-oak-shelf.svg",
      surface_texture_asset_path: "/theme-assets/textures/parchment-soft.svg",
      supports_mix_and_match: true,
      tokens: {
        "--color-bg": "#f4ecde",
        "--color-accent": "#ba7f33",
        "--color-panel": "rgba(255, 248, 239, 0.92)",
      },
    },
    "mahogany-stacks": {
      id: "mahogany-stacks",
      name: "Mahogany Stacks",
      description: "Classic dark-library warmth with brass glow and deeper shelf definition.",
      source_kind: "showcase",
      source_label: "Showcase pack",
      source_reference: null,
      is_builtin: true,
      sort_order: 170,
      family: "showcase",
      preview_variant: "dark-cozy",
      background_asset_path: "/theme-assets/backgrounds/mahogany-stacks.svg",
      background_overlay_path: "/theme-assets/textures/warm-vignette.svg",
      shelf_asset_path: "/theme-assets/shelves/mahogany-shelf.svg",
      surface_texture_asset_path: "/theme-assets/textures/woodgrain-dark.svg",
      supports_mix_and_match: true,
      tokens: {
        "--color-bg": "#16110e",
        "--color-accent": "#c98e52",
        "--color-panel": "rgba(30, 22, 18, 0.93)",
      },
    },
  };

  return {
    ...baseThemes[id],
    ...overrides,
  };
}

function buildSettingsPayload(activeThemeId = "ember") {
  const activeTheme = buildTheme(activeThemeId);

  return {
    active_theme_id: activeThemeId,
    active_theme: activeTheme,
    default_live_voice_id: "builtin:kokoro:af-sarah",
    default_export_voice_id: "preset:11",
    fallback_voice_id: "builtin:piper:fast-reader",
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
      preset_count: 1,
      availability: "available",
      availability_detail: "Ready",
      usage_summary: "Saved cloned presets are used for audiobook export, not instant live reading.",
      execution_summary: "Cloned audiobook exports run on the connected Server host when the clone runtime is available.",
      available_models: [],
    },
    ui_theme: activeThemeId,
    sidebar_width_px: 112,
    sidebar_mode: "compact",
    dock_position: "bottom",
    tooltips_enabled: true,
    default_playback_speed: 1.25,
    auto_pause_on_interrupt: true,
    library_view_mode: "cover",
    background_override_theme_id: null,
    shelf_override_theme_id: null,
  };
}

describe("ThemesPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    let currentThemeId = "ember";
    let currentThemes = [
      buildTheme("ember"),
      buildTheme("ocean"),
      buildTheme("forest"),
      buildTheme("midnight-ink"),
      buildTheme("projector-noir"),
      buildTheme("signal-mint"),
      buildTheme("sunlit-reading-room"),
      buildTheme("mahogany-stacks"),
    ];

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/issues" && !init) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            total_count: 0,
            counts_by_severity: {},
            items: [],
          }),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/voices/options" && !init) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [],
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/settings" && (!init || init.method === undefined)) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload(currentThemeId),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/settings" && init?.method === "PUT") {
        const body = JSON.parse(String(init.body ?? "{}")) as { active_theme_id?: string; ui_theme?: string };
        currentThemeId = body.active_theme_id ?? body.ui_theme ?? currentThemeId;
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => buildSettingsPayload(currentThemeId),
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/themes" && !init) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => currentThemes,
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/themes/import/kavita" && init?.method === "POST") {
        const formData = init.body as FormData;
        const importedTheme = buildTheme("midnight-harbor", {
          description: "Imported from a Kavita-compatible theme file.",
          id: "midnight-harbor",
          is_builtin: false,
          name: String(formData.get("name") ?? "Midnight Harbor"),
          family: "imported_kavita",
          preview_variant: "standard",
          background_asset_path: null,
          background_overlay_path: null,
          shelf_asset_path: null,
          surface_texture_asset_path: null,
          supports_mix_and_match: true,
          sort_order: 1000,
          source_kind: "imported_kavita",
          source_label: "Kavita import",
          source_reference: "pasted-css",
          tokens: {
            "--color-bg": "#0b1118",
            "--color-accent": "#68b7ff",
            "--color-panel": "rgba(24, 39, 55, 0.92)",
          },
        });
        currentThemes = [...currentThemes, importedTheme];

        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () =>
            ({
              report: {
                detected_variable_count: 6,
                fallback_tokens: [{ reason: "retained_default_theme_value", target_token: "--color-success" }],
                ignored_variables: ["--unsupported-token"],
                mapped_variables: [
                  { source_variable: "--primary-color", target_token: "--color-accent" },
                  { source_variable: "--bs-body-bg", target_token: "--color-bg" },
                ],
              },
              theme: importedTheme,
            }) satisfies ThemeImportResponse,
        } satisfies FetchResponse);
      }

      if (typeof input === "string" && input === "/api/themes/midnight-harbor" && init?.method === "DELETE") {
        currentThemes = currentThemes.filter((theme) => theme.id !== "midnight-harbor");
        return Promise.resolve({
          ok: true,
          status: 204,
          json: async () => ({}),
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

  it("renders a dedicated Themes route with simplified cards and short action labels", async () => {
    window.history.pushState({}, "", "/themes");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Themes" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Themes" })).toBeInTheDocument();
    expect(screen.getByText("Browse installed themes, preview them, and apply the one you want across every connected session.")).toBeInTheDocument();
    const oceanCard = (await screen.findByRole("heading", { name: "Ocean" })).closest(".theme-card");
    expect(oceanCard).not.toBeNull();
    expect(screen.getAllByRole("button", { name: "Preview" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "Apply" }).length).toBeGreaterThan(0);
    expect(within(oceanCard as HTMLElement).queryByText(/Kind:/i)).not.toBeInTheDocument();
    expect(within(oceanCard as HTMLElement).queryByText(/Source:/i)).not.toBeInTheDocument();
    expect(screen.getAllByText("House theme").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Reading-focused").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Cinema-focused").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Player-focused").length).toBeGreaterThan(0);
  });

  it("renders a showcase theme group with mix-and-match controls but without verbose asset badges", async () => {
    window.history.pushState({}, "", "/themes");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Themes" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: /showcase themes/i })).toBeInTheDocument();
    const showcaseCard = (await screen.findByRole("heading", { name: "Sunlit Reading Room" })).closest(".theme-card");
    expect(showcaseCard).not.toBeNull();
    expect(within(showcaseCard as HTMLElement).queryByText(/includes shelf art/i)).not.toBeInTheDocument();
    expect(within(showcaseCard as HTMLElement).queryByText(/includes background art/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/background donor/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/shelf donor/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reset to theme defaults/i })).toBeInTheDocument();
  });

  it("previews another theme locally and applies it through the persisted settings flow", async () => {
    window.history.pushState({}, "", "/themes");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Themes" })).toBeInTheDocument();
    const oceanCard = (await screen.findByRole("heading", { name: "Ocean" })).closest(".theme-card");
    expect(oceanCard).not.toBeNull();
    fireEvent.click(within(oceanCard as HTMLElement).getByRole("button", { name: "Preview" }));

    const previewPanel = screen.getByLabelText("Theme preview");
    expect(within(previewPanel).getByText("Ocean")).toBeInTheDocument();
    expect(within(previewPanel).getByText("Previewing this theme")).toBeInTheDocument();

    fireEvent.click(within(oceanCard as HTMLElement).getByRole("button", { name: "Apply" }));

    await waitFor(() => {
      expect(document.documentElement).toHaveAttribute("data-theme", "ocean");
    });
    expect(document.documentElement.style.getPropertyValue("--color-bg")).toBe("#10171c");
    expect(document.documentElement).toHaveAttribute("data-theme", "ocean");
  });

  it("imports a pasted Kavita theme, shows the conversion report, and lets the user delete the imported theme", async () => {
    window.history.pushState({}, "", "/themes");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Themes" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Imported theme name"), {
      target: { value: "Midnight Harbor" },
    });
    fireEvent.change(screen.getByLabelText("Paste Kavita CSS"), {
      target: {
        value: `
        :root .bg-midnight-harbor {
          --primary-color: #68b7ff;
          --bs-body-bg: #0b1118;
          --unsupported-token: #fff;
        }`,
      },
    });

    fireEvent.click(screen.getByRole("button", { name: "Import pasted CSS" }));

    expect(await screen.findByText("Midnight Harbor")).toBeInTheDocument();
    expect(screen.getByText("Imported theme ready")).toBeInTheDocument();
    expect(screen.getByText("Mapped 2 supported variables from 6 detected declarations.")).toBeInTheDocument();
    expect(screen.getByText("Ignored variables: --unsupported-token")).toBeInTheDocument();
    const importedThemeHeadings = screen.getAllByRole("heading", { name: "Midnight Harbor" });
    const importedThemeCard = importedThemeHeadings
      .map((heading) => heading.closest(".theme-card"))
      .find((card) => card !== null);
    expect(importedThemeCard).not.toBeNull();
    expect(within(importedThemeCard as HTMLElement).getByRole("button", { name: "Delete" })).toBeInTheDocument();

    fireEvent.click(within(importedThemeCard as HTMLElement).getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(screen.queryByText("Midnight Harbor")).not.toBeInTheDocument();
    });
  });
});
