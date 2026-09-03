import type { ThemeProfileRecord } from "../api/types";

export function formatThemeFamilyTitle(theme: ThemeProfileRecord): string {
  switch (theme.family) {
    case "showcase":
      return "Showcase theme";
    case "reader_focused":
      return "Reading-focused";
    case "cinema_focused":
      return "Cinema-focused";
    case "player_focused":
      return "Player-focused";
    case "imported_kavita":
      return "Imported theme";
    default:
      return "House theme";
  }
}

export function formatPreviewVariant(theme: ThemeProfileRecord): string {
  switch (theme.preview_variant) {
    case "light-airy":
      return "Light airy";
    case "dark-cozy":
      return "Dark cozy";
    case "showpiece":
      return "Showpiece";
    default:
      return "Standard";
  }
}

export function hasBackgroundArt(theme: ThemeProfileRecord): boolean {
  return Boolean(theme.background_asset_path);
}

export function hasShelfArt(theme: ThemeProfileRecord): boolean {
  return Boolean(theme.shelf_asset_path);
}
