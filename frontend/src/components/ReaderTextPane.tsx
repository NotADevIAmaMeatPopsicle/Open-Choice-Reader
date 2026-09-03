import type { PlaybackSectionChunkRecord } from "../api/types";

type ReaderTextPaneProps = {
  currentChunkIndex: number;
  currentSectionTitle?: string | null;
  sectionChunks: PlaybackSectionChunkRecord[];
};

export function ReaderTextPane({
  currentChunkIndex,
  currentSectionTitle,
  sectionChunks,
}: ReaderTextPaneProps) {
  return (
    <section className="reader-text-pane" aria-label="Current reading text">
      <div className="reader-text-pane__header">
        <div>
          <p className="reader-text-pane__eyebrow">Live text</p>
          <h3>{currentSectionTitle ?? "Current section"}</h3>
        </div>
        <p className="reader-text-pane__active-copy">Current chunk index: {currentChunkIndex}</p>
      </div>
      <ol className="reader-text-pane__chunks">
        {sectionChunks.map((chunk) => (
          <li
            aria-current={chunk.is_current ? "true" : undefined}
            className={`reader-text-pane__chunk${chunk.is_current ? " reader-text-pane__chunk--active" : ""}`}
            key={`${chunk.chunk_index}-${chunk.text}`}
          >
            <p>{chunk.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
