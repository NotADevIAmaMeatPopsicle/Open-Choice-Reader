import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

function buildSettingsState() {
  return {
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
      usage_summary: "Saved cloned presets can be used for live reading and audiobook export.",
      execution_summary: "Premium cloned reading runs on Server.",
      available_models: [],
    },
    ui_theme: "ocean",
    sidebar_width_px: 240,
    sidebar_mode: "expanded",
    dock_position: "bottom",
    tooltips_enabled: true,
    default_playback_speed: 1,
    auto_pause_on_interrupt: true,
    library_view_mode: "cover",
    background_override_theme_id: null,
    shelf_override_theme_id: null,
  };
}

describe("Auth flows", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    let bootstrapAvailable = false;
    let currentUser: Record<string, unknown> | null = {
      id: 1,
      username: "avery",
      display_name: "Avery Reader",
      role: "admin",
      status: "active",
      last_login_at: null,
    };
    let invites = [
      {
        id: 2,
        created_by_user_id: 1,
        claimed_by_user_id: null,
        display_name_hint: "Casey Reader",
        role_to_grant: "member",
        expires_at: null,
        claimed_at: null,
        revoked_at: null,
        created_at: "2026-05-12T00:00:00Z",
      },
    ];
    const users = [
      {
        id: 1,
        username: "avery",
        display_name: "Avery Reader",
        role: "admin",
        status: "active",
        last_login_at: null,
      },
    ];

    fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/auth/bootstrap-status" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ bootstrap_available: bootstrapAvailable }),
        });
      }

      if (typeof input === "string" && input === "/api/auth/me" && !init) {
        if (!currentUser) {
          return Promise.resolve({
            ok: false,
            json: async () => ({ detail: "You must be signed in." }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => currentUser,
        });
      }

      if (typeof input === "string" && input === "/api/auth/bootstrap-admin" && init?.method === "POST") {
        currentUser = {
          id: 1,
          username: "admin",
          display_name: "Admin User",
          role: "admin",
          status: "active",
          last_login_at: null,
        };
        bootstrapAvailable = false;
        return Promise.resolve({
          ok: true,
          json: async () => ({ user: currentUser }),
        });
      }

      if (typeof input === "string" && input === "/api/auth/login" && init?.method === "POST") {
        currentUser = {
          id: 1,
          username: "avery",
          display_name: "Avery Reader",
          role: "admin",
          status: "active",
          last_login_at: null,
        };
        return Promise.resolve({
          ok: true,
          json: async () => ({ user: currentUser }),
        });
      }

      if (typeof input === "string" && input === "/api/auth/logout" && init?.method === "POST") {
        currentUser = null;
        return Promise.resolve({
          ok: true,
          json: async () => ({}),
        });
      }

      if (typeof input === "string" && input === "/api/auth/claim-invite" && init?.method === "POST") {
        currentUser = {
          id: 3,
          username: "casey",
          display_name: "Casey Reader",
          role: "member",
          status: "active",
          last_login_at: null,
        };
        return Promise.resolve({
          ok: true,
          json: async () => ({ user: currentUser }),
        });
      }

      if (typeof input === "string" && input === "/api/auth/users" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => users,
        });
      }

      if (typeof input === "string" && input === "/api/auth/invites" && !init) {
        return Promise.resolve({
          ok: true,
          json: async () => invites,
        });
      }

      if (typeof input === "string" && input === "/api/auth/invites" && init?.method === "POST") {
        const createdInvite = {
          id: 4,
          created_by_user_id: 1,
          claimed_by_user_id: null,
          display_name_hint: "Taylor Reader",
          role_to_grant: "member",
          expires_at: null,
          claimed_at: null,
          revoked_at: null,
          created_at: "2026-05-12T00:00:00Z",
        };
        invites = [createdInvite, ...invites];
        return Promise.resolve({
          ok: true,
          json: async () => ({
            invite: createdInvite,
            token: "invite-token-123",
          }),
        });
      }

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
              availability_detail: "Ready",
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
          json: async () => buildSettingsState(),
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
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("shows bootstrap admin when no users exist and enters the app after creation", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({ bootstrap_available: true }),
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Create the first admin account" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct horse battery staple" } });
    fireEvent.change(screen.getByLabelText("Setup token (remote setup only)"), {
      target: { value: "one-time-bootstrap-token" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create admin" }));

    expect(await screen.findByRole("heading", { name: "Library" })).toBeInTheDocument();
    const bootstrapCall = fetchMock.mock.calls.find(
      ([input, init]) => input === "/api/auth/bootstrap-admin" && init?.method === "POST",
    );
    expect(bootstrapCall?.[1]?.headers).toMatchObject({
      "X-Bootstrap-Token": "one-time-bootstrap-token",
    });
    expect(JSON.parse(String(bootstrapCall?.[1]?.body))).not.toHaveProperty("bootstrap_token");
  });

  it("supports login and logout flows", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({ bootstrap_available: false }),
      }),
    );
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        json: async () => ({ detail: "You must be signed in." }),
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Sign in to Open Choice Reader" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "avery" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "reader-password-123" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("button", { name: "Avery Reader" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { name: "Sign in to Open Choice Reader" })).toBeInTheDocument();
  });

  it("shows extension sign-in guidance on the login shell when the extension sends the user back to the app", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({ bootstrap_available: false }),
      }),
    );
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        json: async () => ({ detail: "You must be signed in." }),
      }),
    );

    window.history.pushState({}, "", "/login?reason=extension-auth-required");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Sign in to Open Choice Reader" })).toBeInTheDocument();
    expect(
      screen.getByText(/sign in to open choice reader on this host first, then try the extension again/i),
    ).toBeInTheDocument();
  });

  it("claims invite-only accounts from the claim page", async () => {
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({ bootstrap_available: false }),
      }),
    );
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        json: async () => ({ detail: "You must be signed in." }),
      }),
    );

    window.history.pushState({}, "", "/claim-invite?token=invite-token-123");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Claim an account invite" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("invite-token-123")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "casey" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "reader-password-123" } });
    fireEvent.click(screen.getByRole("button", { name: "Claim invite" }));

    expect(await screen.findByRole("button", { name: "Casey Reader" })).toBeInTheDocument();
  });

  it("hosts user management and invites on the admin page and can create invites", async () => {
    window.history.pushState({}, "", "/admin");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "User management" })).toBeInTheDocument();
    expect((await screen.findAllByText(/Avery Reader/)).length).toBeGreaterThan(0);
    expect(await screen.findByLabelText("Role for avery")).toBeDisabled();

    const invitesPanel = screen.getByLabelText("Admin invites panel");
    expect(within(invitesPanel).getByRole("heading", { name: "Invites" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Invite display-name hint"), { target: { value: "Taylor Reader" } });
    fireEvent.click(screen.getByRole("button", { name: "Create invite" }));

    await waitFor(() => {
      expect(screen.getByText(/invite-token-123/)).toBeInTheDocument();
    });
  });
});
