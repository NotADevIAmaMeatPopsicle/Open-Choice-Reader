import {
  DEFAULT_HOST,
  EXTENSION_AUTH_REQUIRED_PATH,
  HOST_STORAGE_KEY,
  buildAppUrl,
  buildHostPermissionPattern,
  buildImportPagePayload,
  buildImportSelectionPayload,
  fetchJsonFromHost,
  isExtensionAuthRequiredError,
  normalizeHostUrl,
  normalizePlaybackSpeed,
} from "./core.js";

const elements = {
  hostInput: document.getElementById("host-url"),
  importPageButton: document.getElementById("import-page"),
  importSelectionButton: document.getElementById("import-selection"),
  openAppButton: document.getElementById("open-app"),
  pageTitle: document.getElementById("page-title"),
  pageUrl: document.getElementById("page-url"),
  playbackSpeedInput: document.getElementById("playback-speed"),
  readPageButton: document.getElementById("read-page"),
  readSelectionButton: document.getElementById("read-selection"),
  saveHostButton: document.getElementById("save-host"),
  selectionBadge: document.getElementById("selection-badge"),
  selectionPreview: document.getElementById("selection-preview"),
  statusMessage: document.getElementById("status-message"),
  voiceOptionSelect: document.getElementById("voice-option"),
};

const state = {
  activeTabId: null,
  hostUrl: DEFAULT_HOST,
  pageContext: {
    selectedText: "",
    title: "",
    url: "",
  },
  voiceOptions: [],
};

async function queryActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab ?? null;
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

async function loadHostPreference() {
  const stored = await chrome.storage.local.get(HOST_STORAGE_KEY);
  state.hostUrl = normalizeHostUrl(stored[HOST_STORAGE_KEY] || DEFAULT_HOST);
  if (stored[HOST_STORAGE_KEY] !== state.hostUrl) {
    await chrome.storage.local.set({ [HOST_STORAGE_KEY]: state.hostUrl });
  }
  elements.hostInput.value = state.hostUrl;
}

async function saveHostPreference() {
  state.hostUrl = normalizeHostUrl(elements.hostInput.value);
  const originPattern = buildHostPermissionPattern(state.hostUrl);
  const hasPermission = await chrome.permissions.contains({ origins: [originPattern] });
  if (!hasPermission) {
    const granted = await chrome.permissions.request({ origins: [originPattern] });
    if (!granted) {
      throw new Error(`Permission to connect to ${state.hostUrl} was not granted.`);
    }
  }
  await chrome.storage.local.set({ [HOST_STORAGE_KEY]: state.hostUrl });
  setStatus(`Saved reader server: ${state.hostUrl}`);
}

function setBusy(isBusy) {
  [
    elements.importPageButton,
    elements.importSelectionButton,
    elements.openAppButton,
    elements.readPageButton,
    elements.readSelectionButton,
    elements.saveHostButton,
  ].forEach((element) => {
    element.disabled = isBusy;
  });
}

function setStatus(message) {
  elements.statusMessage.textContent = message;
}

function getSelectedVoiceId() {
  return elements.voiceOptionSelect.value || null;
}

function getPlaybackSpeed() {
  return normalizePlaybackSpeed(elements.playbackSpeedInput.value);
}

function updatePageContextUi() {
  const { selectedText, title, url } = state.pageContext;
  const hasSelection = selectedText.length > 0;

  elements.pageTitle.textContent = title || "No readable page selected";
  elements.pageUrl.textContent = url || "Open a normal webpage tab to use the extension.";
  elements.selectionBadge.textContent = hasSelection ? "Selection ready" : "No selection";
  elements.selectionBadge.classList.toggle("badge--muted", !hasSelection);
  elements.selectionPreview.textContent = hasSelection
    ? selectedText.length > 180
      ? `${selectedText.slice(0, 177)}...`
      : selectedText
    : "Highlight text on the page if you want to start from a specific sentence or paragraph.";

  elements.readSelectionButton.disabled = !hasSelection;
  elements.importSelectionButton.disabled = !hasSelection;
}

async function loadVoiceOptions() {
  try {
    const [voiceOptions, settings] = await Promise.all([
      fetchJsonFromHost(fetch, state.hostUrl, "/api/voices/options", {}, "load server voices"),
      fetchJsonFromHost(fetch, state.hostUrl, "/api/settings", {}, "load server settings"),
    ]);

    state.voiceOptions = voiceOptions.filter((voiceOption) => voiceOption.supports_live_reading);
    const defaultVoiceId = settings.default_live_voice_id || "";
    const defaultSpeed = settings.default_playback_speed || 1;

    elements.voiceOptionSelect.innerHTML = '<option value="">Use app default</option>';
    state.voiceOptions.forEach((voiceOption) => {
      const option = document.createElement("option");
      option.value = voiceOption.id;
      option.textContent = `${voiceOption.name} | ${voiceOption.mode_label}`;
      if (voiceOption.id === defaultVoiceId) {
        option.selected = true;
      }
      elements.voiceOptionSelect.appendChild(option);
    });

    elements.playbackSpeedInput.value = normalizePlaybackSpeed(defaultSpeed).toFixed(2);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to load server voices";
    if (isExtensionAuthRequiredError(error)) {
      setStatus(`${message} Click Open App to sign in first.`);
      return;
    }
    setStatus(message);
  }
}

async function importSelection() {
  const { selectedText, title, url } = state.pageContext;
  if (!selectedText) {
    throw new Error("Highlight text on the page first.");
  }

  return fetchJsonFromHost(fetch, state.hostUrl, "/api/catalogs/import-text", {
    body: JSON.stringify(buildImportSelectionPayload({ selectedText, title, url })),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  }, "import the selected text");
}

async function importPage() {
  const { url } = state.pageContext;
  if (!url) {
    throw new Error("Unable to read the current page URL.");
  }

  return fetchJsonFromHost(fetch, state.hostUrl, "/api/catalogs/import-url", {
    body: JSON.stringify(buildImportPagePayload(url)),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  }, "import the full page");
}

async function createPlaybackSession(documentId) {
  return fetchJsonFromHost(fetch, state.hostUrl, "/api/playback/sessions", {
    body: JSON.stringify({
      document_id: documentId,
      playback_speed: getPlaybackSpeed(),
      voice_option_id: getSelectedVoiceId(),
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  }, "start live reading");
}

async function openPath(path) {
  await chrome.tabs.create({ url: buildAppUrl(state.hostUrl, path) });
}

async function guideToLogin(error) {
  setStatus(error instanceof Error ? error.message : "Sign in to Open Choice Reader on this host first.");
  await openPath(EXTENSION_AUTH_REQUIRED_PATH);
}

async function openApp() {
  setBusy(true);
  setStatus(`Checking reader server ${state.hostUrl}...`);

  try {
    await fetchJsonFromHost(fetch, state.hostUrl, "/api/health", {}, "reach Open Choice Reader");
    await openPath("/");
    setStatus(`Opened Open Choice Reader at ${state.hostUrl}.`);
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Unable to open Open Choice Reader.");
  } finally {
    setBusy(false);
  }
}

async function handleImport(importer, modeLabel) {
  setBusy(true);
  setStatus(`Importing ${modeLabel}...`);

  try {
    const documentRecord = await importer();
    await openPath(`/books/${documentRecord.id}`);
    setStatus(`Imported "${documentRecord.title}".`);
  } catch (error) {
    if (isExtensionAuthRequiredError(error)) {
      await guideToLogin(error);
      return;
    }
    setStatus(error instanceof Error ? error.message : `Unable to import ${modeLabel}.`);
  } finally {
    setBusy(false);
  }
}

async function handleRead(importer, modeLabel) {
  setBusy(true);
  setStatus(`Preparing ${modeLabel}...`);

  try {
    const documentRecord = await importer();
    const session = await createPlaybackSession(documentRecord.id);
    await openPath(`/reader/${session.id}`);
    setStatus(`Opened "${documentRecord.title}" in the reader.`);
  } catch (error) {
    if (isExtensionAuthRequiredError(error)) {
      await guideToLogin(error);
      return;
    }
    setStatus(error instanceof Error ? error.message : `Unable to read ${modeLabel}.`);
  } finally {
    setBusy(false);
  }
}

async function initialize() {
  await loadHostPreference();

  const activeTab = await queryActiveTab();
  state.activeTabId = activeTab?.id ?? null;
  if (state.activeTabId == null) {
    updatePageContextUi();
    setStatus("Open a normal webpage tab, then reopen the extension.");
    return;
  }

  try {
    const pageContext = await capturePageContext(state.activeTabId);
    if (!pageContext) {
      throw new Error("Unable to capture the current page.");
    }

    state.pageContext = pageContext;
    updatePageContextUi();
    await loadVoiceOptions();
  } catch (error) {
    updatePageContextUi();
    setStatus(error instanceof Error ? error.message : "Unable to capture the current page.");
  }
}

elements.saveHostButton.addEventListener("click", () => {
  void saveHostPreference().catch((error) => {
    setStatus(error instanceof Error ? error.message : "Unable to save the reader server.");
  });
});

elements.openAppButton.addEventListener("click", () => {
  void openApp();
});

elements.readPageButton.addEventListener("click", () => {
  void handleRead(importPage, "the full page");
});

elements.readSelectionButton.addEventListener("click", () => {
  void handleRead(importSelection, "the selected text");
});

elements.importPageButton.addEventListener("click", () => {
  void handleImport(importPage, "the full page");
});

elements.importSelectionButton.addEventListener("click", () => {
  void handleImport(importSelection, "the selected text");
});

void initialize();
