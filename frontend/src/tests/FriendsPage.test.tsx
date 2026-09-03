import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import type { DirectoryEntryRecord, FriendsOverviewRecord, SharesOverviewRecord } from "../api/types";
import { withAuthenticatedAppFetch } from "./support/authSessionFetch";

describe("FriendsPage", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    let friendsOverview: FriendsOverviewRecord = {
      friends: [
        {
          friendship_id: 7,
          user: { id: 2, username: "alice", display_name: "Alice" },
          since: "2026-06-01T00:00:00Z",
        },
      ],
      incoming_requests: [
        {
          friendship_id: 9,
          direction: "incoming",
          user: { id: 3, username: "casey", display_name: "Casey Reader" },
          created_at: "2026-06-10T00:00:00Z",
        },
      ],
      outgoing_requests: [],
    };
    let sharesOverview: SharesOverviewRecord = {
      incoming: [
        {
          id: 12,
          direction: "incoming",
          other_user: { id: 2, username: "alice", display_name: "Alice" },
          item_type: "document",
          item_label: "Frankenstein",
          message: "You will love this one.",
          status: "pending",
          accepted_item_id: null,
          created_at: "2026-06-11T00:00:00Z",
          responded_at: null,
        },
      ],
      outgoing: [],
    };
    const directory: DirectoryEntryRecord[] = [
      { user: { id: 2, username: "alice", display_name: "Alice" }, state: "friends", friendship_id: 7 },
      { user: { id: 3, username: "casey", display_name: "Casey Reader" }, state: "pending_incoming", friendship_id: 9 },
      { user: { id: 4, username: "lily", display_name: "Lily Reader" }, state: "none", friendship_id: null },
    ];

    fetchMock = withAuthenticatedAppFetch((input: RequestInfo | URL, init?: RequestInit) => {
      if (typeof input === "string" && input === "/api/friends" && !init) {
        return Promise.resolve({ ok: true, status: 200, json: async () => friendsOverview });
      }

      if (typeof input === "string" && input === "/api/shares" && !init) {
        return Promise.resolve({ ok: true, status: 200, json: async () => sharesOverview });
      }

      if (typeof input === "string" && input === "/api/friends/directory" && !init) {
        return Promise.resolve({ ok: true, status: 200, json: async () => directory });
      }

      if (typeof input === "string" && input === "/api/shares/12/accept" && init?.method === "POST") {
        sharesOverview = {
          incoming: [
            {
              ...sharesOverview.incoming[0],
              status: "accepted",
              accepted_item_id: 41,
              responded_at: "2026-06-12T00:00:00Z",
            },
          ],
          outgoing: [],
        };
        return Promise.resolve({ ok: true, status: 200, json: async () => sharesOverview });
      }

      if (typeof input === "string" && input === "/api/friends/requests" && init?.method === "POST") {
        friendsOverview = {
          ...friendsOverview,
          outgoing_requests: [
            {
              friendship_id: 15,
              direction: "outgoing",
              user: { id: 4, username: "lily", display_name: "Lily Reader" },
              created_at: "2026-06-12T00:00:00Z",
            },
          ],
        };
        return Promise.resolve({ ok: true, status: 201, json: async () => friendsOverview });
      }

      return Promise.resolve({ ok: true, status: 200, json: async () => [] });
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    window.history.pushState({}, "", "/");
    vi.unstubAllGlobals();
  });

  it("renders the share inbox, requests, friends, and directory", async () => {
    window.history.pushState({}, "", "/friends");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Friends and sharing" })).toBeInTheDocument();
    expect(await screen.findByText("Frankenstein")).toBeInTheDocument();
    expect(screen.getByText(/You will love this one/)).toBeInTheDocument();
    expect(screen.getByText("Casey Reader wants to be friends")).toBeInTheDocument();
    expect(screen.getAllByText(/Alice \(alice\)/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Add friend" })).toBeInTheDocument();
  });

  it("accepts an incoming share and reports the new copy", async () => {
    window.history.pushState({}, "", "/friends");

    render(<App />);

    expect(await screen.findByText("Frankenstein")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Accept" })[0]);

    await waitFor(() => {
      expect(fetchMock.mock.calls.some(([input]) => input === "/api/shares/12/accept")).toBe(true);
    });
    expect(await screen.findByText("Added Frankenstein to your library.")).toBeInTheDocument();
  });

  it("sends a friend request from the directory", async () => {
    window.history.pushState({}, "", "/friends");

    render(<App />);

    expect(await screen.findByRole("button", { name: "Add friend" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Add friend" }));

    await waitFor(() => {
      const requestCall = fetchMock.mock.calls.find(
        ([input, init]) => input === "/api/friends/requests" && (init as RequestInit | undefined)?.method === "POST",
      );
      expect(requestCall).toBeDefined();
      expect(JSON.parse(String((requestCall?.[1] as RequestInit | undefined)?.body ?? "{}"))).toEqual({
        user_id: 4,
      });
    });
    expect(await screen.findByText("Friend request sent.")).toBeInTheDocument();
  });
});
