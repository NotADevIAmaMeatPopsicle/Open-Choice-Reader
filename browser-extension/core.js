export const DEFAULT_HOST = "http://127.0.0.1:8000";
export const HOST_STORAGE_KEY = "open-choice-reader.hostUrl";
export const EXTENSION_AUTH_REQUIRED_PATH = "/login?reason=extension-auth-required";

export const CONTEXT_MENU_ITEMS = [
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
];

export function normalizeHostUrl(value) {
  const trimmed = String(value || "").trim();
  if (!trimmed) {
    return DEFAULT_HOST;
  }

  const withProtocol = /^[a-z]+:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;

  try {
    const parsed = new URL(withProtocol);
    return `${parsed.protocol}//${parsed.host}`;
  } catch {
    return withProtocol.endsWith("/") ? withProtocol.slice(0, -1) : withProtocol;
  }
}

export function normalizePlaybackSpeed(value, fallback = 1) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }

  const clamped = Math.max(0.5, Math.min(8, parsed));
  return Math.round(clamped * 20) / 20;
}

export function buildImportSelectionPayload({ selectedText, title, url }) {
  return {
    body: String(selectedText || "").trim(),
    source_url: String(url || "").trim(),
    title: `${title || "Imported selection"} (Selection)`,
  };
}

export function buildImportPagePayload(url) {
  return { url: String(url || "").trim() };
}

export function buildAppUrl(hostUrl, path = "/") {
  const normalizedHost = normalizeHostUrl(hostUrl);
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedHost}${normalizedPath}`;
}

export function buildHostPermissionPattern(hostUrl) {
  const parsed = new URL(normalizeHostUrl(hostUrl));
  return `${parsed.protocol}//${parsed.hostname}/*`;
}

function isSignedOutMessage(message) {
  return /must be signed in|sign in/i.test(message);
}

function buildSignInRequiredMessage(hostUrl, actionLabel) {
  const normalizedHost = normalizeHostUrl(hostUrl);
  return `Unable to ${actionLabel} at ${normalizedHost}. Sign in to Open Choice Reader on this host first, then try the extension again.`;
}

export function isExtensionAuthRequiredError(error) {
  const message = error instanceof Error ? error.message : String(error || "");
  return /sign in to Open Choice Reader on this host first/i.test(message);
}

export function describeExtensionFailure(error, hostUrl, actionLabel) {
  const normalizedHost = normalizeHostUrl(hostUrl);
  const rawMessage = error instanceof Error ? error.message : String(error || "");
  const message = rawMessage.trim();

  if (isSignedOutMessage(message)) {
    return buildSignInRequiredMessage(hostUrl, actionLabel);
  }

  if (/failed to fetch|networkerror|load failed/i.test(message)) {
    return `Unable to ${actionLabel} at ${normalizedHost}. Check that the Open Choice Reader server is running and reachable from this browser.`;
  }

  if (!message) {
    return `Unable to ${actionLabel} at ${normalizedHost}.`;
  }

  return message;
}

export async function fetchJsonFromHost(fetchImpl, hostUrl, path, options = {}, actionLabel = "reach Open Choice Reader") {
  const requestUrl = buildAppUrl(hostUrl, path);
  const requestOptions = { ...options };
  if (!requestOptions.credentials) {
    requestOptions.credentials = "include";
  }
  let response;

  try {
    response = await fetchImpl(requestUrl, requestOptions);
  } catch (error) {
    throw new Error(describeExtensionFailure(error, hostUrl, actionLabel));
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = String(payload.detail || "").trim();
    if (response.status === 401 || response.status === 403 || isSignedOutMessage(detail)) {
      throw new Error(buildSignInRequiredMessage(hostUrl, actionLabel));
    }
    throw new Error(payload.detail || `Unable to ${actionLabel}. The server returned status ${response.status}.`);
  }

  return payload;
}
