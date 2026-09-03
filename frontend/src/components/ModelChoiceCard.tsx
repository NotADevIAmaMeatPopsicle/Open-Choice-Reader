type ModelChoiceCardProps = {
  availabilityDetail: string;
  displayName: string;
  isSelected: boolean;
  modelName: string;
  onSelect: () => void;
  usageHint: string;
};

export function ModelChoiceCard({
  availabilityDetail,
  displayName,
  isSelected,
  modelName,
  onSelect,
  usageHint,
}: ModelChoiceCardProps) {
  return (
    <article className={`model-choice-card${isSelected ? " model-choice-card--selected" : ""}`}>
      <div className="model-choice-card__header">
        <div>
          <p className="model-choice-card__title">{displayName}</p>
          <p className="model-choice-card__model">{modelName}</p>
        </div>
        <span className="model-choice-card__badge">{isSelected ? "Selected" : "Available"}</span>
      </div>
      <p className="model-choice-card__detail">{usageHint}</p>
      <p className="model-choice-card__detail">{availabilityDetail}</p>
      <button
        className={isSelected ? "book-card__button" : "book-card__button book-card__button--ghost"}
        onClick={onSelect}
        type="button"
      >
        {isSelected ? "Selected premium model" : `Use ${displayName}`}
      </button>
    </article>
  );
}
