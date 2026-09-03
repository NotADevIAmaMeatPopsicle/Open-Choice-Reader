import type { DocumentSectionRecord } from "../api/types";

type ChapterListProps = {
  currentChunkIndex?: number | null;
  isStartingPlayback: boolean;
  onReadFromSection: (sectionId: number) => void;
  sections: DocumentSectionRecord[];
};

function buildSectionLabel(section: DocumentSectionRecord) {
  return section.title?.trim() || `Section ${section.position + 1}`;
}

function isCurrentSection(section: DocumentSectionRecord, currentChunkIndex: number | null | undefined) {
  if (currentChunkIndex == null) {
    return false;
  }

  return (
    currentChunkIndex >= section.chunk_start_index &&
    currentChunkIndex < section.chunk_start_index + Math.max(section.chunk_count, 1)
  );
}

export function ChapterList({
  currentChunkIndex,
  isStartingPlayback,
  onReadFromSection,
  sections,
}: ChapterListProps) {
  return (
    <section className="chapter-list" aria-label="Chapters">
      <div className="chapter-list__header">
        <h3>Chapters</h3>
        <p>Choose where live reading should begin from the player.</p>
      </div>
      <ol className="chapter-list__items">
        {sections.map((section) => {
          const sectionLabel = buildSectionLabel(section);
          const current = isCurrentSection(section, currentChunkIndex);

          return (
            <li className="chapter-list__item" key={section.id}>
              <div className="chapter-list__copy">
                <div className="chapter-list__title-row">
                  <h4>{sectionLabel}</h4>
                  {current ? <span className="chapter-list__badge">Current</span> : null}
                </div>
                <p>{section.preview_text || "No preview available yet."}</p>
                <p className="chapter-list__meta">
                  Starts at chunk {section.chunk_start_index + 1} · {section.chunk_count} chunk
                  {section.chunk_count === 1 ? "" : "s"}
                </p>
              </div>
              <button
                className="book-card__button book-card__button--ghost"
                disabled={isStartingPlayback}
                onClick={() => {
                  onReadFromSection(section.id);
                }}
                type="button"
              >
                {isStartingPlayback ? "Starting..." : `Read from ${sectionLabel}`}
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
