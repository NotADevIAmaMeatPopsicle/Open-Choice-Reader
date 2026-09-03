import type { ThemeProfileRecord } from "../api/types";

type ThemeDecor = Pick<
  ThemeProfileRecord,
  | "background_asset_path"
  | "background_overlay_path"
  | "shelf_asset_path"
  | "surface_texture_asset_path"
  | "family"
  | "preview_variant"
  | "supports_mix_and_match"
>;

const BUILTIN_THEME_DECOR: Record<string, ThemeDecor> = {
  "sunlit-reading-room": {
    family: "showcase",
    preview_variant: "light-airy",
    background_asset_path: "/theme-assets/backgrounds/sunlit-reading-room.svg",
    background_overlay_path: "/theme-assets/textures/paper-glow-light.svg",
    shelf_asset_path: "/theme-assets/shelves/sunlit-oak-shelf.svg",
    surface_texture_asset_path: "/theme-assets/textures/parchment-soft.svg",
    supports_mix_and_match: true,
  },
  "linen-ledger": {
    family: "showcase",
    preview_variant: "light-airy",
    background_asset_path: "/theme-assets/backgrounds/linen-ledger.svg",
    background_overlay_path: "/theme-assets/textures/linen-weave.svg",
    shelf_asset_path: "/theme-assets/shelves/painted-cream-shelf.svg",
    surface_texture_asset_path: "/theme-assets/textures/linen-weave.svg",
    supports_mix_and_match: true,
  },
  "sea-glass-study": {
    family: "showcase",
    preview_variant: "light-airy",
    background_asset_path: "/theme-assets/backgrounds/sea-glass-study.svg",
    background_overlay_path: "/theme-assets/textures/sea-mist-overlay.svg",
    shelf_asset_path: "/theme-assets/shelves/weathered-teak-shelf.svg",
    surface_texture_asset_path: "/theme-assets/textures/linen-weave.svg",
    supports_mix_and_match: true,
  },
  "garden-atlas": {
    family: "showcase",
    preview_variant: "light-airy",
    background_asset_path: "/theme-assets/backgrounds/garden-atlas.svg",
    background_overlay_path: "/theme-assets/textures/leaf-shadow-light.svg",
    shelf_asset_path: "/theme-assets/shelves/sage-painted-shelf.svg",
    surface_texture_asset_path: "/theme-assets/textures/parchment-soft.svg",
    supports_mix_and_match: true,
  },
  "mahogany-stacks": {
    family: "showcase",
    preview_variant: "dark-cozy",
    background_asset_path: "/theme-assets/backgrounds/mahogany-stacks.svg",
    background_overlay_path: "/theme-assets/textures/warm-vignette.svg",
    shelf_asset_path: "/theme-assets/shelves/mahogany-shelf.svg",
    surface_texture_asset_path: "/theme-assets/textures/woodgrain-dark.svg",
    supports_mix_and_match: true,
  },
  "after-hours-atrium": {
    family: "showcase",
    preview_variant: "dark-cozy",
    background_asset_path: "/theme-assets/backgrounds/after-hours-atrium.svg",
    background_overlay_path: "/theme-assets/textures/night-vignette.svg",
    shelf_asset_path: "/theme-assets/shelves/atrium-night-shelf.svg",
    surface_texture_asset_path: "/theme-assets/textures/slate-paper-dark.svg",
    supports_mix_and_match: true,
  },
  "candlewick-catalog": {
    family: "showcase",
    preview_variant: "dark-cozy",
    background_asset_path: "/theme-assets/backgrounds/candlewick-catalog.svg",
    background_overlay_path: "/theme-assets/textures/warm-vignette.svg",
    shelf_asset_path: "/theme-assets/shelves/candlewick-shelf.svg",
    surface_texture_asset_path: "/theme-assets/textures/leather-paper-dark.svg",
    supports_mix_and_match: true,
  },
  "projector-noir-library": {
    family: "showcase",
    preview_variant: "dark-cozy",
    background_asset_path: "/theme-assets/backgrounds/projector-noir-library.svg",
    background_overlay_path: "/theme-assets/textures/projection-beam.svg",
    shelf_asset_path: "/theme-assets/shelves/noir-steel-shelf.svg",
    surface_texture_asset_path: "/theme-assets/textures/slate-paper-dark.svg",
    supports_mix_and_match: true,
  },
  "lantern-meadow-library": {
    family: "showcase",
    preview_variant: "showpiece",
    background_asset_path: "/theme-assets/backgrounds/lantern-meadow-library.svg",
    background_overlay_path: "/theme-assets/textures/painted-paper.svg",
    shelf_asset_path: "/theme-assets/shelves/storybook-painted-shelf.svg",
    surface_texture_asset_path: "/theme-assets/textures/painted-paper.svg",
    supports_mix_and_match: true,
  },
  "grand-oak-observatory": {
    family: "showcase",
    preview_variant: "showpiece",
    background_asset_path: "/theme-assets/backgrounds/grand-oak-observatory.svg",
    background_overlay_path: "/theme-assets/textures/brass-stars.svg",
    shelf_asset_path: "/theme-assets/shelves/grand-oak-shelf.svg",
    surface_texture_asset_path: "/theme-assets/textures/woodgrain-dark.svg",
    supports_mix_and_match: true,
  },
};

export type EffectiveThemeLayers = {
  backgroundAssetPath: string | null;
  backgroundOverlayPath: string | null;
  shelfAssetPath: string | null;
  surfaceTextureAssetPath: string | null;
};

export type ThemeAppearance = "light" | "dark";

export function hydrateTheme(theme: ThemeProfileRecord): ThemeProfileRecord {
  const builtinDecor = BUILTIN_THEME_DECOR[theme.id];
  if (!builtinDecor) {
    return theme;
  }

  return {
    ...builtinDecor,
    ...theme,
    background_asset_path: theme.background_asset_path ?? builtinDecor.background_asset_path,
    background_overlay_path: theme.background_overlay_path ?? builtinDecor.background_overlay_path,
    shelf_asset_path: theme.shelf_asset_path ?? builtinDecor.shelf_asset_path,
    surface_texture_asset_path:
      theme.surface_texture_asset_path ?? builtinDecor.surface_texture_asset_path,
    family: theme.family || builtinDecor.family,
    preview_variant: theme.preview_variant || builtinDecor.preview_variant,
  };
}

function parseHexChannel(channel: string): number {
  return Number.parseInt(channel, 16);
}

function parseColorChannels(value: string | null | undefined): [number, number, number] | null {
  if (!value) {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  const hex = normalized.replace("#", "");
  if (hex.length === 3 && /^[0-9a-f]{3}$/i.test(hex)) {
    return [
      parseHexChannel(`${hex[0]}${hex[0]}`),
      parseHexChannel(`${hex[1]}${hex[1]}`),
      parseHexChannel(`${hex[2]}${hex[2]}`),
    ];
  }

  if (hex.length === 6 && /^[0-9a-f]{6}$/i.test(hex)) {
    return [
      parseHexChannel(hex.slice(0, 2)),
      parseHexChannel(hex.slice(2, 4)),
      parseHexChannel(hex.slice(4, 6)),
    ];
  }

  const rgbMatch = normalized.match(/^rgba?\(([^)]+)\)$/);
  if (!rgbMatch) {
    return null;
  }

  const parts = rgbMatch[1]
    .split(",")
    .map((part) => Number.parseFloat(part.trim()))
    .slice(0, 3);
  if (parts.length !== 3 || parts.some((part) => Number.isNaN(part))) {
    return null;
  }

  return [parts[0], parts[1], parts[2]];
}

function computeRelativeLuminance([red, green, blue]: [number, number, number]): number {
  const normalize = (value: number) => {
    const channel = value / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  };

  return 0.2126 * normalize(red) + 0.7152 * normalize(green) + 0.0722 * normalize(blue);
}

export function inferThemeAppearance(theme: ThemeProfileRecord): ThemeAppearance {
  const hydratedTheme = hydrateTheme(theme);

  if (hydratedTheme.preview_variant === "light-airy") {
    return "light";
  }

  if (hydratedTheme.preview_variant === "dark-cozy") {
    return "dark";
  }

  const colorSample =
    parseColorChannels(hydratedTheme.tokens["--color-panel"]) ??
    parseColorChannels(hydratedTheme.tokens["--color-bg"]);

  if (!colorSample) {
    return "dark";
  }

  return computeRelativeLuminance(colorSample) >= 0.5 ? "light" : "dark";
}

export function resolveThemeById(
  themes: ThemeProfileRecord[],
  themeId: string | null | undefined,
): ThemeProfileRecord | null {
  if (!themeId) {
    return null;
  }

  const directMatch = themes.find((theme) => theme.id === themeId);
  if (directMatch) {
    return hydrateTheme(directMatch);
  }

  const decor = BUILTIN_THEME_DECOR[themeId];
  if (!decor) {
    return null;
  }

  return {
    id: themeId,
    name: themeId,
    description: null,
    source_kind: decor.family,
    source_label: "Open Choice Reader",
    source_reference: null,
    is_builtin: true,
    sort_order: 999,
    family: decor.family,
    preview_variant: decor.preview_variant,
    background_asset_path: decor.background_asset_path,
    background_overlay_path: decor.background_overlay_path,
    shelf_asset_path: decor.shelf_asset_path,
    surface_texture_asset_path: decor.surface_texture_asset_path,
    supports_mix_and_match: decor.supports_mix_and_match,
    tokens: {},
  };
}

export function resolveEffectiveThemeLayers(args: {
  activeTheme: ThemeProfileRecord | null | undefined;
  backgroundOverrideThemeId?: string | null;
  shelfOverrideThemeId?: string | null;
  themes?: ThemeProfileRecord[];
}): EffectiveThemeLayers {
  const themes = args.themes ?? [];
  const activeTheme = args.activeTheme ? hydrateTheme(args.activeTheme) : null;
  const backgroundTheme =
    resolveThemeById(themes, args.backgroundOverrideThemeId) ?? activeTheme;
  const shelfTheme = resolveThemeById(themes, args.shelfOverrideThemeId) ?? activeTheme;

  return {
    backgroundAssetPath: backgroundTheme?.background_asset_path ?? null,
    backgroundOverlayPath: backgroundTheme?.background_overlay_path ?? null,
    shelfAssetPath: shelfTheme?.shelf_asset_path ?? null,
    surfaceTextureAssetPath:
      shelfTheme?.surface_texture_asset_path ??
      activeTheme?.surface_texture_asset_path ??
      null,
  };
}

export function toCssImageValue(path: string | null | undefined): string {
  return path ? `url("${path}")` : "none";
}
