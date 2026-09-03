import { vi } from "vitest";

type MockJsonResponse = {
  blob?: () => Promise<Blob>;
  json?: () => Promise<unknown>;
  ok: boolean;
  status?: number;
};

const AUTHENTICATED_TEST_USER = {
  id: 1,
  username: "local-host",
  display_name: "Local host",
  role: "admin",
  status: "active",
  last_login_at: null,
};

export function withAuthenticatedAppFetch(
  handler: (input: RequestInfo | URL, init?: RequestInit) => Promise<MockJsonResponse>,
) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    if (typeof input === "string" && input === "/api/auth/bootstrap-status" && init === undefined) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          bootstrap_available: false,
        }),
      } satisfies MockJsonResponse);
    }

    if (typeof input === "string" && input === "/api/auth/me" && init === undefined) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => AUTHENTICATED_TEST_USER,
      } satisfies MockJsonResponse);
    }

    return handler(input, init);
  });
}
