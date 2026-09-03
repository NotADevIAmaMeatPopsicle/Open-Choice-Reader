import type { InboxCandidateRecord } from "../api/types";

type LibraryImportPanelProps = {
  activePath: string | null;
  candidates: InboxCandidateRecord[];
  isLoading: boolean;
  notice: string | null;
  onCandidateAction: (candidate: InboxCandidateRecord) => void;
  onRefresh: () => void;
};

export function LibraryImportPanel({
  activePath,
  candidates,
  isLoading,
  notice,
  onCandidateAction,
  onRefresh,
}: LibraryImportPanelProps) {
  return (
    <div className="library-page__inbox-panel">
      <div className="library-page__inbox-header">
        <div>
          <p className="library-page__panel-title">Server inbox</p>
          <p className="library-page__panel-copy">Import from the watched folder or refresh a title whose source file changed.</p>
        </div>
        <button className="book-card__button book-card__button--ghost" onClick={onRefresh} type="button">
          Refresh inbox
        </button>
      </div>
      {isLoading ? <p className="library-page__panel-copy">Scanning server inbox...</p> : null}
      {notice ? <p className="library-page__panel-copy">{notice}</p> : null}
      {candidates.length > 0 ? (
        <ul className="library-page__inbox-list">
          {candidates.map((candidate) => (
            <li className="library-page__inbox-item" key={candidate.path}>
              <div>
                <p className="series-page__book-title">{candidate.name}</p>
                <p className="series-page__book-meta">
                  {candidate.format.toUpperCase()} · {candidate.document_id ? "Already imported" : "Ready to import"}
                </p>
              </div>
              <button
                className="book-card__button"
                disabled={activePath === candidate.path}
                onClick={() => {
                  onCandidateAction(candidate);
                }}
                type="button"
              >
                {candidate.document_id ? "Refresh imported book" : "Import from inbox"}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {!isLoading && candidates.length === 0 ? (
        <p className="library-page__panel-copy">The watched inbox is empty right now.</p>
      ) : null}
    </div>
  );
}
