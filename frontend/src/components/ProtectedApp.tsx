import { useEffect, useMemo, useRef, useState } from "react";

import type { AuthUserRecord } from "../api/types";
import { setAutoPauseOnInterruptPreference } from "../hooks/usePlayer";
import { useSettings } from "../hooks/useSettings";
import { AdminPage } from "../routes/AdminPage";
import { BookPage } from "../routes/BookPage";
import { CollectionsPage } from "../routes/CollectionsPage";
import { DiscoverPage } from "../routes/DiscoverPage";
import { FriendsPage } from "../routes/FriendsPage";
import { HomePage } from "../routes/HomePage";
import { IssuesPage } from "../routes/IssuesPage";
import { JobsPage } from "../routes/JobsPage";
import { LibraryPage } from "../routes/LibraryPage";
import { ReaderPage } from "../routes/ReaderPage";
import { SeriesPage } from "../routes/SeriesPage";
import { SettingsPage } from "../routes/SettingsPage";
import { ThemesPage } from "../routes/ThemesPage";
import { VoicesPage } from "../routes/VoicesPage";
import {
  hydrateTheme,
  inferThemeAppearance,
  resolveEffectiveThemeLayers,
  toCssImageValue,
} from "../theme/runtime";
import { AppShell } from "./AppShell";

type ProtectedAppProps = {
  currentPathname: string;
  currentUser: AuthUserRecord;
  onLogout: () => Promise<void>;
  onNavigate: (pathname: string) => void;
};

export function ProtectedApp({ currentPathname, currentUser, onLogout, onNavigate }: ProtectedAppProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const { error, isLoading, isSaving, saveSuccessMessage, settings, updateSettings, voiceOptions } = useSettings();
  const appliedThemeTokenKeysRef = useRef<string[]>([]);
  const activeTheme = useMemo(
    () => (settings?.active_theme ? hydrateTheme(settings.active_theme) : null),
    [settings?.active_theme],
  );
  const themeAppearance = activeTheme ? inferThemeAppearance(activeTheme) : "dark";

  useEffect(() => {
    const root = document.documentElement;
    const themeLayers = resolveEffectiveThemeLayers({
      activeTheme,
      backgroundOverrideThemeId: settings?.background_override_theme_id,
      shelfOverrideThemeId: settings?.shelf_override_theme_id,
    });

    if (!activeTheme) {
      root.setAttribute("data-theme", settings?.ui_theme ?? "ember");
      root.setAttribute("data-theme-appearance", "dark");
      root.style.colorScheme = "dark";
      return;
    }

    root.setAttribute("data-theme", activeTheme.id);
    root.setAttribute("data-theme-family", activeTheme.family);
    root.setAttribute("data-theme-preview-variant", activeTheme.preview_variant);
    root.setAttribute("data-theme-appearance", themeAppearance);
    root.style.colorScheme = themeAppearance;
    root.style.setProperty("--theme-background-image", toCssImageValue(themeLayers.backgroundAssetPath));
    root.style.setProperty("--theme-background-overlay", toCssImageValue(themeLayers.backgroundOverlayPath));
    root.style.setProperty("--theme-shelf-image", toCssImageValue(themeLayers.shelfAssetPath));
    root.style.setProperty("--theme-surface-texture", toCssImageValue(themeLayers.surfaceTextureAssetPath));

    for (const tokenName of appliedThemeTokenKeysRef.current) {
      if (!(tokenName in activeTheme.tokens)) {
        root.style.removeProperty(tokenName);
      }
    }

    for (const [tokenName, tokenValue] of Object.entries(activeTheme.tokens)) {
      root.style.setProperty(tokenName, tokenValue);
    }

    appliedThemeTokenKeysRef.current = Object.keys(activeTheme.tokens);
  }, [
    settings?.active_theme,
    settings?.background_override_theme_id,
    settings?.shelf_override_theme_id,
    settings?.ui_theme,
    activeTheme,
    themeAppearance,
  ]);

  useEffect(() => {
    setAutoPauseOnInterruptPreference(settings?.auto_pause_on_interrupt ?? true);
  }, [settings?.auto_pause_on_interrupt]);

  let page = <LibraryPage onNavigate={onNavigate} searchTerm={searchTerm} />;
  if (currentPathname.startsWith("/reader/")) {
    page = <ReaderPage sessionId={currentPathname.split("/")[2] ?? "1"} />;
  } else if (currentPathname.startsWith("/books/")) {
    page = <BookPage bookId={currentPathname.split("/")[2] ?? "1"} onNavigate={onNavigate} />;
  } else if (currentPathname === "/home") {
    page = <HomePage onNavigate={onNavigate} searchTerm={searchTerm} />;
  } else if (currentPathname === "/discover") {
    page = <DiscoverPage onNavigate={onNavigate} />;
  } else if (currentPathname === "/series") {
    page = <SeriesPage onNavigate={onNavigate} searchTerm={searchTerm} />;
  } else if (currentPathname === "/collections") {
    page = <CollectionsPage onNavigate={onNavigate} />;
  } else if (currentPathname === "/issues") {
    page = <IssuesPage onNavigate={onNavigate} />;
  } else if (currentPathname === "/jobs") {
    page = <JobsPage />;
  } else if (currentPathname === "/voices") {
    page = <VoicesPage />;
  } else if (currentPathname === "/friends") {
    page = <FriendsPage onNavigate={onNavigate} />;
  } else if (currentPathname === "/admin") {
    page = <AdminPage currentUser={currentUser} />;
  } else if (currentPathname === "/themes") {
    page = <ThemesPage onUpdateSettings={updateSettings} settings={settings} />;
  } else if (currentPathname === "/settings") {
    page = (
      <SettingsPage
        currentUser={currentUser}
        error={error}
        isLoading={isLoading}
        isSaving={isSaving}
        onLogout={onLogout}
        saveSuccessMessage={saveSuccessMessage}
        settings={settings}
        updateSettings={updateSettings}
        voiceOptions={voiceOptions}
      />
    );
  }

  return (
    <AppShell
      currentPathname={currentPathname}
      currentUser={currentUser}
      onLogout={onLogout}
      onNavigate={onNavigate}
      onSearchTermChange={setSearchTerm}
      onUpdateSettings={updateSettings}
      searchTerm={searchTerm}
      settings={settings}
      themeAppearance={themeAppearance}
    >
      {page}
    </AppShell>
  );
}
