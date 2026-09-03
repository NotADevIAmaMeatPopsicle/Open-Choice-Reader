import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

import {
  browseGutenberg,
  browseStandardEbooks,
  importCatalogItem,
  importDocument,
  importDocumentFromUrl,
  importPastedText,
  searchGutenberg,
  searchOpenLibrary,
  searchStandardEbooks,
} from "../api/client";
import type { CatalogResultRecord } from "../api/types";

type DiscoverPageProps = {
  onNavigate: (pathname: string) => void;
};

type DiscoverMode = "catalogs" | "upload" | "url" | "text";
type CatalogSource = "gutenberg" | "standard_ebooks" | "openlibrary";

const CATALOG_SOURCE_LABELS: Record<CatalogSource, string> = {
  gutenberg: "Project Gutenberg",
  openlibrary: "Open Library / Internet Archive",
  standard_ebooks: "Standard Ebooks",
};

export function DiscoverPage({ onNavigate }: DiscoverPageProps) {
  const [mode, setMode] = useState<DiscoverMode>("catalogs");
  const [catalogSource, setCatalogSource] = useState<CatalogSource>("gutenberg");
  const [catalogQuery, setCatalogQuery] = useState("");
  const [catalogResults, setCatalogResults] = useState<CatalogResultRecord[]>([]);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [isLoadingCatalogs, setIsLoadingCatalogs] = useState(false);
  const [importingCatalogId, setImportingCatalogId] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [urlValue, setUrlValue] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);
  const [isImportingUrl, setIsImportingUrl] = useState(false);
  const [textTitle, setTextTitle] = useState("");
  const [textAuthor, setTextAuthor] = useState("");
  const [textSourceUrl, setTextSourceUrl] = useState("");
  const [textBody, setTextBody] = useState("");
  const [textError, setTextError] = useState<string | null>(null);
  const [isImportingText, setIsImportingText] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (catalogSource === "openlibrary") {
      setCatalogResults([]);
      setCatalogError(null);
      return;
    }

    void loadCatalogResults(catalogSource);
  }, [catalogSource]);

  async function loadCatalogResults(source: CatalogSource, query?: string) {
    setIsLoadingCatalogs(true);
    setCatalogError(null);

    try {
      let results: CatalogResultRecord[] = [];

      if (source === "gutenberg") {
        results = query?.trim() ? await searchGutenberg(query.trim()) : await browseGutenberg();
      } else if (source === "standard_ebooks") {
        results = query?.trim() ? await searchStandardEbooks(query.trim()) : await browseStandardEbooks();
      } else if (query?.trim()) {
        results = await searchOpenLibrary(query.trim());
      }

      setCatalogResults(results);
    } catch (error) {
      setCatalogError(error instanceof Error ? error.message : "Unable to load catalog results");
      setCatalogResults([]);
    } finally {
      setIsLoadingCatalogs(false);
    }
  }

  const handleCatalogSearch = async (event?: FormEvent) => {
    event?.preventDefault();
    await loadCatalogResults(catalogSource, catalogQuery);
  };

  const handleImportCatalogResult = async (result: CatalogResultRecord) => {
    setImportingCatalogId(result.id);
    setCatalogError(null);

    try {
      const document = await importCatalogItem({
        source: result.source,
        catalog_id: result.id,
      });
      onNavigate(`/books/${document.id}`);
    } catch (error) {
      setCatalogError(error instanceof Error ? error.message : "Unable to import catalog result");
    } finally {
      setImportingCatalogId(null);
    }
  };

  const handleUploadChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      const document = await importDocument(file);
      onNavigate(`/books/${document.id}`);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Unable to import file");
    } finally {
      event.target.value = "";
      setIsUploading(false);
    }
  };

  const handleUrlImport = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsImportingUrl(true);
    setUrlError(null);

    try {
      const document = await importDocumentFromUrl(urlValue.trim());
      onNavigate(`/books/${document.id}`);
    } catch (error) {
      setUrlError(error instanceof Error ? error.message : "Unable to import URL");
    } finally {
      setIsImportingUrl(false);
    }
  };

  const handleTextImport = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsImportingText(true);
    setTextError(null);

    try {
      const document = await importPastedText({
        title: textTitle.trim(),
        author: textAuthor.trim() || undefined,
        source_url: textSourceUrl.trim() || undefined,
        body: textBody,
      });
      onNavigate(`/books/${document.id}`);
    } catch (error) {
      setTextError(error instanceof Error ? error.message : "Unable to import pasted text");
    } finally {
      setIsImportingText(false);
    }
  };

  return (
    <section aria-label="Discover page" className="library-page discover-page">
      <div className="library-page__hero">
        <div className="library-page__title-block">
          <p className="library-page__eyebrow">Discover</p>
          <h2>Discover</h2>
          <p>Bring new books, articles, direct document links, and saved clippings into Open Choice Reader from one place.</p>
        </div>
      </div>

      <div className="discover-page__mode-tabs" role="tablist" aria-label="Acquisition modes">
        {[
          { id: "catalogs", label: "Catalogs" },
          { id: "upload", label: "Upload file" },
          { id: "url", label: "From URL" },
          { id: "text", label: "Paste text" },
        ].map((tab) => (
          <button
            aria-pressed={mode === tab.id}
            className={`discover-page__mode-tab${mode === tab.id ? " discover-page__mode-tab--active" : ""}`}
            key={tab.id}
            onClick={() => {
              setMode(tab.id as DiscoverMode);
            }}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      {mode === "catalogs" ? (
        <section className="voices-page__panel" aria-label="Catalog discovery">
          <div className="voices-page__section-header">
            <div>
              <h3>Public-domain catalogs</h3>
              <p>Search or browse public-domain shelves, then import directly into your library.</p>
            </div>
          </div>

          <div className="discover-page__source-tabs" role="tablist" aria-label="Catalog sources">
            {(Object.keys(CATALOG_SOURCE_LABELS) as CatalogSource[]).map((source) => (
              <button
                aria-pressed={catalogSource === source}
                className={`discover-page__source-tab${catalogSource === source ? " discover-page__source-tab--active" : ""}`}
                key={source}
                onClick={() => {
                  setCatalogSource(source);
                }}
                type="button"
              >
                {CATALOG_SOURCE_LABELS[source]}
              </button>
            ))}
          </div>

          <form className="discover-page__search-row" onSubmit={(event) => void handleCatalogSearch(event)}>
            <label className="library-page__field">
              <span className="sr-only">Catalog search</span>
              <input
                aria-label="Catalog search"
                onChange={(event) => {
                  setCatalogQuery(event.target.value);
                }}
                placeholder={
                  catalogSource === "openlibrary"
                    ? "Search Open Library and Internet Archive"
                    : `Search ${CATALOG_SOURCE_LABELS[catalogSource]}`
                }
                type="search"
                value={catalogQuery}
              />
            </label>
            <button className="library-page__button" type="submit">
              Search
            </button>
          </form>

          {catalogSource === "openlibrary" && !catalogQuery.trim() ? (
            <p className="library-page__panel-copy">Open Library search needs a title, author, or subject query before results can load.</p>
          ) : null}
          {isLoadingCatalogs ? <p className="library-page__panel-copy">Loading catalog results...</p> : null}
          {catalogError ? (
            <p className="library-page__alert" role="alert">
              {catalogError}
            </p>
          ) : null}

          {catalogResults.length > 0 ? (
            <div className="discover-page__results-grid">
              {catalogResults.map((result) => (
                <article className="discover-page__result-card" key={`${result.source}:${result.id}`}>
                  {result.cover_url ? (
                    <img alt="" className="discover-page__result-cover" src={result.cover_url} />
                  ) : (
                    <div className="discover-page__result-cover discover-page__result-cover--empty">No cover</div>
                  )}
                  <div className="discover-page__result-body">
                    <p className="library-page__eyebrow">{result.source_name}</p>
                    <h4>{result.title}</h4>
                    <p className="discover-page__result-meta">{result.author ?? "Unknown author"}</p>
                    <p className="discover-page__result-summary">{result.summary ?? "No description available yet."}</p>
                    <button
                      className="library-page__button"
                      disabled={!result.importable || importingCatalogId === result.id}
                      onClick={() => {
                        void handleImportCatalogResult(result);
                      }}
                      type="button"
                    >
                      {importingCatalogId === result.id ? "Importing..." : `Import ${result.title}`}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      {mode === "upload" ? (
        <section className="voices-page__panel" aria-label="Upload file import">
          <div className="voices-page__section-header">
            <div>
              <h3>Upload a document</h3>
              <p>Supported formats: EPUB, PDF, TXT, Markdown, and HTML snapshots.</p>
            </div>
          </div>
          <input
            accept=".epub,.pdf,.txt,.md,.markdown,.html"
            aria-label="Upload document file"
            onChange={(event) => {
              void handleUploadChange(event);
            }}
            ref={fileInputRef}
            style={{ display: "none" }}
            type="file"
          />
          <div className="discover-page__upload-panel">
            <p className="library-page__panel-copy">Drop a file into the server inbox or choose one from this device.</p>
            <button className="library-page__button" onClick={() => fileInputRef.current?.click()} type="button">
              {isUploading ? "Importing..." : "Choose file"}
            </button>
          </div>
          {uploadError ? (
            <p className="library-page__alert" role="alert">
              {uploadError}
            </p>
          ) : null}
        </section>
      ) : null}

      {mode === "url" ? (
        <section className="voices-page__panel" aria-label="URL import">
          <div className="voices-page__section-header">
            <div>
              <h3>Import from URL</h3>
              <p>Paste a raw document link or a normal article page. The server will download it once and store a stable snapshot.</p>
            </div>
          </div>
          <form className="discover-page__stack" onSubmit={(event) => void handleUrlImport(event)}>
            <label className="library-page__field">
              <span>Document or article URL</span>
              <input
                aria-label="Document or article URL"
                onChange={(event) => {
                  setUrlValue(event.target.value);
                }}
                placeholder="https://example.com/article-or-file"
                type="url"
                value={urlValue}
              />
            </label>
            <button className="library-page__button" disabled={!urlValue.trim() || isImportingUrl} type="submit">
              {isImportingUrl ? "Importing..." : "Import from URL"}
            </button>
          </form>
          {urlError ? (
            <p className="library-page__alert" role="alert">
              {urlError}
            </p>
          ) : null}
        </section>
      ) : null}

      {mode === "text" ? (
        <section className="voices-page__panel" aria-label="Paste text import">
          <div className="voices-page__section-header">
            <div>
              <h3>Paste text</h3>
              <p>Turn copied notes, article text, or snippets into a first-class library item.</p>
            </div>
          </div>
          <form className="discover-page__stack" onSubmit={(event) => void handleTextImport(event)}>
            <label className="library-page__field">
              <span>Title</span>
              <input
                aria-label="Title"
                onChange={(event) => {
                  setTextTitle(event.target.value);
                }}
                type="text"
                value={textTitle}
              />
            </label>
            <label className="library-page__field">
              <span>Author</span>
              <input
                aria-label="Author"
                onChange={(event) => {
                  setTextAuthor(event.target.value);
                }}
                type="text"
                value={textAuthor}
              />
            </label>
            <label className="library-page__field">
              <span>Source URL</span>
              <input
                aria-label="Source URL"
                onChange={(event) => {
                  setTextSourceUrl(event.target.value);
                }}
                type="url"
                value={textSourceUrl}
              />
            </label>
            <label className="library-page__field">
              <span>Body text</span>
              <textarea
                aria-label="Body text"
                onChange={(event) => {
                  setTextBody(event.target.value);
                }}
                rows={10}
                value={textBody}
              />
            </label>
            <button className="library-page__button" disabled={!textTitle.trim() || !textBody.trim() || isImportingText} type="submit">
              {isImportingText ? "Importing..." : "Import pasted text"}
            </button>
          </form>
          {textError ? (
            <p className="library-page__alert" role="alert">
              {textError}
            </p>
          ) : null}
        </section>
      ) : null}
    </section>
  );
}
