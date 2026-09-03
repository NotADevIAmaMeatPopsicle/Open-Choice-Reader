import { describe, expect, it } from "vitest";

import type { ThemeProfileRecord } from "../api/types";
import { inferThemeAppearance } from "../theme/runtime";

function buildTheme(overrides: Partial<ThemeProfileRecord>): ThemeProfileRecord {
  return {
    id: "theme-under-test",
    name: "Theme Under Test",
    description: null,
    source_kind: "builtin",
    source_label: "Open Choice Reader",
    source_reference: null,
    is_builtin: true,
    sort_order: 1,
    family: "showcase",
    preview_variant: "standard",
    background_asset_path: null,
    background_overlay_path: null,
    shelf_asset_path: null,
    surface_texture_asset_path: null,
    supports_mix_and_match: true,
    tokens: {},
    ...overrides,
  };
}

describe("inferThemeAppearance", () => {
  it("treats bright light-airy themes as light appearance", () => {
    const theme = buildTheme({
      id: "sunlit-reading-room",
      preview_variant: "light-airy",
      tokens: {
        "--color-bg": "#f4ecde",
        "--color-panel": "rgba(255, 248, 239, 0.92)",
        "--color-text": "#32261d",
      },
    });

    expect(inferThemeAppearance(theme)).toBe("light");
  });

  it("keeps darker showcase themes in dark appearance", () => {
    const theme = buildTheme({
      id: "mahogany-stacks",
      preview_variant: "dark-cozy",
      tokens: {
        "--color-bg": "#14100d",
        "--color-panel": "rgba(27, 22, 19, 0.92)",
        "--color-text": "#f8efe4",
      },
    });

    expect(inferThemeAppearance(theme)).toBe("dark");
  });
});
