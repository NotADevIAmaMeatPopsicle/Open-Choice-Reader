import type { ThemeProfileRecord } from "../api/types";

type ThemeLayerPickerProps = {
  backgroundOverrideThemeId: string | null;
  onResetToThemeDefaults: () => void;
  onSelectBackground: (themeId: string | null) => void;
  onSelectShelf: (themeId: string | null) => void;
  shelfOverrideThemeId: string | null;
  themes: ThemeProfileRecord[];
};

export function ThemeLayerPicker({
  backgroundOverrideThemeId,
  onResetToThemeDefaults,
  onSelectBackground,
  onSelectShelf,
  shelfOverrideThemeId,
  themes,
}: ThemeLayerPickerProps) {
  return (
    <section className="theme-layer-picker" aria-label="Mix and match theme layers">
      <div className="theme-layer-picker__header">
        <div>
          <p className="theme-card__eyebrow">Advanced controls</p>
          <h4>Mix and match</h4>
        </div>
        <button className="book-card__button book-card__button--ghost" onClick={onResetToThemeDefaults} type="button">
          Reset to theme defaults
        </button>
      </div>
      <div className="theme-layer-picker__grid">
        <label className="library-page__field" htmlFor="background-donor">
          <span>Background donor</span>
          <select
            id="background-donor"
            onChange={(event) => {
              onSelectBackground(event.target.value || null);
            }}
            value={backgroundOverrideThemeId ?? ""}
          >
            <option value="">Use active theme background</option>
            {themes.map((theme) => (
              <option key={theme.id} value={theme.id}>
                {theme.name}
              </option>
            ))}
          </select>
        </label>
        <label className="library-page__field" htmlFor="shelf-donor">
          <span>Shelf donor</span>
          <select
            id="shelf-donor"
            onChange={(event) => {
              onSelectShelf(event.target.value || null);
            }}
            value={shelfOverrideThemeId ?? ""}
          >
            <option value="">Use active theme shelf</option>
            {themes.map((theme) => (
              <option key={theme.id} value={theme.id}>
                {theme.name}
              </option>
            ))}
          </select>
        </label>
      </div>
    </section>
  );
}
