import {
  CONTEXT_MENU_ITEMS,
  DEFAULT_HOST,
  EXTENSION_AUTH_REQUIRED_PATH,
  HOST_STORAGE_KEY,
  buildAppUrl,
  buildImportPagePayload,
  buildImportSelectionPayload,
  fetchJsonFromHost,
  isExtensionAuthRequiredError,
  normalizeHostUrl,
} from "./core.js";

async function getHostUrl() {
  const stored = await chrome.storage.local.get(HOST_STORAGE_KEY);
  const hostUrl = normalizeHostUrl(stored[HOST_STORAGE_KEY] || DEFAULT_HOST);
  if (stored[HOST_STORAGE_KEY] !== hostUrl) {
    await chrome.storage.local.set({ [HOST_STORAGE_KEY]: hostUrl });
  }
  return hostUrl;
}

function createContextMenus() {
  chrome.contextMenus.removeAll(() => {
    CONTEXT_MENU_ITEMS.forEach((item) => chrome.contextMenus.create(item));
  });
}

async function capturePageContext(tabId) {
  const [result] = await chrome.scripting.executeScript({
    func: () => ({
      selectedText: window.getSelection ? String(window.getSelection()).trim() : "",
      title: document.title || "Untitled page",
      url: window.location.href,
    }),
    target: { tabId },
  });

  return result?.result ?? null;
}

async function importSelection(hostUrl, info, tab) {
  const pageContext =
    tab?.id != null
      ? await capturePageContext(tab.id)
      : {
          selectedText: String(info.selectionText || "").trim(),
          title: tab?.title || "Imported selection",
          url: tab?.url || "",
        };

  const selectedText = String(pageContext?.selectedText || info.selectionText || "").trim();
  if (!selectedText) {
    throw new Error("Select text on the page first.");
  }

  return fetchJsonFromHost(fetch, hostUrl, "/api/catalogs/import-text", {
    body: JSON.stringify(
      buildImportSelectionPayload({
        selectedText,
        title: pageContext?.title || tab?.title || "Imported selection",
        url: pageContext?.url || tab?.url || "",
      }),
    ),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  }, "import the selected text");
}

async function importPage(hostUrl, tab) {
  const url = String(tab?.url || "").trim();
  if (!url) {
    throw new Error("Open a normal webpage tab first.");
  }

  return fetchJsonFromHost(fetch, hostUrl, "/api/catalogs/import-url", {
    body: JSON.stringify(buildImportPagePayload(url)),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  }, "import the full page");
}

async function createPlaybackSession(hostUrl, documentId) {
  return fetchJsonFromHost(fetch, hostUrl, "/api/playback/sessions", {
    body: JSON.stringify({ document_id: documentId }),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  }, "start live reading");
}

async function openPath(hostUrl, path) {
  await chrome.tabs.create({ url: buildAppUrl(hostUrl, path) });
}

async function handleMenuClick(info, tab) {
  const hostUrl = await getHostUrl();
  const menuId = String(info.menuItemId || "");

  try {
    if (menuId === "read-page") {
      const documentRecord = await importPage(hostUrl, tab);
      const session = await createPlaybackSession(hostUrl, documentRecord.id);
      await openPath(hostUrl, `/reader/${session.id}`);
      return;
    }

    if (menuId === "import-page") {
      const documentRecord = await importPage(hostUrl, tab);
      await openPath(hostUrl, `/books/${documentRecord.id}`);
      return;
    }

    if (menuId === "read-selection") {
      const documentRecord = await importSelection(hostUrl, info, tab);
      const session = await createPlaybackSession(hostUrl, documentRecord.id);
      await openPath(hostUrl, `/reader/${session.id}`);
      return;
    }

    if (menuId === "import-selection") {
      const documentRecord = await importSelection(hostUrl, info, tab);
      await openPath(hostUrl, `/books/${documentRecord.id}`);
    }
  } catch (error) {
    console.error("Open Choice Reader extension handoff failed", error);
    if (isExtensionAuthRequiredError(error)) {
      await openPath(hostUrl, EXTENSION_AUTH_REQUIRED_PATH);
    }
  }
}

chrome.runtime.onInstalled.addListener(createContextMenus);
chrome.runtime.onStartup.addListener(createContextMenus);
chrome.contextMenus.onClicked.addListener((info, tab) => {
  void handleMenuClick(info, tab);
});
