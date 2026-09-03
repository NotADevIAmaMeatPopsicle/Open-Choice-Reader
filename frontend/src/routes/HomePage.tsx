import { useEffect, useState } from "react";

import { createPlaybackSession, listInboxCandidates } from "../api/client";
import { ShelfRow } from "../components/ShelfRow";
import { useHomeSummary } from "../hooks/useHomeSummary";
import { useIssues } from "../hooks/useIssues";
import { setActivePlaybackSession } from "../hooks/usePlayer";

type HomePageProps = {
  onNavigate: (pathname: string) => void;
  searchTerm: string;
};

function matchesSearch(searchTerm: string, candidate: string) {
  return candidate.toLowerCase().includes(searchTerm.toLowerCase());
}

export function HomePage({ onNavigate, searchTerm }: HomePageProps) {
  const { summary, isLoading } = useHomeSummary();
  const { summary: issueSummary } = useIssues();
  const [inboxCount, setInboxCount] = useState(0);

  const continueReading = summary.continue_reading.filter((document) =>
    matchesSearch(searchTerm, `${document.title} ${document.author ?? ""} ${document.summary ?? ""}`),
  );
  const recentDocuments = summary.recent_documents.filter((document) =>
    matchesSearch(searchTerm, `${document.title} ${document.author ?? ""} ${document.summary ?? ""}`),
  );

  useEffect(() => {
    let cancelled = false;

    const loadInbox = async () => {
      try {
        const candidates = await listInboxCandidates();
        if (!cancelled) {
          setInboxCount(candidates.length);
        }
      } catch {
        if (!cancelled) {
          setInboxCount(0);
        }
      }
    };

    void loadInbox();

    return () => {
      cancelled = true;
    };
  }, []);

  const startReading = async (documentId: number) => {
    const session = await createPlaybackSession({ document_id: documentId });
    setActivePlaybackSession(session);
    onNavigate(`/reader/${session.id}`);
  };

  const issueCopy =
    issueSummary.total_count === 1
      ? "1 issue needs attention"
      : `${issueSummary.total_count} issues need attention`;
  const inboxCopy =
    inboxCount === 1 ? "1 file waiting in the inbox" : `${inboxCount} files waiting in the inbox`;

  return (
    <section aria-label="Home page" className="utility-page">
      <div className="utility-page__hero">
        <p className="utility-page__eyebrow">Home</p>
        <h2>Home</h2>
        <p>{isLoading ? "Loading your listening shelves..." : "Pick up where you left off or browse new imports."}</p>
      </div>
      <div className="utility-page__summary-grid">
        <article className="utility-page__summary-card">
          <p className="utility-page__summary-title">Operations</p>
          <p className="utility-page__summary-value">{issueCopy}</p>
          <p className="utility-page__summary-copy">Failed exports, missing sources, and engine warnings land here first.</p>
          <button
            className="book-card__button"
            onClick={() => {
              onNavigate("/issues");
            }}
            type="button"
          >
            Open issues
          </button>
        </article>
        <article className="utility-page__summary-card">
          <p className="utility-page__summary-title">Inbox</p>
          <p className="utility-page__summary-value">{inboxCopy}</p>
          <p className="utility-page__summary-copy">The server can watch a drop folder so imports can land without using the host shell.</p>
          <button
            className="book-card__button book-card__button--ghost"
            onClick={() => {
              onNavigate("/");
            }}
            type="button"
          >
            Review inbox
          </button>
        </article>
      </div>
      <ShelfRow
        documents={continueReading}
        emptyMessage="Nothing is in progress yet."
        onOpenBook={(documentId) => {
          onNavigate(`/books/${documentId}`);
        }}
        onReadNow={(documentId) => {
          void startReading(documentId);
        }}
        title="Continue reading"
      />
      <ShelfRow
        documents={recentDocuments}
        emptyMessage="No recent imports yet."
        onOpenBook={(documentId) => {
          onNavigate(`/books/${documentId}`);
        }}
        title="Recent imports"
      />
    </section>
  );
}
