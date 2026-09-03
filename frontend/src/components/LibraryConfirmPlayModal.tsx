import type { DocumentRecord } from "../api/types";

type LibraryConfirmPlayModalProps = {
  document: DocumentRecord;
  onCancel: () => void;
  onConfirm: () => void;
};

export function LibraryConfirmPlayModal({ document, onCancel, onConfirm }: LibraryConfirmPlayModalProps) {
  return (
    <div className="library-page__modal-backdrop" role="presentation">
      <div aria-label="Confirm play" aria-modal="true" className="library-page__modal" role="dialog">
        <div className="library-page__modal-copy">
          <h3>Confirm play</h3>
          <p>Start reading {document.title}?</p>
        </div>
        <div className="library-page__modal-actions">
          <button className="library-page__button" onClick={onConfirm} type="button">
            Confirm play
          </button>
          <button className="library-page__button library-page__button--secondary" onClick={onCancel} type="button">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
