import { IconGlyph } from "./IconGlyph";
import type { SidebarMode } from "../utils/sidebar";

type NavigationItem = {
  label: string;
  pathname: string;
  badgeCount?: number;
};

type SidebarNavProps = {
  currentPathname: string;
  items: NavigationItem[];
  mode?: SidebarMode;
  onNavigate: (pathname: string) => void;
  tooltipsEnabled?: boolean;
};

function isActive(currentPathname: string, pathname: string) {
  if (pathname === "/") {
    return currentPathname === "/" || currentPathname.startsWith("/books/") || currentPathname.startsWith("/reader/");
  }

  return currentPathname === pathname;
}

function iconNameForLabel(label: string) {
  switch (label) {
    case "Home":
      return "home";
    case "Discover":
      return "discover";
    case "Library":
      return "library";
    case "Series":
      return "series";
    case "Collections":
      return "collections";
    case "Issues":
      return "issues";
    case "Jobs":
      return "jobs";
    case "Voices":
      return "voices";
    case "Friends":
      return "friends";
    case "Themes":
      return "themes";
    case "Settings":
      return "settings";
    case "Admin":
      return "admin";
    default:
      return "book";
  }
}

export function SidebarNav({
  currentPathname,
  items,
  mode = "expanded",
  onNavigate,
  tooltipsEnabled = true,
}: SidebarNavProps) {
  return (
    <nav aria-label="Primary" className={`sidebar-nav sidebar-nav--${mode}`}>
      {items.map((item) => {
        const active = isActive(currentPathname, item.pathname);

        return (
          <div className="sidebar-nav__item" key={item.pathname}>
            <a
              aria-current={active ? "page" : undefined}
              className={`sidebar-nav__link${active ? " sidebar-nav__link--active" : ""}`}
              href={item.pathname}
              onClick={(event) => {
                event.preventDefault();
                onNavigate(item.pathname);
              }}
              title={tooltipsEnabled && mode === "icon" ? item.label : undefined}
            >
              <span className="sidebar-nav__glyph" aria-hidden="true">
                <IconGlyph name={iconNameForLabel(item.label)} />
              </span>
              <span className={`sidebar-nav__label${mode === "icon" ? " sidebar-nav__label--sr-only" : ""}`}>
                {item.label}
              </span>
            </a>
            {item.badgeCount && item.badgeCount > 0 ? (
              <span
                aria-label={`${item.badgeCount} issues need attention`}
                className="sidebar-nav__badge"
                role="status"
              >
                {item.badgeCount}
              </span>
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}
