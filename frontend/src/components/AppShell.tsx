import type { PropsWithChildren } from "react";
import { useEffect, useState } from "react";

import type { AuthUserRecord, VoiceSettingsRecord, VoiceSettingsUpdate } from "../api/types";
import { useFriendsSummary } from "../hooks/useFriendsSummary";
import { useIssues } from "../hooks/useIssues";
import type { ThemeAppearance } from "../theme/runtime";
import { normalizeSidebarMode, sidebarWidthForMode, type SidebarMode } from "../utils/sidebar";
import { NowPlayingDock } from "./NowPlayingDock";
import { IconGlyph } from "./IconGlyph";
import { SidebarNav } from "./SidebarNav";
import { TopBar } from "./TopBar";

type AppShellProps = PropsWithChildren<{
  currentPathname: string;
  currentUser: AuthUserRecord;
  onNavigate: (pathname: string) => void;
  onLogout: () => Promise<void>;
  onSearchTermChange: (value: string) => void;
  onUpdateSettings: (nextSettings: Partial<VoiceSettingsUpdate>) => Promise<boolean>;
  searchTerm: string;
  settings: VoiceSettingsRecord | null;
  themeAppearance: ThemeAppearance;
}>;

export function AppShell({
  children,
  currentPathname,
  currentUser,
  onNavigate,
  onLogout,
  onSearchTermChange,
  onUpdateSettings,
  searchTerm,
  settings,
  themeAppearance,
}: AppShellProps) {
  const { summary: issueSummary } = useIssues();
  const friendsSummary = useFriendsSummary();
  const [sidebarMode, setSidebarMode] = useState<SidebarMode>(normalizeSidebarMode(settings?.sidebar_mode));
  const navigationItems = [
    { label: "Home", pathname: "/home" },
    { label: "Discover", pathname: "/discover" },
    { label: "Library", pathname: "/" },
    { label: "Settings", pathname: "/settings" },
    { label: "Voices", pathname: "/voices" },
    {
      label: "Friends",
      pathname: "/friends",
      badgeCount: friendsSummary.pending_friend_requests + friendsSummary.pending_shares,
    },
    { label: "Series", pathname: "/series" },
    { label: "Collections", pathname: "/collections" },
    { label: "Issues", pathname: "/issues", badgeCount: issueSummary.total_count },
    { label: "Jobs", pathname: "/jobs" },
    { label: "Themes", pathname: "/themes" },
    ...(currentUser.role === "admin" ? [{ label: "Admin", pathname: "/admin" }] : []),
  ];

  const persistSidebarState = async (mode: SidebarMode) => {
    setSidebarMode(mode);
    await onUpdateSettings({
      sidebar_mode: mode,
      sidebar_width_px: sidebarWidthForMode(mode),
    });
  };

  useEffect(() => {
    const nextMode = normalizeSidebarMode(settings?.sidebar_mode);
    setSidebarMode(nextMode);
  }, [settings?.sidebar_mode]);

  const dockPosition = settings?.dock_position ?? "bottom";
  const tooltipsEnabled = settings?.tooltips_enabled ?? true;

  const handleSidebarToggle = async () => {
    if (sidebarMode === "icon") {
      await persistSidebarState("expanded");
      return;
    }

    await persistSidebarState("icon");
  };

  return (
    <div
      className={`app-shell app-shell--dock-${dockPosition} app-shell--sidebar-${sidebarMode} app-shell--appearance-${themeAppearance}`}
      style={{ ["--sidebar-width" as string]: `${sidebarWidthForMode(sidebarMode)}px` }}
    >
      <div className={`app-shell__rail app-shell__rail--${sidebarMode}`}>
        <button
          aria-label={sidebarMode === "icon" ? "Expand sidebar" : "Collapse sidebar"}
          className="app-shell__rail-toggle"
          onClick={() => {
            void handleSidebarToggle();
          }}
          title={
            tooltipsEnabled
              ? sidebarMode === "icon"
                ? "Expand sidebar"
                : "Collapse sidebar"
              : undefined
          }
          type="button"
        >
          <IconGlyph name={sidebarMode === "icon" ? "chevron-right" : "chevron-left"} />
        </button>
        <SidebarNav
          currentPathname={currentPathname}
          items={navigationItems}
          mode={sidebarMode}
          onNavigate={onNavigate}
          tooltipsEnabled={tooltipsEnabled}
        />
      </div>
      <div className="app-shell__main">
        <TopBar
          currentPathname={currentPathname}
          currentUser={currentUser}
          onNavigate={onNavigate}
          onLogout={onLogout}
          onSearchTermChange={onSearchTermChange}
          searchTerm={searchTerm}
        />
        <main className="app-shell__content">{children}</main>
        <NowPlayingDock
          dockPosition={dockPosition}
          onNavigate={onNavigate}
          tooltipsEnabled={tooltipsEnabled}
        />
      </div>
    </div>
  );
}
