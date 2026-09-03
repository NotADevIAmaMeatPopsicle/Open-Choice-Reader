import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { withAuthenticatedAppFetch } from "./support/authSessionFetch";

describe("AdminPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    let users = [
      {
        id: 1,
        username: "local-host",
        display_name: "Local host",
        role: "admin",
        status: "active",
        last_login_at: "2026-06-12T00:00:00Z",
        created_at: "2026-05-13T00:00:00Z",
        documents_count: 54,
        voice_presets_count: 1,
        jobs_count: 3,
        storage_bytes: 2147483648,
      },
      {
        id: 2,
        username: "bob",
        display_name: "Bob",
        role: "member",
        status: "active",
        last_login_at: null,
        created_at: "2026-06-01T00:00:00Z",
        documents_count: 2,
        voice_presets_count: 0,
        jobs_count: 0,
        storage_bytes: 1048576,
      },
    ];

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/auth/users" && !init) {
        return Promise.resolve({ ok: true, status: 200, json: async () => users });
      }

      if (typeof input === "string" && input === "/api/auth/users/2" && init?.method === "PATCH") {
        const payload = JSON.parse(String(init.body ?? "{}")) as { role?: string; status?: string };
        users = users.map((user) =>
          user.id === 2
            ? { ...user, role: payload.role ?? user.role, status: payload.status ?? user.status }
            : user,
        );
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => users.find((user) => user.id === 2),
        });
      }

      if (typeof input === "string" && input === "/api/auth/users/2/reset-password" && init?.method === "POST") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            user: users.find((user) => user.id === 2),
            temporary_password: "ocr-temp-password-123",
          }),
        });
      }

      if (typeof input === "string" && input === "/api/auth/invites" && !init) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [] });
      }

      return Promise.resolve({ ok: true, status: 200, json: async () => [] });
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
    vi.unstubAllGlobals();
  });

  it("lists accounts with usage stats and protects the signed-in admin row", async () => {
    window.history.pushState({}, "", "/admin");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "User management" })).toBeInTheDocument();
    expect(await screen.findByText(/Local host \(you\)/)).toBeInTheDocument();
    expect(screen.getByText(/54 books • 1 voice presets • 3 export jobs • 2\.0 GB on disk/)).toBeInTheDocument();
    expect(screen.getByText(/2 books • 0 voice presets • 0 export jobs • 1\.0 MB on disk/)).toBeInTheDocument();
    expect(screen.getByLabelText("Role for local-host")).toBeDisabled();
    expect(screen.getByLabelText("Role for bob")).toBeEnabled();
  });

  it("changes a member's role through the role select", async () => {
    window.history.pushState({}, "", "/admin");

    render(<App />);

    expect(await screen.findByLabelText("Role for bob")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Role for bob"), { target: { value: "admin" } });

    await waitFor(() => {
      const patchCall = fetchMock.mock.calls.find(
        ([input, init]) => input === "/api/auth/users/2" && (init as RequestInit | undefined)?.method === "PATCH",
      );
      expect(patchCall).toBeDefined();
      expect(JSON.parse(String((patchCall?.[1] as RequestInit | undefined)?.body ?? "{}"))).toEqual({
        role: "admin",
      });
    });
    expect(await screen.findByText("Bob is now a admin.")).toBeInTheDocument();
  });

  it("resets a member's password and shows the one-time temporary password", async () => {
    window.history.pushState({}, "", "/admin");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "User management" })).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Reset password" })[1]);

    expect(await screen.findByText(/ocr-temp-password-123/)).toBeInTheDocument();
    expect(screen.getByText(/Temporary password for bob/)).toBeInTheDocument();
  });

  it("disables and re-labels a member account", async () => {
    window.history.pushState({}, "", "/admin");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "User management" })).toBeInTheDocument();

    const enabledDisableButtons = screen
      .getAllByRole("button", { name: "Disable" })
      .filter((button) => !(button as HTMLButtonElement).disabled);
    fireEvent.click(enabledDisableButtons[0]);

    expect(await screen.findByText("Bob is disabled and signed out everywhere.")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Enable" })).toBeInTheDocument();
  });
});
