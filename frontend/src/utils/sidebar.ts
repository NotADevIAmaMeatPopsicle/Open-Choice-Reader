export type SidebarMode = "expanded" | "icon";

export const EXPANDED_SIDEBAR_WIDTH_PX = 196;
export const ICON_SIDEBAR_WIDTH_PX = 74;

export function normalizeSidebarMode(value?: string | null): SidebarMode {
  if (value === "icon") {
    return "icon";
  }

  return "expanded";
}

export function sidebarWidthForMode(mode: SidebarMode): number {
  return mode === "icon" ? ICON_SIDEBAR_WIDTH_PX : EXPANDED_SIDEBAR_WIDTH_PX;
}
