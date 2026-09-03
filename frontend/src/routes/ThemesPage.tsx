import { useMemo, useState } from "react";

import { deleteTheme, importKavitaTheme } from "../api/client";
import type {
  KavitaThemeImportRecord,
  ThemeProfileRecord,
  VoiceSettingsRecord,
  VoiceSettingsUpdate,
} from "../api/types";
import { ThemeCard } from "../components/ThemeCard";
import { ThemeLayerPicker } from "../components/ThemeLayerPicker";
import { ThemePreviewPanel } from "../components/ThemePreviewPanel";
import { useThemes } from "../hooks/useThemes";
import { hydrateTheme, resolveThemeById } from "../theme/runtime";

type ThemesPageProps = {
  onUpdateSettings: (nextSettings: Partial<VoiceSettingsUpdate>) => Promise<boolean>;
  settings: VoiceSettingsRecord | null;
};

type ThemeGroup = {
  description: string;
  key: string;
  title: string;
  themes: ThemeProfileRecord[];
};

function fallbackTheme(themeId: string): ThemeProfileRecord {
  return {
    id: themeId,
    name: themeId,
    description: "The active theme is applied, but its full profile is not available in the current gallery response.",
    source_kind: "house",
    source_label: "Open Choice Reader",
    source_reference: null,
    is_builtin: true,
    sort_order: 999,
    family: "house",
    preview_variant: "standard",
    background_asset_path: null,
    background_overlay_path: null,
    shelf_asset_path: null,
    surface_texture_asset_path: null,
    supports_mix_and_match: true,
    tokens: {},
  };
}

export function ThemesPage({ onUpdateSettings, settings }: ThemesPageProps) {
  const { error, isLoading, refreshThemes, themes } = useThemes();
  const [previewThemeId, setPreviewThemeId] = useState<string | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [importCssText, setImportCssText] = useState("");
  const [importError, setImportError] = useState<string | null>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importName, setImportName] = useState("");
  const [importResult, setImportResult] = useState<KavitaThemeImportRecord | null>(null);
  const [isApplyingThemeId, setIsApplyingThemeId] = useState<string | null>(null);
  const [isDeletingThemeId, setIsDeletingThemeId] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);

  const activeThemeId = settings?.active_theme_id ?? settings?.ui_theme ?? "ember";
  const sortedThemes = useMemo(
    () =>
      [...themes]
        .map((theme) => hydrateTheme(theme))
        .sort((left, right) => left.sort_order - right.sort_order || left.name.localeCompare(right.name)),
    [themes],
  );
  const showcaseThemes = useMemo(
    () => sortedThemes.filter((theme) => theme.family === "showcase"),
    [sortedThemes],
  );
  const themeGroups = useMemo<ThemeGroup[]>(() => {
    const orderedGroups: ThemeGroup[] = [
      {
        key: "showcase",
        title: "Showcase themes",
        description: "Ten polished full-room presets with coordinated background art, shelf treatments, and richer chrome.",
        themes: [],
      },
      {
        key: "house",
        title: "House themes",
        description: "The original Open Choice Reader palettes and product-native defaults.",
        themes: [],
      },
      {
        key: "reading",
        title: "Reading-focused",
        description: "Reader-first dark palettes with calmer contrast and longer-session comfort.",
        themes: [],
      },
      {
        key: "cinema",
        title: "Cinema-focused",
        description: "Cinematic media-center looks with stronger glow, glass, and projection energy.",
        themes: [],
      },
      {
        key: "player",
        title: "Player-focused",
        description: "Cleaner player-app palettes with flatter surfaces and tighter accent control.",
        themes: [],
      },
      {
        key: "imported",
        title: "Imported from Kavita",
        description: "Converted CSS-variable themes that now behave like native Open Choice Reader themes.",
        themes: [],
      },
    ];

    for (const theme of sortedThemes) {
      if (theme.family === "showcase") {
        orderedGroups[0].themes.push(theme);
      } else if (!theme.is_builtin && theme.source_kind === "imported_kavita") {
        orderedGroups[5].themes.push(theme);
      } else if (theme.source_label === "Reading-focused") {
        orderedGroups[2].themes.push(theme);
      } else if (theme.source_label === "Cinema-focused") {
        orderedGroups[3].themes.push(theme);
      } else if (theme.source_label === "Player-focused") {
        orderedGroups[4].themes.push(theme);
      } else {
        orderedGroups[1].themes.push(theme);
      }
    }

    return orderedGroups.filter((group) => group.themes.length > 0);
  }, [sortedThemes]);
  const previewTheme =
    sortedThemes.find((theme) => theme.id === (previewThemeId ?? activeThemeId)) ??
    settings?.active_theme ??
    fallbackTheme(activeThemeId);
  const backgroundTheme = resolveThemeById(sortedThemes, settings?.background_override_theme_id ?? null);
  const shelfTheme = resolveThemeById(sortedThemes, settings?.shelf_override_theme_id ?? null);

  const handleApplyTheme = async (theme: ThemeProfileRecord) => {
    setApplyError(null);
    setIsApplyingThemeId(theme.id);
    const didSave = await onUpdateSettings({
      active_theme_id: theme.id,
      ui_theme: theme.id,
    });
    setIsApplyingThemeId(null);

    if (!didSave) {
      setApplyError(`Unable to apply ${theme.name} right now.`);
      return;
    }

    setPreviewThemeId(theme.id);
  };

  const handleDeleteTheme = async (theme: ThemeProfileRecord) => {
    setDeleteError(null);
    setIsDeletingThemeId(theme.id);
    try {
      await deleteTheme(theme.id);
      await refreshThemes();
      if (previewThemeId === theme.id) {
        setPreviewThemeId(null);
      }
      if (importResult?.theme.id === theme.id) {
        setImportResult(null);
      }
    } catch (deleteThemeError) {
      setDeleteError(deleteThemeError instanceof Error ? deleteThemeError.message : `Unable to delete ${theme.name} right now.`);
    } finally {
      setIsDeletingThemeId(null);
    }
  };

  const handleImportFromFile = async () => {
    if (!importFile) {
      setImportError("Choose a .css file to import first.");
      return;
    }

    await handleImport({ cssFile: importFile });
  };

  const handleImportFromText = async () => {
    if (!importCssText.trim()) {
      setImportError("Paste Kavita CSS before importing.");
      return;
    }

    await handleImport({ cssText: importCssText });
  };

  const handleImport = async ({ cssFile, cssText }: { cssFile?: File | null; cssText?: string }) => {
    setImportError(null);
    setDeleteError(null);
    setApplyError(null);
    setIsImporting(true);

    try {
      const result = await importKavitaTheme({
        cssFile,
        cssText,
        name: importName,
      });
      setImportResult(result);
      await refreshThemes();
      setPreviewThemeId(result.theme.id);
      if (cssFile) {
        setImportFile(null);
      }
    } catch (themeImportError) {
      setImportError(themeImportError instanceof Error ? themeImportError.message : "Unable to import that Kavita theme right now.");
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <section aria-label="Themes page" className="library-page themes-page">
      <div className="library-page__hero themes-page__hero">
        <div className="library-page__title-block">
          <p className="library-page__eyebrow">Themes</p>
          <h2>Themes</h2>
          <p>Browse installed themes, preview them, and apply the one you want across every connected session.</p>
        </div>
      </div>

      <details className="theme-import-disclosure">
        <summary className="theme-import-disclosure__summary">Import a Kavita theme (advanced)</summary>
        <section className="theme-import-panel" aria-label="Import Kavita theme">
        <div className="theme-import-panel__header">
          <div>
            <p className="theme-card__eyebrow">Kavita compatibility</p>
            <h3>Import a Kavita theme</h3>
          </div>
          <p className="theme-card__copy">
            Upload a Kavita `.css` theme file or paste CSS variables directly. Open Choice Reader maps supported variables into its native theme tokens and tells you exactly what it used.
          </p>
        </div>

        <div className="theme-import-panel__grid">
          <label className="library-page__field" htmlFor="theme-import-name">
            <span>Imported theme name</span>
            <input id="theme-import-name" onChange={(event) => setImportName(event.target.value)} value={importName} />
          </label>

          <label className="library-page__field" htmlFor="theme-import-file">
            <span>Upload Kavita CSS</span>
            <input
              accept=".css,text/css"
              id="theme-import-file"
              onChange={(event) => setImportFile(event.target.files?.[0] ?? null)}
              type="file"
            />
          </label>
        </div>

        <div className="theme-import-panel__actions">
          <button className="book-card__button" disabled={isImporting} onClick={() => void handleImportFromFile()} type="button">
            {isImporting ? "Importing..." : "Import uploaded CSS"}
          </button>
          {importFile ? <p className="theme-card__copy">{`Selected file: ${importFile.name}`}</p> : null}
        </div>

        <label className="library-page__field" htmlFor="theme-import-css">
          <span>Paste Kavita CSS</span>
          <textarea
            id="theme-import-css"
            onChange={(event) => setImportCssText(event.target.value)}
            placeholder=":root .bg-your-theme { --primary-color: #68b7ff; ... }"
            value={importCssText}
          />
        </label>

        <div className="theme-import-panel__actions">
          <button className="book-card__button" disabled={isImporting} onClick={() => void handleImportFromText()} type="button">
            {isImporting ? "Importing..." : "Import pasted CSS"}
          </button>
        </div>

        {importError ? (
          <p className="library-page__alert" role="alert">
            {importError}
          </p>
        ) : null}

        {importResult ? (
          <section className="theme-import-report" aria-label="Theme import report">
            <div className="theme-import-report__header">
              <div>
                <p className="theme-card__eyebrow">Import report</p>
                <h3>Imported theme ready</h3>
              </div>
              <span className="theme-card__badge">{importResult.theme.name}</span>
            </div>
            <p className="theme-card__copy">
              {`Mapped ${importResult.report.mapped_variables.length} supported variables from ${importResult.report.detected_variable_count} detected declarations.`}
            </p>
            {importResult.report.ignored_variables.length ? (
              <p className="theme-card__copy">{`Ignored variables: ${importResult.report.ignored_variables.join(", ")}`}</p>
            ) : null}
            {importResult.report.fallback_tokens.length ? (
              <p className="theme-card__copy">
                {`Fallback tokens: ${importResult.report.fallback_tokens.map((item) => item.target_token).join(", ")}`}
              </p>
            ) : null}
          </section>
        ) : null}
        </section>
      </details>

      {isLoading ? <p className="library-page__status-copy">Loading installed themes from the server...</p> : null}
      {error ? (
        <p className="library-page__alert" role="alert">
          {error}
        </p>
      ) : null}
      {applyError ? (
        <p className="library-page__alert" role="alert">
          {applyError}
        </p>
      ) : null}
      {deleteError ? (
        <p className="library-page__alert" role="alert">
          {deleteError}
        </p>
      ) : null}

      <div className="themes-page__layout">
        <div className="themes-page__gallery">
          {themeGroups.map((group) => (
            <section className="themes-page__group" key={group.key}>
              <div className="themes-page__group-header">
                <div>
                  <p className="theme-card__eyebrow">Theme pack</p>
                  <h3>{group.title}</h3>
                </div>
                <p className="theme-card__copy">{group.description}</p>
              </div>
              {group.key === "showcase" ? (
                <ThemeLayerPicker
                  backgroundOverrideThemeId={settings?.background_override_theme_id ?? null}
                  onResetToThemeDefaults={() => {
                    void onUpdateSettings({
                      background_override_theme_id: null,
                      shelf_override_theme_id: null,
                    });
                  }}
                  onSelectBackground={(themeId) => {
                    void onUpdateSettings({ background_override_theme_id: themeId });
                  }}
                  onSelectShelf={(themeId) => {
                    void onUpdateSettings({ shelf_override_theme_id: themeId });
                  }}
                  shelfOverrideThemeId={settings?.shelf_override_theme_id ?? null}
                  themes={showcaseThemes}
                />
              ) : null}
              <div className="themes-page__group-grid">
                {group.themes.map((theme) => (
                  <ThemeCard
                    isActive={theme.id === activeThemeId}
                    isApplying={isApplyingThemeId === theme.id}
                    isDeleting={isDeletingThemeId === theme.id}
                    isPreviewing={theme.id === previewTheme.id}
                    key={theme.id}
                    onApply={() => void handleApplyTheme(theme)}
                    onDelete={!theme.is_builtin ? () => void handleDeleteTheme(theme) : undefined}
                    onPreview={() => setPreviewThemeId(theme.id)}
                    theme={theme}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>

        <ThemePreviewPanel
          backgroundThemeName={backgroundTheme?.name ?? null}
          isPreviewing={previewTheme.id !== activeThemeId}
          shelfThemeName={shelfTheme?.name ?? null}
          theme={previewTheme}
        />
      </div>
    </section>
  );
}
