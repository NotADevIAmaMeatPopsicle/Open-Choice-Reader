import type {
  AdminPasswordResetRecord,
  AdminSessionsRevokedRecord,
  AdminUserRecord,
  AdminUserUpdatePayload,
  AuthSessionRecord,
  AuthUserRecord,
  BootstrapAdminPayload,
  BootstrapStatusRecord,
  DirectoryEntryRecord,
  FriendsOverviewRecord,
  FriendsSummaryRecord,
  CatalogImportPayload,
  CatalogResultRecord,
  CatalogSourceRecord,
  ChangePasswordPayload,
  CloneSampleImportPayload,
  CloneSampleSearchRecord,
  ClaimInvitePayload,
  CollectionCreatePayload,
  CollectionRecord,
  CreateInvitePayload,
  DocumentDetailRecord,
  DocumentRecord,
  DocumentSummaryRecord,
  EngineStatusRecord,
  ExportJobCreate,
  InboxCandidateRecord,
  InviteCreateRecord,
  IssueSummaryRecord,
  JobRecord,
  KavitaThemeImportRecord,
  LoginPayload,
  PlaybackPrebufferRecord,
  PlaybackSessionCreatePayload,
  PlaybackSessionRecord,
  PlaybackSessionUpdatePayload,
  ShareCreatePayload,
  SharesOverviewRecord,
  ThemeProfileRecord,
  VoiceOptionRecord,
  VoicePresetRecord,
  VoiceSettingsRecord,
  VoiceSettingsUpdate,
  PastedTextImportPayload,
  UserInviteRecord,
  VoiceTranscriptionRecord,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  if (!API_BASE_URL) {
    return init === undefined ? fetch(input) : fetch(input, init);
  }

  return fetch(input, {
    credentials: "include",
    ...init,
  });
}

async function readJson<T>(response: Response): Promise<T> {
  let payload: T | { detail?: string };

  try {
    payload = (await response.json()) as T | { detail?: string };
  } catch {
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    throw new Error("Response payload was not valid JSON");
  }

  if (!response.ok) {
    if (typeof payload === "object" && payload && "detail" in payload && typeof payload.detail === "string") {
      throw new Error(payload.detail);
    }

    throw new Error(`Request failed with status ${response.status}`);
  }

  return payload as T;
}

export async function getBootstrapStatus(): Promise<BootstrapStatusRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/bootstrap-status`);
  return readJson<BootstrapStatusRecord>(response);
}

export async function getCurrentUser(): Promise<AuthUserRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/me`);
  return readJson<AuthUserRecord>(response);
}

export async function bootstrapAdmin(payload: BootstrapAdminPayload): Promise<AuthSessionRecord> {
  const { bootstrap_token: bootstrapToken, ...account } = payload;
  const response = await apiFetch(`${API_BASE_URL}/api/auth/bootstrap-admin`, {
    body: JSON.stringify(account),
    headers: {
      "Content-Type": "application/json",
      ...(bootstrapToken ? { "X-Bootstrap-Token": bootstrapToken } : {}),
    },
    method: "POST",
  });
  return readJson<AuthSessionRecord>(response);
}

export async function login(payload: LoginPayload): Promise<AuthSessionRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/login`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });
  return readJson<AuthSessionRecord>(response);
}

export async function logout(): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/logout`, {
    method: "POST",
  });
  if (!response.ok) {
    await readJson<Record<string, never>>(response);
  }
}

export async function claimInvite(payload: ClaimInvitePayload): Promise<AuthSessionRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/claim-invite`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });
  return readJson<AuthSessionRecord>(response);
}

export async function deleteDocument(documentId: number): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/api/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    await readJson<Record<string, never>>(response);
  }
}

export async function changePassword(payload: ChangePasswordPayload): Promise<AuthUserRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/change-password`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });
  return readJson<AuthUserRecord>(response);
}

export async function adminUpdateUser(userId: number, payload: AdminUserUpdatePayload): Promise<AdminUserRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/users/${userId}`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "PATCH",
  });
  return readJson<AdminUserRecord>(response);
}

export async function adminResetPassword(userId: number): Promise<AdminPasswordResetRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/users/${userId}/reset-password`, {
    method: "POST",
  });
  return readJson<AdminPasswordResetRecord>(response);
}

export async function adminRevokeSessions(userId: number): Promise<AdminSessionsRevokedRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/users/${userId}/revoke-sessions`, {
    method: "POST",
  });
  return readJson<AdminSessionsRevokedRecord>(response);
}

export async function getFriendsOverview(): Promise<FriendsOverviewRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/friends`);
  return readJson<FriendsOverviewRecord>(response);
}

export async function getFriendsDirectory(): Promise<DirectoryEntryRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/friends/directory`);
  return readJson<DirectoryEntryRecord[]>(response);
}

export async function getFriendsSummary(): Promise<FriendsSummaryRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/friends/summary`);
  return readJson<FriendsSummaryRecord>(response);
}

export async function sendFriendRequest(userId: number): Promise<FriendsOverviewRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/friends/requests`, {
    body: JSON.stringify({ user_id: userId }),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });
  return readJson<FriendsOverviewRecord>(response);
}

export async function acceptFriendRequest(friendshipId: number): Promise<FriendsOverviewRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/friends/requests/${friendshipId}/accept`, {
    method: "POST",
  });
  return readJson<FriendsOverviewRecord>(response);
}

export async function declineFriendRequest(friendshipId: number): Promise<FriendsOverviewRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/friends/requests/${friendshipId}/decline`, {
    method: "POST",
  });
  return readJson<FriendsOverviewRecord>(response);
}

export async function unfriendUser(userId: number): Promise<FriendsOverviewRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/friends/${userId}`, {
    method: "DELETE",
  });
  return readJson<FriendsOverviewRecord>(response);
}

export async function getSharesOverview(): Promise<SharesOverviewRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/shares`);
  return readJson<SharesOverviewRecord>(response);
}

export async function createShare(payload: ShareCreatePayload): Promise<SharesOverviewRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/shares`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });
  return readJson<SharesOverviewRecord>(response);
}

export async function acceptShare(shareId: number): Promise<SharesOverviewRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/shares/${shareId}/accept`, {
    method: "POST",
  });
  return readJson<SharesOverviewRecord>(response);
}

export async function declineShare(shareId: number): Promise<SharesOverviewRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/shares/${shareId}/decline`, {
    method: "POST",
  });
  return readJson<SharesOverviewRecord>(response);
}

export async function listUsers(): Promise<AdminUserRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/users`);
  return readJson<AdminUserRecord[]>(response);
}

export async function listInvites(): Promise<UserInviteRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/invites`);
  return readJson<UserInviteRecord[]>(response);
}

export async function createInvite(payload: CreateInvitePayload): Promise<InviteCreateRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/invites`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });
  return readJson<InviteCreateRecord>(response);
}

export async function revokeInvite(inviteId: number): Promise<UserInviteRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/auth/invites/${inviteId}/revoke`, {
    method: "POST",
  });
  return readJson<UserInviteRecord>(response);
}

export async function listDocuments(): Promise<DocumentRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/documents`);
  return readJson<DocumentRecord[]>(response);
}

export async function getDocumentSummary(): Promise<DocumentSummaryRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/documents/summary`);
  return readJson<DocumentSummaryRecord>(response);
}

export async function getDocumentDetail(documentId: number): Promise<DocumentDetailRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/documents/${documentId}`);
  return readJson<DocumentDetailRecord>(response);
}

export async function listThemes(): Promise<ThemeProfileRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/themes`);
  return readJson<ThemeProfileRecord[]>(response);
}

export async function importKavitaTheme(payload: {
  cssFile?: File | null;
  cssText?: string;
  name?: string;
}): Promise<KavitaThemeImportRecord> {
  const formData = new FormData();
  if (payload.name?.trim()) {
    formData.append("name", payload.name.trim());
  }
  if (payload.cssText?.trim()) {
    formData.append("css_text", payload.cssText.trim());
  }
  if (payload.cssFile) {
    formData.append("css_file", payload.cssFile);
  }

  const response = await apiFetch(`${API_BASE_URL}/api/themes/import/kavita`, {
    body: formData,
    method: "POST",
  });
  return readJson<KavitaThemeImportRecord>(response);
}

export async function deleteTheme(themeId: string): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/api/themes/${themeId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    await readJson<Record<string, never>>(response);
  }
}

export async function importDocument(file: File): Promise<DocumentRecord> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch(`${API_BASE_URL}/api/documents/import`, {
    body: formData,
    method: "POST",
  });

  return readJson<DocumentRecord>(response);
}

export async function listCatalogSources(): Promise<CatalogSourceRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/catalogs/sources`);
  return readJson<CatalogSourceRecord[]>(response);
}

export async function browseGutenberg(limit = 12): Promise<CatalogResultRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/catalogs/gutenberg/top?limit=${limit}`);
  return readJson<CatalogResultRecord[]>(response);
}

export async function searchGutenberg(query: string, limit = 12): Promise<CatalogResultRecord[]> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/catalogs/gutenberg/search?q=${encodeURIComponent(query)}&limit=${limit}`,
  );
  return readJson<CatalogResultRecord[]>(response);
}

export async function browseStandardEbooks(limit = 12, sort = "new"): Promise<CatalogResultRecord[]> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/catalogs/standard-ebooks/browse?limit=${limit}&sort=${encodeURIComponent(sort)}`,
  );
  return readJson<CatalogResultRecord[]>(response);
}

export async function searchStandardEbooks(query: string, limit = 12): Promise<CatalogResultRecord[]> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/catalogs/standard-ebooks/search?q=${encodeURIComponent(query)}&limit=${limit}`,
  );
  return readJson<CatalogResultRecord[]>(response);
}

export async function searchOpenLibrary(query: string, limit = 12): Promise<CatalogResultRecord[]> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/catalogs/open-library/search?q=${encodeURIComponent(query)}&limit=${limit}`,
  );
  return readJson<CatalogResultRecord[]>(response);
}

export async function importCatalogItem(payload: CatalogImportPayload): Promise<DocumentRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/catalogs/import`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  return readJson<DocumentRecord>(response);
}

export async function importDocumentFromUrl(url: string): Promise<DocumentRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/catalogs/import-url`, {
    body: JSON.stringify({ url }),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  return readJson<DocumentRecord>(response);
}

export async function importPastedText(payload: PastedTextImportPayload): Promise<DocumentRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/catalogs/import-text`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  return readJson<DocumentRecord>(response);
}

export async function listInboxCandidates(): Promise<InboxCandidateRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/documents/inbox`);
  return readJson<InboxCandidateRecord[]>(response);
}

export async function importInboxCandidate(path: string): Promise<DocumentRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/documents/import-inbox`, {
    body: JSON.stringify({ path }),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  return readJson<DocumentRecord>(response);
}

export async function reimportDocument(documentId: number): Promise<DocumentRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/documents/${documentId}/reimport`, {
    method: "POST",
  });

  return readJson<DocumentRecord>(response);
}

export async function resetDocumentBookmark(documentId: number): Promise<DocumentRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/documents/${documentId}/bookmark/reset`, {
    method: "POST",
  });

  return readJson<DocumentRecord>(response);
}

export async function updateDocumentBookmark(documentId: number, enabled: boolean): Promise<DocumentRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/documents/${documentId}/bookmark`, {
    body: JSON.stringify({ enabled }),
    headers: {
      "Content-Type": "application/json",
    },
    method: "PATCH",
  });

  return readJson<DocumentRecord>(response);
}

export async function markDocumentFinished(documentId: number): Promise<DocumentRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/documents/${documentId}/finished`, {
    method: "POST",
  });

  return readJson<DocumentRecord>(response);
}

export async function clearDocumentFinished(documentId: number): Promise<DocumentRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/documents/${documentId}/finished`, {
    method: "DELETE",
  });

  return readJson<DocumentRecord>(response);
}

export async function listJobs(): Promise<JobRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/jobs`);
  return readJson<JobRecord[]>(response);
}

export async function createExportJob(payload: ExportJobCreate): Promise<JobRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/jobs/export`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  return readJson<JobRecord>(response);
}

export async function retryExportJob(jobId: number): Promise<JobRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/jobs/${jobId}/retry`, {
    method: "POST",
  });

  return readJson<JobRecord>(response);
}

export async function cancelExportJob(jobId: number): Promise<JobRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/jobs/${jobId}/cancel`, {
    method: "POST",
  });

  return readJson<JobRecord>(response);
}

export async function listVoicePresets(): Promise<VoicePresetRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/voices/presets`);
  return readJson<VoicePresetRecord[]>(response);
}

export async function listCollections(): Promise<CollectionRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/collections`);
  return readJson<CollectionRecord[]>(response);
}

export async function createCollection(payload: CollectionCreatePayload): Promise<CollectionRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/collections`, {
    body: JSON.stringify({
      name: payload.name,
      description: payload.description ?? "",
    }),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  return readJson<CollectionRecord>(response);
}

export async function addDocumentToCollection(collectionId: number, documentId: number): Promise<CollectionRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/collections/${collectionId}/documents`, {
    body: JSON.stringify({ document_id: documentId }),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  return readJson<CollectionRecord>(response);
}

export async function removeDocumentFromCollection(collectionId: number, documentId: number): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/api/collections/${collectionId}/documents/${documentId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    await readJson<Record<string, never>>(response);
  }
}

export async function getIssueSummary(): Promise<IssueSummaryRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/issues`);
  return readJson<IssueSummaryRecord>(response);
}

export async function listVoiceOptions(): Promise<VoiceOptionRecord[]> {
  const response = await apiFetch(`${API_BASE_URL}/api/voices/options`);
  return readJson<VoiceOptionRecord[]>(response);
}

export async function fetchVoicePreviewAudio(voiceOptionId: string): Promise<Blob> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/voices/preview?voice_option_id=${encodeURIComponent(voiceOptionId)}`,
  );

  if (!response.ok) {
    await readJson<Record<string, never>>(response);
  }

  return response.blob();
}

export async function transcribeReferenceAudio(referenceAudio: File): Promise<VoiceTranscriptionRecord> {
  const formData = new FormData();
  formData.append("reference_audio", referenceAudio);

  const response = await apiFetch(`${API_BASE_URL}/api/voices/transcribe-reference`, {
    body: formData,
    method: "POST",
  });

  return readJson<VoiceTranscriptionRecord>(response);
}

export async function searchCloneSamples(query: string, limit = 10): Promise<CloneSampleSearchRecord> {
  const response = await apiFetch(
    `${API_BASE_URL}/api/clone-samples/search?q=${encodeURIComponent(query)}&limit=${limit}`,
  );
  return readJson<CloneSampleSearchRecord>(response);
}

export async function importCloneSample(payload: CloneSampleImportPayload): Promise<VoicePresetRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/clone-samples/import`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  return readJson<VoicePresetRecord>(response);
}

export async function createVoicePreset(
  name: string,
  transcript: string,
  referenceAudio: File,
): Promise<VoicePresetRecord> {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("transcript", transcript);
  formData.append("reference_audio", referenceAudio);

  const response = await apiFetch(`${API_BASE_URL}/api/voices/presets`, {
    body: formData,
    method: "POST",
  });

  return readJson<VoicePresetRecord>(response);
}

export async function getVoiceSettings(): Promise<VoiceSettingsRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/settings`);
  return readJson<VoiceSettingsRecord>(response);
}

export async function updateVoiceSettings(payload: VoiceSettingsUpdate): Promise<VoiceSettingsRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/settings`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "PUT",
  });

  return readJson<VoiceSettingsRecord>(response);
}

export async function getPlaybackSession(sessionId: string): Promise<PlaybackSessionRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/playback/sessions/${sessionId}`);
  return readJson<PlaybackSessionRecord>(response);
}

export async function prebufferPlaybackSession(sessionId: string): Promise<PlaybackPrebufferRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/playback/sessions/${sessionId}/prebuffer`, {
    method: "POST",
  });
  return readJson<PlaybackPrebufferRecord>(response);
}

export async function createPlaybackSession(
  payload: PlaybackSessionCreatePayload,
): Promise<PlaybackSessionRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/playback/sessions`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  return readJson<PlaybackSessionRecord>(response);
}

export async function updatePlaybackSessionProgress(
  sessionId: string,
  currentChunkIndex: number,
): Promise<PlaybackSessionRecord> {
  return updatePlaybackSession(sessionId, { current_chunk_index: currentChunkIndex });
}

export async function updatePlaybackSession(
  sessionId: string,
  payload: PlaybackSessionUpdatePayload,
): Promise<PlaybackSessionRecord> {
  const response = await apiFetch(`${API_BASE_URL}/api/playback/sessions/${sessionId}`, {
    body: JSON.stringify(payload),
    headers: {
      "Content-Type": "application/json",
    },
    method: "PATCH",
  });

  return readJson<PlaybackSessionRecord>(response);
}
