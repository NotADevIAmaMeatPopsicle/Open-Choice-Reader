import type { ThemeProfileRecord } from "../api/types";
import { formatThemeFamilyTitle } from "../theme/showcaseThemePreview";

type ThemeCardProps = {
  isActive: boolean;
  isApplying: boolean;
  isDeleting?: boolean;
  isPreviewing: boolean;
  onApply: () => void;
  onDelete?: () => void;
  onPreview: () => void;
  theme: ThemeProfileRecord;
};

export function ThemeCard({
  isActive,
  isApplying,
  isDeleting = false,
  isPreviewing,
  onApply,
  onDelete,
  onPreview,
  theme,
}: ThemeCardProps) {
  return (
    <article className={`theme-card${isActive ? " theme-card--active" : ""}${isPreviewing ? " theme-card--previewing" : ""}`}>
      <div className="theme-card__layout">
        <div className="theme-card__content">
          <div className="theme-card__header">
            <div>
              <p className="theme-card__eyebrow">{formatThemeFamilyTitle(theme)}</p>
              <h3>{theme.name}</h3>
            </div>
          </div>

          <p className="theme-card__copy">{theme.description ?? "No description available for this theme yet."}</p>

          <div className="theme-card__swatches" aria-hidden="true">
            {Object.entries(theme.tokens)
              .slice(0, 4)
              .map(([tokenName, tokenValue]) => (
                <span className="theme-card__swatch" key={tokenName} style={{ background: tokenValue }} title={tokenName} />
              ))}
          </div>
        </div>

        <div className="theme-card__actions">
          <button className="theme-card__action-button theme-card__action-button--ghost" onClick={onPreview} type="button">
            Preview
          </button>
          <button className="theme-card__action-button" disabled={isActive || isApplying} onClick={onApply} type="button">
            {isApplying ? "Applying..." : "Apply"}
          </button>
          {!theme.is_builtin && onDelete ? (
            <button
              className="theme-card__action-button theme-card__action-button--ghost"
              disabled={isActive || isDeleting}
              onClick={onDelete}
              type="button"
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </button>
          ) : null}
        </div>
      </div>
    </article>
  );
}
