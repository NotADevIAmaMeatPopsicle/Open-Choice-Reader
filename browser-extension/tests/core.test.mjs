import test from "node:test";
import assert from "node:assert/strict";

import {
  CONTEXT_MENU_ITEMS,
  DEFAULT_HOST,
  HOST_STORAGE_KEY,
  buildAppUrl,
  buildHostPermissionPattern,
  buildImportPagePayload,
  buildImportSelectionPayload,
  describeExtensionFailure,
  fetchJsonFromHost,
  normalizeHostUrl,
  normalizePlaybackSpeed,
} from "../core.js";

test("normalizeHostUrl trims whitespace and trailing slashes", () => {
  assert.equal(normalizeHostUrl(" http://reader.example.test:8000/ "), "http://reader.example.test:8000");
  assert.equal(normalizeHostUrl(" reader.example.test:8000 "), "http://reader.example.test:8000");
  assert.equal(normalizeHostUrl(""), DEFAULT_HOST);
});

test("buildAppUrl keeps the configured origin and normalizes leading slashes", () => {
  assert.equal(buildAppUrl("reader.example.test:8000", "/reader/12"), "http://reader.example.test:8000/reader/12");
  assert.equal(buildAppUrl(DEFAULT_HOST, "books/8"), `${DEFAULT_HOST}/books/8`);
});

test("buildHostPermissionPattern requests only the configured scheme and host", () => {
  assert.equal(buildHostPermissionPattern("https://reader.example.test:8443"), "https://reader.example.test/*");
});

test("normalizePlaybackSpeed clamps to supported range and rounds to 0.05x increments", () => {
  assert.equal(normalizePlaybackSpeed("1.53"), 1.55);
  assert.equal(normalizePlaybackSpeed("0.2"), 0.5);
  assert.equal(normalizePlaybackSpeed("3.1"), 3.1);
  assert.equal(normalizePlaybackSpeed("9.4"), 8);
  assert.equal(normalizePlaybackSpeed("not-a-number"), 1);
});

test("selection payload preserves source metadata and selected text", () => {
  assert.deepEqual(
    buildImportSelectionPayload({
      selectedText: "Read from here.",
      title: "Example article",
      url: "https://example.com/post",
    }),
    {
      body: "Read from here.",
      source_url: "https://example.com/post",
      title: "Example article (Selection)",
    },
  );
});

test("page payload contains only the original url", () => {
  assert.deepEqual(buildImportPagePayload("https://example.com/story"), { url: "https://example.com/story" });
});

test("context-menu definitions cover page and selection import/read actions", () => {
  assert.equal(HOST_STORAGE_KEY, "open-choice-reader.hostUrl");
  assert.deepEqual(
    CONTEXT_MENU_ITEMS.map(({ contexts, id, title }) => ({ contexts, id, title })),
    [
      {
        id: "read-page",
        title: "Read page in Open Choice Reader",
        contexts: ["page"],
      },
      {
        id: "import-page",
        title: "Import page to Open Choice Reader",
        contexts: ["page"],
      },
      {
        id: "read-selection",
        title: "Read selection in Open Choice Reader",
        contexts: ["selection"],
      },
      {
        id: "import-selection",
        title: "Import selection to Open Choice Reader",
        contexts: ["selection"],
      },
    ],
  );
});

test("describeExtensionFailure turns fetch/network errors into actionable server guidance", () => {
  const message = describeExtensionFailure(new TypeError("Failed to fetch"), DEFAULT_HOST, "import the full page");

  assert.match(message, /Unable to import the full page at http:\/\/127\.0\.0\.1:8000/);
  assert.match(message, /server is running and reachable/i);
});

test("fetchJsonFromHost preserves backend detail for non-network failures", async () => {
  await assert.rejects(
    () =>
      fetchJsonFromHost(
        async () => ({
          ok: false,
          status: 422,
          json: async () => ({ detail: "Page URL is not importable." }),
        }),
        DEFAULT_HOST,
        "/api/catalogs/import-url",
        { method: "POST" },
        "import the full page",
      ),
    /Page URL is not importable\./,
  );
});

test("fetchJsonFromHost includes browser credentials so server sessions can be reused", async () => {
  let capturedOptions = null;

  const payload = await fetchJsonFromHost(
    async (_requestUrl, options) => {
      capturedOptions = options;
      return {
        ok: true,
        status: 200,
        json: async () => ({ ok: true }),
      };
    },
    DEFAULT_HOST,
    "/api/auth/me",
    {},
    "load the signed-in account",
  );

  assert.deepEqual(payload, { ok: true });
  assert.equal(capturedOptions.credentials, "include");
});

test("fetchJsonFromHost turns signed-out auth failures into sign-in guidance", async () => {
  await assert.rejects(
    () =>
      fetchJsonFromHost(
        async () => ({
          ok: false,
          status: 401,
          json: async () => ({ detail: "You must be signed in." }),
        }),
        DEFAULT_HOST,
        "/api/catalogs/import-url",
        { method: "POST" },
        "import the full page",
      ),
    /sign in to Open Choice Reader on this host first/i,
  );
});
