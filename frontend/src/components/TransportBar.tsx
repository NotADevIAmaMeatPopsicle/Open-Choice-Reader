type TransportBarProps = {
  currentChunkIndex: number;
  isPlaying: boolean;
  onAdvanceProgress: () => void;
  onProgressChange: (nextChunkIndex: number) => void;
  onSeekRelative: (seconds: number) => void;
  onTogglePlayback: () => void;
  totalChunks: number;
};

export function TransportBar({
  currentChunkIndex,
  isPlaying,
  onAdvanceProgress,
  onProgressChange,
  onSeekRelative,
  onTogglePlayback,
  totalChunks,
}: TransportBarProps) {
  const progressPercent = totalChunks > 0 ? Math.round(((currentChunkIndex + 1) / totalChunks) * 100) : 0;
  const canAdvanceProgress = totalChunks <= 0 || currentChunkIndex < totalChunks - 1;

  return (
    <div aria-label="Transport controls" className="transport-bar">
      <div className="transport-bar__copy">
        <p className="transport-bar__title">Transport controls</p>
        <p className="transport-bar__meta">
          Chunk {currentChunkIndex + 1}
          {totalChunks > 0 ? ` of ${totalChunks}` : ""}
        </p>
        <p className="transport-bar__meta">{progressPercent}% complete</p>
        <label className="transport-bar__progress">
          <span className="sr-only">Document progress</span>
          <input
            aria-label="Document progress"
            max={Math.max(totalChunks - 1, 0)}
            min="0"
            onChange={(event) => {
              onProgressChange(Number(event.target.value));
            }}
            step="1"
            type="range"
            value={currentChunkIndex}
          />
        </label>
      </div>
      <div className="transport-bar__actions">
        <button className="book-card__button book-card__button--ghost" onClick={() => onSeekRelative(-30)} type="button">
          Back 30s
        </button>
        <button className="book-card__button book-card__button--ghost" onClick={() => onSeekRelative(-5)} type="button">
          Back 5s
        </button>
        <button
          className="book-card__button book-card__button--ghost"
          disabled={!canAdvanceProgress}
          onClick={onAdvanceProgress}
          type="button"
        >
          Next chunk
        </button>
        <button
          className="book-card__button"
          onClick={onTogglePlayback}
          type="button"
        >
          {isPlaying ? "Pause" : "Play"}
        </button>
      </div>
    </div>
  );
}
