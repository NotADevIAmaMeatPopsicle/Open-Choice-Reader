import { useMemo } from "react";

import type { DocumentRecord } from "../api/types";
import { EmptyState } from "../components/EmptyState";
import { useLibrary } from "../hooks/useLibrary";

type SeriesPageProps = {
  onNavigate: (pathname: string) => void;
  searchTerm: string;
};

type SeriesGroup = {
  name: string;
  books: DocumentRecord[];
};

function parseSeriesTitle(title: string) {
  const match = title.match(/^(.+?)\s+#(\d+)(?:\s*[-:]\s*(.+))?$/);
  if (!match) {
    return null;
  }

  return {
    name: match[1]?.trim() ?? title,
    order: Number(match[2] ?? 0),
  };
}

function groupSeries(documents: DocumentRecord[], searchTerm: string): SeriesGroup[] {
  const groups = new Map<string, Array<DocumentRecord & { seriesOrder: number }>>();

  documents.forEach((document) => {
    const parsed = parseSeriesTitle(document.title);
    if (!parsed) {
      return;
    }

    const searchHaystack = `${parsed.name} ${document.title} ${document.author ?? ""}`.toLowerCase();
    if (searchTerm && !searchHaystack.includes(searchTerm.toLowerCase())) {
      return;
    }

    const entry = groups.get(parsed.name) ?? [];
    entry.push({ ...document, seriesOrder: parsed.order });
    groups.set(parsed.name, entry);
  });

  return [...groups.entries()]
    .map(([name, books]) => ({
      name,
      books: books.sort((left, right) => left.seriesOrder - right.seriesOrder),
    }))
    .filter((group) => group.books.length > 1)
    .sort((left, right) => left.name.localeCompare(right.name));
}

export function SeriesPage({ onNavigate, searchTerm }: SeriesPageProps) {
  const { documents } = useLibrary();
  const groups = useMemo(() => groupSeries(documents, searchTerm), [documents, searchTerm]);

  return (
    <section aria-label="Series page" className="utility-page">
      <div className="utility-page__hero">
        <p className="utility-page__eyebrow">Series</p>
        <h2>Series</h2>
        <p>Grouped multi-book runs stay together here so you can move through a sequence without hunting through the whole shelf.</p>
      </div>
      {groups.length > 0 ? (
        <div className="series-page__grid">
          {groups.map((group) => (
            <article className="series-page__card" key={group.name}>
              <div className="series-page__card-header">
                <div>
                  <h3>{group.name}</h3>
                  <p>{group.books.length} books</p>
                </div>
              </div>
              <ul className="series-page__list">
                {group.books.map((book) => (
                  <li className="series-page__list-item" key={book.id}>
                    <div>
                      <p className="series-page__book-title">{book.title}</p>
                      <p className="series-page__book-meta">{book.author ?? book.format.toUpperCase()}</p>
                    </div>
                    <button
                      className="book-card__button book-card__button--ghost"
                      onClick={() => {
                        onNavigate(`/books/${book.id}`);
                      }}
                      type="button"
                    >
                      Open {book.title}
                    </button>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          copy={searchTerm ? "No matching multi-book series yet." : "No grouped multi-book series yet."}
          icon="series"
          title={searchTerm ? "Nothing matches that search" : "No series yet"}
        />
      )}
    </section>
  );
}
