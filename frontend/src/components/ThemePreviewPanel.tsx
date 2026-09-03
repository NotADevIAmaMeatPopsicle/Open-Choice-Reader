import type { CSSProperties } from "react";

import type { ThemeProfileRecord } from "../api/types";
import { formatPreviewVariant, formatThemeFamilyTitle } from "../theme/showcaseThemePreview";
import { resolveEffectiveThemeLayers, toCssImageValue } from "../theme/runtime";

type ThemePreviewPanelProps = {
  backgroundThemeName?: string | null;
  isPreviewing: boolean;
  shelfThemeName?: string | null;
  theme: ThemeProfileRecord;
};

export function ThemePreviewPanel({
  backgroundThemeName,
  isPreviewing,
  shelfThemeName,
  theme,
}: ThemePreviewPanelProps) {
  const themeLayers = resolveEffectiveThemeLayers({ activeTheme: theme });
  const previewStyle = {
    "--theme-preview-accent": theme.tokens["--color-accent"] ?? "#d7a24c",
    "--theme-preview-bg": theme.tokens["--color-bg"] ?? "#151413",
    "--theme-preview-panel": theme.tokens["--color-panel"] ?? "rgba(25, 24, 23, 0.94)",
    "--theme-preview-background-image": toCssImageValue(themeLayers.backgroundAssetPath),
    "--theme-preview-background-overlay": toCssImageValue(themeLayers.backgroundOverlayPath),
    "--theme-preview-shelf-image": toCssImageValue(themeLayers.shelfAssetPath),
  } as CSSProperties;

  return (
    <section aria-label="Theme preview" className="theme-preview-panel">
      <div className="theme-preview-panel__header">
        <div>
          <p className="theme-preview-panel__eyebrow">Live preview</p>
          <h3>{theme.name}</h3>
        </div>
        <div className="theme-preview-panel__header-badges">
          <span className="theme-card__badge">{formatThemeFamilyTitle(theme)}</span>
          <span className="theme-card__badge theme-card__badge--muted">{formatPreviewVariant(theme)}</span>
          <span className="theme-card__badge theme-card__badge--active">
            {isPreviewing ? "Previewing this theme" : "Active preview"}
          </span>
        </div>
      </div>

      <p className="theme-preview-panel__copy">{`Source: ${theme.source_label}`}</p>
      <div className="theme-preview-panel__context-badges">
        <span className="theme-card__badge theme-card__badge--muted">{`Background: ${backgroundThemeName ?? theme.name}`}</span>
        <span className="theme-card__badge theme-card__badge--muted">{`Shelf: ${shelfThemeName ?? theme.name}`}</span>
      </div>

      <div className="theme-preview-panel__mock" style={previewStyle}>
        <div className="theme-preview-panel__brand">
          <div className="theme-preview-panel__brand-mark">OC</div>
          <div>
            <p className="theme-preview-panel__brand-label">Reader surface preview</p>
            <p className="theme-preview-panel__brand-copy">Audiobooks, articles, and narrators in one shelf.</p>
          </div>
        </div>

        <div className="theme-preview-panel__tiles">
          <article className="theme-preview-panel__tile">
            <p className="theme-preview-panel__tile-eyebrow">Library</p>
            <strong>Collections that feel curated, not dumped.</strong>
          </article>
          <article className="theme-preview-panel__tile">
            <p className="theme-preview-panel__tile-eyebrow">Player</p>
            <strong>Docked controls, progress, and current narrator.</strong>
          </article>
          <article className="theme-preview-panel__tile theme-preview-panel__tile--spine">
            <p className="theme-preview-panel__tile-eyebrow">Spine shelf</p>
            <strong>The Left Hand of Darkness - Ursula K. Le Guin</strong>
          </article>
        </div>
      </div>
    </section>
  );
}
