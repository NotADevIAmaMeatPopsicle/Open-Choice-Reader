import { useEffect, useState } from "react";

import {
  addDocumentToCollection as addCollectionDocument,
  createCollection as createCollectionRecord,
  listCollections,
  removeDocumentFromCollection as removeCollectionDocument,
} from "../api/client";
import type { CollectionRecord } from "../api/types";

function sortCollections(collections: CollectionRecord[]) {
  return [...collections].sort((left, right) => left.name.localeCompare(right.name));
}

export function useCollections() {
  const [collections, setCollections] = useState<CollectionRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  async function refresh() {
    setIsLoading(true);

    try {
      setCollections(sortCollections(await listCollections()));
    } catch {
      setCollections([]);
    } finally {
      setIsLoading(false);
    }
  }

  async function createCollection(name: string, description: string) {
    const collection = await createCollectionRecord({ name, description });
    setCollections((current) => sortCollections([...current, collection]));
    return collection;
  }

  async function addDocument(collectionId: number, documentId: number) {
    const collection = await addCollectionDocument(collectionId, documentId);
    setCollections((current) =>
      sortCollections(current.map((entry) => (entry.id === collection.id ? collection : entry))),
    );
    return collection;
  }

  async function removeDocument(collectionId: number, documentId: number) {
    await removeCollectionDocument(collectionId, documentId);
    setCollections((current) =>
      current.map((entry) =>
        entry.id === collectionId
          ? {
              ...entry,
              document_count: Math.max(0, entry.document_count - 1),
              documents: entry.documents.filter((document) => document.id !== documentId),
            }
          : entry,
      ),
    );
  }

  useEffect(() => {
    void refresh();
  }, []);

  return {
    collections,
    isLoading,
    refresh,
    createCollection,
    addDocument,
    removeDocument,
  };
}
