import { useEffect, useState } from "react";

import { changePassword } from "../api/client";
import type { AuthUserRecord, VoiceOptionRecord, VoiceSettingsRecord, VoiceSettingsUpdate } from "../api/types";
import { resolveVoiceOption } from "../utils/voices";

const DOCK_OPTIONS = [
  { value: "bottom", label: "Bottom dock" },
  { value: "top-left", label: "Top left" },
  { value: "top-center", label: "Top center" },
  { value: "top-right", label: "Top right" },
];

type PreferenceDraft = {
  autoPauseOnInterrupt: boolean;
  defaultPlaybackSpeed: number;
  dockPosition: string;
  narrationPace: number;
  sidebarMode: string;
  tooltipsEnabled: boolean;
};

type SettingsPageProps = {
  currentUser: AuthUserRecord;
  error: string | null;
  isLoading: boolean;
  isSaving: boolean;
  onLogout: () => Promise<void>;
  saveSuccessMessage: string | null;
  settings: VoiceSettingsRecord | null;
  updateSettings: (nextSettings: Partial<VoiceSettingsUpdate>) => Promise<boolean>;
  voiceOptions: VoiceOptionRecord[];
};

export function SettingsPage({
  currentUser,
  error,
  isLoading,
  isSaving,
  onLogout,
  saveSuccessMessage,
  settings,
  updateSettings,
  voiceOptions,
}: SettingsPageProps) {
  const [preferences, setPreferences] = useState<PreferenceDraft | null>(null);
  const [passwordDraft, setPasswordDraft] = useState({ current: "", next: "", confirm: "" });
  const [passwordStatus, setPasswordStatus] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  useEffect(() => {
    if (!settings) {
      return;
    }

    setPreferences({
      autoPauseOnInterrupt: settings.auto_pause_on_interrupt,
      defaultPlaybackSpeed: settings.default_playback_speed,
      dockPosition: settings.dock_position,
      narrationPace: settings.live_narration_pace ?? 1,
      sidebarMode: settings.sidebar_mode,
      tooltipsEnabled: settings.tooltips_enabled,
    });
  }, [settings]);

  const cloneRuntime = settings?.clone_runtime ?? {
    availability: "unknown",
    availability_detail: "Clone runtime details are unavailable until the host reports them.",
    engine: "qwen3_clone",
    execution_summary: "Live cloned reading and audiobook exports run on the connected host when the clone runtime is available.",
    model_name: "Unknown clone model",
    preset_count: 0,
    usage_summary: "Saved cloned presets can be used for live reading and audiobook export when the clone runtime is available.",
    available_models: [],
  };
  const selectedCloneModel =
    cloneRuntime.available_models.find((model) => model.engine === settings?.selected_clone_model_engine) ?? null;
  const defaultLiveVoice = resolveVoiceOption(settings?.default_live_voice_id, voiceOptions);
  const defaultExportVoice = resolveVoiceOption(settings?.default_export_voice_id, voiceOptions);
  const fallbackVoice = resolveVoiceOption(settings?.fallback_voice_id ?? null, voiceOptions);
  const effectivePreferences =
    preferences ??
    (settings
      ? {
          autoPauseOnInterrupt: settings.auto_pause_on_interrupt,
          defaultPlaybackSpeed: settings.default_playback_speed,
          dockPosition: settings.dock_position,
          narrationPace: settings.live_narration_pace ?? 1,
          sidebarMode: settings.sidebar_mode,
          tooltipsEnabled: settings.tooltips_enabled,
        }
      : null);

  const handleSavePreferences = async () => {
    if (!effectivePreferences) {
      return;
    }

    await updateSettings({
      auto_pause_on_interrupt: effectivePreferences.autoPauseOnInterrupt,
      default_playback_speed: effectivePreferences.defaultPlaybackSpeed,
      dock_position: effectivePreferences.dockPosition,
      live_narration_pace: effectivePreferences.narrationPace,
      sidebar_mode: effectivePreferences.sidebarMode,
      tooltips_enabled: effectivePreferences.tooltipsEnabled,
    });
  };

  const handleChangePassword = async () => {
    setPasswordStatus(null);

    if (!passwordDraft.current || !passwordDraft.next) {
      setPasswordError("Enter your current password and a new password.");
      return;
    }
    if (passwordDraft.next !== passwordDraft.confirm) {
      setPasswordError("New password and confirmation do not match.");
      return;
    }

    setIsChangingPassword(true);
    setPasswordError(null);
    try {
      await changePassword({
        current_password: passwordDraft.current,
        new_password: passwordDraft.next,
      });
      setPasswordDraft({ current: "", next: "", confirm: "" });
      setPasswordStatus("Password updated.");
    } catch (error) {
      setPasswordError(error instanceof Error ? error.message : "Unable to change password");
    } finally {
      setIsChangingPassword(false);
    }
  };

  if (!settings) {
    return (
      <section aria-label="Settings page" className="library-page settings-page">
        {isLoading ? <p className="library-page__status-copy">Loading server runtime details...</p> : null}
        {error ? (
          <p className="library-page__alert" role="alert">
            {error}
          </p>
        ) : null}
      </section>
    );
  }

  return (
    <section aria-label="Settings page" className="library-page settings-page">
      <div className="library-page__hero settings-page__hero">
        <div className="library-page__title-block">
          <p className="library-page__eyebrow">Settings</p>
          <h2>Settings</h2>
          <p>
            Server status, engine health, and the active narrator defaults live here. Change voices in the
            dedicated Voices workspace and tune player ergonomics below.
          </p>
        </div>
        <div className="settings-page__hero-actions">
          <a className="book-card__button" href="/voices" style={{ textDecoration: "none" }}>
            Manage narrators
          </a>
          <a className="book-card__button book-card__button--ghost" href="/themes" style={{ textDecoration: "none" }}>
            Manage themes
          </a>
          <button
            className="book-card__button book-card__button--ghost"
            disabled={!settings || !effectivePreferences || isSaving}
            onClick={() => void handleSavePreferences()}
            type="button"
          >
            {isSaving ? "Saving preferences..." : "Save reader preferences"}
          </button>
        </div>
      </div>

      {saveSuccessMessage ? <p className="library-page__status-copy">{saveSuccessMessage}</p> : null}
      {isLoading ? <p className="library-page__status-copy">Loading server runtime details...</p> : null}
      {error ? (
        <p className="library-page__alert" role="alert">
          {error}
        </p>
      ) : null}

      {settings ? (
        <>
          <section className="settings-page__defaults-grid" aria-label="Account summary">
            <article className="settings-page__summary-card">
              <p className="voices-page__summary-label">Signed-in account</p>
              <p className="voices-page__summary-value">{currentUser.display_name}</p>
              <p className="voices-page__summary-copy">
                {currentUser.username} | {currentUser.role}
              </p>
            </article>
            <article className="settings-page__summary-card">
              <p className="voices-page__summary-label">Session</p>
              <p className="voices-page__summary-value">Authenticated</p>
              <button
                className="book-card__button book-card__button--ghost"
                onClick={() => {
                  void onLogout();
                }}
                type="button"
              >
                Sign out
              </button>
            </article>
            <article className="settings-page__summary-card">
              <p className="voices-page__summary-label">Change password</p>
              <label className="library-page__field">
                <span>Current password</span>
                <input
                  aria-label="Current password"
                  autoComplete="current-password"
                  onChange={(event) =>
                    setPasswordDraft((current) => ({ ...current, current: event.target.value }))
                  }
                  type="password"
                  value={passwordDraft.current}
                />
              </label>
              <label className="library-page__field">
                <span>New password</span>
                <input
                  aria-label="New password"
                  autoComplete="new-password"
                  onChange={(event) => setPasswordDraft((current) => ({ ...current, next: event.target.value }))}
                  type="password"
                  value={passwordDraft.next}
                />
              </label>
              <label className="library-page__field">
                <span>Confirm new password</span>
                <input
                  aria-label="Confirm new password"
                  autoComplete="new-password"
                  onChange={(event) =>
                    setPasswordDraft((current) => ({ ...current, confirm: event.target.value }))
                  }
                  type="password"
                  value={passwordDraft.confirm}
                />
              </label>
              <button
                className="book-card__button"
                disabled={isChangingPassword}
                onClick={() => {
                  void handleChangePassword();
                }}
                type="button"
              >
                {isChangingPassword ? "Updating password..." : "Update password"}
              </button>
              {passwordStatus ? (
                <p className="library-page__status-copy" role="status">
                  {passwordStatus}
                </p>
              ) : null}
              {passwordError ? (
                <p className="library-page__alert" role="alert">
                  {passwordError}
                </p>
              ) : null}
            </article>
          </section>

          <section className="settings-page__defaults-grid" aria-label="Current narrator defaults">
            <article className="settings-page__summary-card">
              <p className="voices-page__summary-label">Default live narrator</p>
              <p className="voices-page__summary-value">{defaultLiveVoice?.name ?? "Not selected"}</p>
              <p className="voices-page__summary-copy">
                {defaultLiveVoice
                  ? `${defaultLiveVoice.engine_family ?? defaultLiveVoice.engine} | ${defaultLiveVoice.mode_label}`
                  : "Choose in Voices"}
              </p>
            </article>
            <article className="settings-page__summary-card">
              <p className="voices-page__summary-label">Fallback narrator</p>
              <p className="voices-page__summary-value">{fallbackVoice?.name ?? "No fallback"}</p>
              <p className="voices-page__summary-copy">
                {fallbackVoice
                  ? `${fallbackVoice.engine_family ?? fallbackVoice.engine} | ${fallbackVoice.availability_detail}`
                  : "Playback will stay on the selected live narrator only"}
              </p>
            </article>
            <article className="settings-page__summary-card">
              <p className="voices-page__summary-label">Default export narrator</p>
              <p className="voices-page__summary-value">{defaultExportVoice?.name ?? "Not selected"}</p>
              <p className="voices-page__summary-copy">
                {defaultExportVoice?.mode_label ?? "Choose a saved clone preset in Voices"}
              </p>
            </article>
            <article className="settings-page__summary-card">
              <p className="voices-page__summary-label">Active theme</p>
              <p className="voices-page__summary-value">{settings.active_theme?.name ?? "Not selected"}</p>
              <p className="voices-page__summary-copy">
                {settings.active_theme
                  ? `${settings.active_theme.source_label} | ${settings.active_theme.source_kind}`
                  : "Choose in Themes"}
              </p>
            </article>
            <article className="settings-page__summary-card">
              <p className="voices-page__summary-label">Premium model</p>
              <p className="voices-page__summary-value">{selectedCloneModel?.display_name ?? "Premium clone 0.6B"}</p>
              <p className="voices-page__summary-copy">{selectedCloneModel?.model_name ?? cloneRuntime.model_name}</p>
            </article>
          </section>

          <section className="settings-page__preferences-panel" aria-label="Reader preferences">
            <div className="settings-page__panel-header">
              <div>
                <p className="library-page__eyebrow">Reader Preferences</p>
                <h3>Layout, speed, and accessibility</h3>
              </div>
              <p className="settings-page__panel-copy">
                These preferences persist on the server so the reader feels consistent across devices.
              </p>
            </div>
            {effectivePreferences ? (
              <div className="settings-page__preferences-grid">
                <label className="library-page__field">
                  <span>Sidebar layout</span>
                  <select
                    aria-label="Sidebar layout"
                    onChange={(event) =>
                      setPreferences((current) =>
                        current
                          ? { ...current, sidebarMode: event.target.value }
                          : {
                              ...effectivePreferences,
                              sidebarMode: event.target.value,
                            },
                      )
                    }
                    value={effectivePreferences.sidebarMode}
                  >
                    <option value="expanded">Fully open</option>
                    <option value="icon">Icons only</option>
                  </select>
                </label>
                <label className="library-page__field">
                  <span>Player position</span>
                  <select
                    aria-label="Player position"
                    onChange={(event) =>
                      setPreferences((current) =>
                        current
                          ? { ...current, dockPosition: event.target.value }
                          : {
                              ...effectivePreferences,
                              dockPosition: event.target.value,
                            },
                      )
                    }
                    value={effectivePreferences.dockPosition}
                  >
                    {DOCK_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="library-page__field">
                  <span>Default playback speed</span>
                  <input
                    aria-label="Default playback speed"
                    max="8"
                    min="0.5"
                    onChange={(event) =>
                      setPreferences((current) =>
                        current
                          ? { ...current, defaultPlaybackSpeed: Number(event.target.value) }
                          : {
                              ...effectivePreferences,
                              defaultPlaybackSpeed: Number(event.target.value),
                            },
                      )
                    }
                    step="0.05"
                    type="number"
                    value={Number(effectivePreferences.defaultPlaybackSpeed.toFixed(2))}
                  />
                </label>
                <label className="library-page__field">
                  <span>Narrator pace (built-in voices)</span>
                  <input
                    aria-label="Narrator pace"
                    max="2"
                    min="0.5"
                    onChange={(event) =>
                      setPreferences((current) =>
                        current
                          ? { ...current, narrationPace: Number(event.target.value) }
                          : {
                              ...effectivePreferences,
                              narrationPace: Number(event.target.value),
                            },
                      )
                    }
                    step="0.05"
                    type="number"
                    value={Number(effectivePreferences.narrationPace.toFixed(2))}
                  />
                  <span className="settings-page__panel-copy">
                    Speeds up the narration itself so it sounds natural. Cloned voices keep their native pace.
                  </span>
                </label>
                <label className="settings-page__toggle">
                  <input
                    aria-label="Show hover labels for player buttons"
                    checked={effectivePreferences.tooltipsEnabled}
                    onChange={(event) =>
                      setPreferences((current) =>
                        current
                          ? { ...current, tooltipsEnabled: event.target.checked }
                          : {
                              ...effectivePreferences,
                              tooltipsEnabled: event.target.checked,
                            },
                      )
                    }
                    type="checkbox"
                  />
                  <span>Show hover labels for player buttons</span>
                </label>
                <label className="settings-page__toggle">
                  <input
                    aria-label="Pause when Open Choice Reader is backgrounded or the browser reports a media interruption"
                    checked={effectivePreferences.autoPauseOnInterrupt}
                    onChange={(event) =>
                      setPreferences((current) =>
                        current
                          ? { ...current, autoPauseOnInterrupt: event.target.checked }
                          : {
                              ...effectivePreferences,
                              autoPauseOnInterrupt: event.target.checked,
                            },
                      )
                    }
                    type="checkbox"
                  />
                  <span>Pause when Open Choice Reader is backgrounded or the browser reports a media interruption</span>
                </label>
              </div>
            ) : (
              <p className="library-page__status-copy">Loading saved reader preferences...</p>
            )}
            <p className="settings-page__panel-copy">
              This is best-effort browser behavior. It usually catches hidden-tab, backgrounded-page, and some browser
              media interruptions, but it cannot detect every OS alarm or another app&apos;s audio.
            </p>
          </section>

          <section className="settings-page__panel">
            <div className="settings-page__panel-header">
              <div>
                <p className="library-page__eyebrow">Browser extension</p>
                <h3>Browser extension</h3>
              </div>
              <p className="settings-page__panel-copy">
                Install the handoff bundle in Chrome, Edge, Brave, Arc, or another Chromium-based browser.
              </p>
            </div>
            <div className="settings-page__extension-actions">
              <a className="book-card__button" href="/api/extension/chromium">
                Download Chromium-browser bundle
              </a>
              <a className="book-card__button book-card__button--ghost" href="/discover" style={{ textDecoration: "none" }}>
                Open Discover
              </a>
            </div>
            <p className="settings-page__panel-copy">
              Right-click any page or selected text to import or read it immediately.
            </p>
            <p className="settings-page__panel-copy">
              The popup still supports narrator choice and a temporary playback-speed override when you want more
              control than the quick handoff actions.
            </p>
            <p className="settings-page__panel-copy">
              The extension reuses your signed-in browser session on this host when possible. If it sends you back to
              the login shell, sign in there first and then retry the page or selection handoff.
            </p>
            <p className="settings-page__panel-copy">
              Enter the URL of the Open Choice Reader server in the extension popup, for example
              {" "}
              <code>http://127.0.0.1:8000</code> for a local installation.
            </p>
            <p className="settings-page__panel-copy">
              Firefox and Safari do not currently have a packaged extension build.
            </p>
          </section>

        </>
      ) : null}
    </section>
  );
}
