import type { DocumentRecord } from "../api/types";
import { BookCard } from "./BookCard";

type ShelfRowProps = {
  documents: DocumentRecord[];
  emptyMessage: string;
  onOpenBook: (documentId: number) => void;
  onReadNow?: (documentId: number) => void;
  title: string;
};

export function ShelfRow({ documents, emptyMessage, onOpenBook, onReadNow, title }: ShelfRowProps) {
  return (
    <section className="shelf-row" aria-label={title}>
      <div className="shelf-row__header">
        <h2>{title}</h2>
      </div>
      {documents.length > 0 ? (
        <div className="shelf-row__grid">
          {documents.map((document) => (
            <BookCard
              document={document}
              key={document.id}
              onReadNow={onReadNow}
              onViewDetails={onOpenBook}
            />
          ))}
        </div>
      ) : (
        <p className="shelf-row__empty">{emptyMessage}</p>
      )}
    </section>
  );
}
