export type DocumentStatus = "imported" | "processing" | "ready" | "failed" | string;

export interface DocumentRecord {
  id: number;
  title: string;
  format: string;
  status: DocumentStatus;
  author?: string | null;
  cover_url?: string;
  summary?: string | null;
  total_sections?: number;
  total_chunks?: number;
  estimated_duration_seconds?: number;
  current_chunk_index?: number | null;
  progress_percent?: number;
  bookmark_enabled?: boolean;
  is_finished?: boolean;
  finished_at?: string | null;
  last_opened_at?: string | null;
  source_provider?: string | null;
  source_provider_name?: string | null;
  source_provider_url?: string | null;
  source_url?: string | null;
  source_site_name?: string | null;
  import_mode?: string | null;
}

export interface DocumentSectionRecord {
  id: number;
  position: number;
  title?: string | null;
  chunk_start_index: number;
  chunk_count: number;
  preview_text: string;
}

export interface DocumentDetailRecord extends DocumentRecord {
  sections: DocumentSectionRecord[];
}

export interface DocumentSummaryRecord {
  continue_reading: DocumentRecord[];
  recent_documents: DocumentRecord[];
}

export interface InboxCandidateRecord {
  name: string;
  path: string;
  format: string;
  document_id: number | null;
}

export interface PlaybackSessionCreatePayload {
  document_id: number;
  start_section_id?: number;
  voice_option_id?: string;
  playback_speed?: number;
}

export interface PlaybackSectionChunkRecord {
  chunk_index: number;
  text: string;
  is_current: boolean;
}

export interface PlaybackSessionRecord {
  id: number;
  document_id: number;
  document_title: string;
  document_author?: string | null;
  cover_url: string;
  current_chunk_index: number;
  total_chunks: number;
  audio_url: string;
  engine_name?: string;
  voice_option_id?: string | null;
  voice_model_name?: string | null;
  playback_speed: number;
  current_chunk_text: string;
  current_section_title?: string | null;
  section_chunks: PlaybackSectionChunkRecord[];
}

export interface PlaybackSessionUpdatePayload {
  current_chunk_index?: number;
  playback_speed?: number;
  voice_option_id?: string;
}

export interface PlaybackPrebufferRecord {
  session_id: number;
  target_chunk_index: number | null;
  status: string;
  audio_url?: string | null;
  detail?: string | null;
}

export interface JobRecord {
  id: number;
  document_id: number;
  voice_preset_id: string;
  clone_engine_id?: string | null;
  format: string;
  status: string;
  split_chapters?: boolean;
  artifact_basename?: string;
  progress_percent?: number;
  status_detail?: string | null;
  download_url: string | null;
  failure_detail: string | null;
  artifacts?: JobArtifactRecord[];
  can_retry?: boolean;
  can_cancel?: boolean;
}

export interface ExportJobCreate {
  document_id: number;
  voice_preset_id: string;
  clone_engine_id?: string;
  format: "wav";
  split_chapters?: boolean;
  artifact_basename?: string;
}

export interface JobArtifactRecord {
  artifact_id: string;
  filename: string;
  label: string;
  section_title?: string | null;
  download_url: string;
}

export interface VoicePresetRecord {
  id: number;
  name: string;
  engine: string;
  transcript: string | null;
  source_provider?: string | null;
  source_url?: string | null;
  transcript_source_url?: string | null;
  license_label?: string | null;
  provenance_note?: string | null;
}

export interface VoiceTranscriptionSegmentRecord {
  start: number;
  end: number;
  text: string;
}

export interface VoiceTranscriptionRecord {
  transcript: string;
  language?: string | null;
  engine: string;
  segments: VoiceTranscriptionSegmentRecord[];
}

export interface CloneSampleCandidateRecord {
  id: string;
  provider: string;
  title: string;
  speaker?: string | null;
  audio_url: string;
  transcript?: string | null;
  transcript_source_url: string;
  source_url: string;
  license_label: string;
  provenance_note: string;
  is_importable: boolean;
}

export interface CloneSampleSearchRecord {
  query: string;
  items: CloneSampleCandidateRecord[];
}

export interface CloneSampleImportPayload {
  provider: string;
  title: string;
  speaker?: string | null;
  audio_url: string;
  transcript: string;
  transcript_source_url: string;
  source_url: string;
  license_label: string;
  provenance_note: string;
}

export interface CollectionDocumentRecord {
  id: number;
  title: string;
  author: string | null;
  cover_url: string;
  progress_percent: number;
}

export interface CollectionRecord {
  id: number;
  name: string;
  description: string | null;
  document_count: number;
  documents: CollectionDocumentRecord[];
}

export interface CollectionCreatePayload {
  name: string;
  description?: string;
}

export interface IssueRecord {
  id: string;
  issue_type: string;
  severity: string;
  title: string;
  detail: string;
  action_label: string;
  action_path: string;
  document_id: number | null;
}

export interface IssueSummaryRecord {
  total_count: number;
  counts_by_severity: Record<string, number>;
  items: IssueRecord[];
}

export interface VoiceOptionRecord {
  id: string;
  name: string;
  voice_type: string;
  engine: string;
  mode_label: string;
  description: string;
  availability: string;
  availability_detail: string;
  supports_live_reading: boolean;
  supports_export: boolean;
  transcript_preview: string | null;
  engine_family?: string;
  model_name?: string | null;
}

export interface EngineStatusRecord {
  engine: string;
  display_name: string;
  availability: string;
  availability_detail: string;
  supports_live_reading: boolean;
  supports_export: boolean;
  engine_family?: string;
  model_name?: string | null;
  voice_count?: number;
}

export interface HostRuntimeRecord {
  host_name: string;
  runtime_label: string;
  gpu_name: string | null;
  execution_summary: string;
}

export interface CloneRuntimeRecord {
  engine: string;
  model_name: string;
  preset_count: number;
  availability: string;
  availability_detail: string;
  usage_summary: string;
  execution_summary: string;
  available_models: CloneRuntimeModelRecord[];
}

export interface CloneRuntimeModelRecord {
  engine: string;
  display_name: string;
  model_name: string;
  availability: string;
  availability_detail: string;
}

export interface ThemeProfileRecord {
  id: string;
  name: string;
  description: string | null;
  source_kind: string;
  source_label: string;
  source_reference: string | null;
  is_builtin: boolean;
  sort_order: number;
  family: string;
  preview_variant: string;
  background_asset_path?: string | null;
  background_overlay_path?: string | null;
  shelf_asset_path?: string | null;
  surface_texture_asset_path?: string | null;
  supports_mix_and_match: boolean;
  tokens: Record<string, string>;
}

export interface ThemeImportMappingRecord {
  source_variable: string;
  target_token: string;
  value: string;
}

export interface ThemeImportFallbackRecord {
  target_token: string;
  source_variable?: string | null;
  value: string;
  reason: string;
}

export interface KavitaThemeImportReportRecord {
  detected_variable_count: number;
  mapped_variables: ThemeImportMappingRecord[];
  ignored_variables: string[];
  fallback_tokens: ThemeImportFallbackRecord[];
}

export interface KavitaThemeImportRecord {
  theme: ThemeProfileRecord;
  report: KavitaThemeImportReportRecord;
}

export interface VoiceSettingsRecord {
  active_theme_id: string;
  active_theme: ThemeProfileRecord;
  default_live_voice_id: string;
  default_export_voice_id: string;
  fallback_voice_id: string | null;
  selected_clone_model_engine: string;
  engine_statuses: EngineStatusRecord[];
  host_runtime: HostRuntimeRecord;
  clone_runtime: CloneRuntimeRecord;
  ui_theme: string;
  sidebar_width_px: number;
  sidebar_mode: string;
  dock_position: string;
  tooltips_enabled: boolean;
  default_playback_speed: number;
  live_narration_pace: number;
  auto_pause_on_interrupt: boolean;
  library_view_mode: string;
  background_override_theme_id?: string | null;
  shelf_override_theme_id?: string | null;
}

export interface VoiceSettingsUpdate {
  active_theme_id?: string;
  default_live_voice_id: string;
  default_export_voice_id: string;
  fallback_voice_id: string | null;
  selected_clone_model_engine: string;
  ui_theme?: string;
  sidebar_width_px?: number;
  sidebar_mode?: string;
  dock_position?: string;
  tooltips_enabled?: boolean;
  default_playback_speed?: number;
  live_narration_pace?: number;
  auto_pause_on_interrupt?: boolean;
  library_view_mode?: string;
  background_override_theme_id?: string | null;
  shelf_override_theme_id?: string | null;
}

export interface CatalogSourceRecord {
  id: string;
  name: string;
  description: string;
  supports_search: boolean;
  supports_browse: boolean;
}

export interface CatalogResultRecord {
  id: string;
  source: string;
  source_name: string;
  title: string;
  author: string | null;
  summary: string | null;
  cover_url: string | null;
  detail_url: string;
  download_format: string | null;
  language: string | null;
  importable: boolean;
}

export interface CatalogImportPayload {
  source: string;
  catalog_id: string;
}

export interface PastedTextImportPayload {
  title: string;
  body: string;
  author?: string;
  source_url?: string;
}

export interface AuthUserRecord {
  id: number;
  username: string;
  display_name: string;
  role: string;
  status: string;
  last_login_at?: string | null;
}

export interface AuthSessionRecord {
  user: AuthUserRecord;
}

export interface AdminUserRecord extends AuthUserRecord {
  created_at?: string | null;
  documents_count: number;
  voice_presets_count: number;
  jobs_count: number;
  storage_bytes: number;
}

export interface AdminUserUpdatePayload {
  role?: string;
  status?: string;
}

export interface AdminPasswordResetRecord {
  user: AuthUserRecord;
  temporary_password: string;
}

export interface AdminSessionsRevokedRecord {
  user: AuthUserRecord;
  revoked_sessions: number;
}

export interface FriendUserRecord {
  id: number;
  username: string;
  display_name: string;
}

export interface FriendRecord {
  friendship_id: number;
  user: FriendUserRecord;
  since?: string | null;
}

export interface FriendRequestRecord {
  friendship_id: number;
  direction: "incoming" | "outgoing";
  user: FriendUserRecord;
  created_at: string;
}

export interface FriendsOverviewRecord {
  friends: FriendRecord[];
  incoming_requests: FriendRequestRecord[];
  outgoing_requests: FriendRequestRecord[];
}

export interface DirectoryEntryRecord {
  user: FriendUserRecord;
  state: "none" | "friends" | "pending_incoming" | "pending_outgoing";
  friendship_id?: number | null;
}

export interface FriendsSummaryRecord {
  pending_friend_requests: number;
  pending_shares: number;
}

export interface SharedItemRecord {
  id: number;
  direction: "incoming" | "outgoing";
  other_user: FriendUserRecord;
  item_type: "document" | "voice_preset";
  item_label: string;
  message?: string | null;
  status: "pending" | "accepted" | "declined";
  accepted_item_id?: number | null;
  created_at: string;
  responded_at?: string | null;
}

export interface SharesOverviewRecord {
  incoming: SharedItemRecord[];
  outgoing: SharedItemRecord[];
}

export interface ShareCreatePayload {
  recipient_user_id: number;
  item_type: "document" | "voice_preset";
  item_id: number;
  message?: string;
}

export interface BootstrapStatusRecord {
  bootstrap_available: boolean;
}

export interface BootstrapAdminPayload {
  username: string;
  display_name?: string;
  password: string;
  bootstrap_token?: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface ClaimInvitePayload {
  token: string;
  username: string;
  display_name?: string;
  password: string;
}

export interface UserInviteRecord {
  id: number;
  created_by_user_id?: number | null;
  claimed_by_user_id?: number | null;
  display_name_hint?: string | null;
  role_to_grant: string;
  expires_at?: string | null;
  claimed_at?: string | null;
  revoked_at?: string | null;
  created_at: string;
}

export interface CreateInvitePayload {
  display_name_hint?: string;
  role_to_grant?: string;
  expires_in_days?: number;
}

export interface InviteCreateRecord {
  invite: UserInviteRecord;
  token: string;
}
