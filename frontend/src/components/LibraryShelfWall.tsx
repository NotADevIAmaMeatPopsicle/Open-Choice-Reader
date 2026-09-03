import type { DocumentRecord } from "../api/types";
import { LibraryCoverTile } from "./LibraryCoverTile";
import { LibrarySpineTile } from "./LibrarySpineTile";

type LibraryShelfWallProps = {
  documents: DocumentRecord[];
  onSelect: (documentId: number) => void;
  selectedDocumentId: number;
  viewMode: "cover" | "spine";
};

export function LibraryShelfWall({ documents, onSelect, selectedDocumentId, viewMode }: LibraryShelfWallProps) {
  return (
    <section aria-label="Library shelf wall" className="library-page__shelf-wall">
      <div className={`library-page__shelf-grid${viewMode === "spine" ? " library-page__shelf-grid--spine" : ""}`}>
        {documents.map((document) =>
          viewMode === "spine" ? (
            <LibrarySpineTile
              document={document}
              isSelected={selectedDocumentId === document.id}
              key={document.id}
              onSelect={onSelect}
            />
          ) : (
            <LibraryCoverTile
              document={document}
              isSelected={selectedDocumentId === document.id}
              key={document.id}
              onSelect={onSelect}
            />
          ),
        )}
      </div>
    </section>
  );
}
