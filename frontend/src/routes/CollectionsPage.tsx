import { useMemo, useState } from "react";

import { EmptyState } from "../components/EmptyState";
import { useCollections } from "../hooks/useCollections";
import { useLibrary } from "../hooks/useLibrary";

type CollectionsPageProps = {
  onNavigate: (pathname: string) => void;
};

export function CollectionsPage({ onNavigate }: CollectionsPageProps) {
  const { collections, createCollection, addDocument, removeDocument } = useCollections();
  const { documents } = useLibrary();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedDocuments, setSelectedDocuments] = useState<Record<number, string>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const documentOptions = useMemo(
    () =>
      documents.map((document) => ({
        id: document.id,
        label: document.author
          ? `${document.title} by ${document.author}`
          : `${document.title} (${document.format.toUpperCase()})`,
      })),
    [documents],
  );

  const handleCreateCollection = async () => {
    if (!name.trim()) {
      return;
    }

    setErrorMessage(null);

    try {
      await createCollection(name.trim(), description.trim());
      setName("");
      setDescription("");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create collection");
    }
  };

  const handleAddDocument = async (collectionId: number) => {
    const nextDocumentId = Number(selectedDocuments[collectionId] ?? "0");
    if (!nextDocumentId) {
      return;
    }

    setErrorMessage(null);

    try {
      await addDocument(collectionId, nextDocumentId);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to update collection");
    }
  };

  return (
    <section aria-label="Collections page" className="utility-page">
      <div className="utility-page__hero">
        <p className="utility-page__eyebrow">Collections</p>
        <h2>Collections</h2>
        <p>Build manual shelves for favorites, works in progress, or anything worth revisiting later.</p>
      </div>
      <div className="collections-page__composer">
        <label className="library-page__field">
          <span>Collection name</span>
          <input
            onChange={(event) => {
              setName(event.target.value);
            }}
            type="text"
            value={name}
          />
        </label>
        <label className="library-page__field">
          <span>Description</span>
          <input
            onChange={(event) => {
              setDescription(event.target.value);
            }}
            type="text"
            value={description}
          />
        </label>
        <button className="book-card__button" onClick={() => void handleCreateCollection()} type="button">
          Create collection
        </button>
      </div>
      {errorMessage ? (
        <p className="library-page__alert" role="alert">
          {errorMessage}
        </p>
      ) : null}
      {collections.length > 0 ? (
        <div className="collections-page__grid">
          {collections.map((collection) => (
            <article className="series-page__card" key={collection.id}>
              <div className="series-page__card-header">
                <div>
                  <h3>{collection.name}</h3>
                  <p>{collection.description ?? "Manual shelf"}</p>
                </div>
                <span className="chapter-list__badge">{collection.document_count} books</span>
              </div>
              <div className="collections-page__controls">
                <label className="library-page__field">
                  <span>Add book to {collection.name}</span>
                  <select
                    aria-label={`Add book to ${collection.name}`}
                    onChange={(event) => {
                      setSelectedDocuments((current) => ({
                        ...current,
                        [collection.id]: event.target.value,
                      }));
                    }}
                    value={selectedDocuments[collection.id] ?? ""}
                  >
                    <option value="">Select a book</option>
                    {documentOptions.map((documentOption) => (
                      <option key={documentOption.id} value={documentOption.id}>
                        {documentOption.label}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="book-card__button book-card__button--ghost"
                  onClick={() => void handleAddDocument(collection.id)}
                  type="button"
                >
                  Add to {collection.name}
                </button>
              </div>
              {collection.documents.length > 0 ? (
                <ul className="collections-page__documents">
                  {collection.documents.map((document) => (
                    <li className="collections-page__document" key={document.id}>
                      <div>
                        <p className="series-page__book-title">{document.title}</p>
                        <p className="series-page__book-meta">
                          {document.author ?? "Unknown author"} · {Math.round(document.progress_percent)}% complete
                        </p>
                      </div>
                      <div className="book-card__actions">
                        <button
                          className="book-card__button book-card__button--ghost"
                          onClick={() => {
                            onNavigate(`/books/${document.id}`);
                          }}
                          type="button"
                        >
                          View details
                        </button>
                        <button
                          className="book-card__button book-card__button--ghost"
                          onClick={() => {
                            void removeDocument(collection.id, document.id);
                          }}
                          type="button"
                        >
                          Remove
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="library-page__panel-copy">No books have been added to this collection yet.</p>
              )}
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          copy="Create the first manual shelf to pin favorites or nightly listening queues."
          icon="collections"
          title="No collections yet"
        />
      )}
    </section>
  );
}
