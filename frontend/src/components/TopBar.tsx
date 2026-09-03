import type { AuthUserRecord } from "../api/types";
import { IconGlyph } from "./IconGlyph";

type TopBarProps = {
  currentPathname: string;
  currentUser: AuthUserRecord;
  onNavigate: (pathname: string) => void;
  onLogout: () => Promise<void>;
  searchTerm: string;
  onSearchTermChange: (value: string) => void;
};

export function TopBar({ currentPathname, currentUser, onNavigate, onLogout, searchTerm, onSearchTermChange }: TopBarProps) {
  const viewLabel =
    currentPathname === "/discover"
      ? "Discover"
      : currentPathname === "/jobs"
        ? "Exports"
        : currentPathname === "/voices"
          ? "Voices"
          : "Library";

  return (
    <header className="top-bar">
      <div className="top-bar__brand">
        <div aria-hidden="true" className="top-bar__brand-mark">
          <IconGlyph name="library" />
        </div>
        <h1 className="top-bar__title">Open Choice Reader</h1>
        <div className="top-bar__view-pill">{viewLabel}</div>
      </div>
      <label className="top-bar__search">
        <span aria-hidden="true" className="top-bar__search-icon">
          <IconGlyph name="search" />
        </span>
        <span className="sr-only">Search library</span>
        <input
          aria-label="Search library"
          onChange={(event) => {
            onSearchTermChange(event.target.value);
          }}
          placeholder="Search books, authors, or summaries"
          type="search"
          value={searchTerm}
        />
      </label>
      <div className="top-bar__actions">
        <button
          aria-label="Open dashboard"
          className="top-bar__icon-button"
          onClick={() => {
            onNavigate("/home");
          }}
          type="button"
        >
          <IconGlyph name="dashboard" />
        </button>
        <button
          aria-label="Open export queue"
          className="top-bar__icon-button"
          onClick={() => {
            onNavigate("/jobs");
          }}
          type="button"
        >
          <IconGlyph name="queue" />
        </button>
        <button
          aria-label="Open settings"
          className="top-bar__icon-button"
          onClick={() => {
            onNavigate("/settings");
          }}
          type="button"
        >
          <IconGlyph name="settings" />
        </button>
      </div>
      <div className="top-bar__status">
        <span className="top-bar__status-pill">Local only</span>
        <button
          className="top-bar__user-chip"
          onClick={() => {
            onNavigate("/settings");
          }}
          type="button"
        >
          <span aria-hidden="true" className="top-bar__user-icon">
            <IconGlyph name="user" />
          </span>
          <span>{currentUser.display_name}</span>
        </button>
        <button
          aria-label="Sign out"
          className="top-bar__icon-button"
          onClick={() => {
            void onLogout();
          }}
          type="button"
        >
          <IconGlyph name="logout" />
        </button>
      </div>
    </header>
  );
}
