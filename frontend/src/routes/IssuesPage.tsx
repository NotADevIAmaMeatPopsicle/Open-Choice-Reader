import { EmptyState } from "../components/EmptyState";
import { useIssues } from "../hooks/useIssues";

type IssuesPageProps = {
  onNavigate: (pathname: string) => void;
};

export function IssuesPage({ onNavigate }: IssuesPageProps) {
  const { summary } = useIssues();

  return (
    <section aria-label="Issues page" className="utility-page">
      <div className="utility-page__hero">
        <p className="utility-page__eyebrow">Issues</p>
        <h2>Issues</h2>
        <p>Recover from the important problems without dropping into logs or a terminal.</p>
      </div>
      <div className="utility-page__summary-grid">
        <article className="utility-page__summary-card">
          <p className="utility-page__summary-title">Total</p>
          <p className="utility-page__summary-value">{summary.total_count} issues</p>
        </article>
        <article className="utility-page__summary-card">
          <p className="utility-page__summary-title">Errors</p>
          <p className="utility-page__summary-value">{summary.counts_by_severity.error ?? 0}</p>
        </article>
        <article className="utility-page__summary-card">
          <p className="utility-page__summary-title">Warnings</p>
          <p className="utility-page__summary-value">{summary.counts_by_severity.warning ?? 0}</p>
        </article>
      </div>
      {summary.items.length > 0 ? (
        <div className="issues-page__list">
          {summary.items.map((issue) => (
            <article className={`issues-page__card issues-page__row issues-page__card--${issue.severity}`} key={issue.id}>
              <div className="issues-page__row-copy">
                <p className="jobs-page__card-eyebrow">{issue.issue_type.replace(/_/g, " ")}</p>
                <h3>{issue.title}</h3>
                <p>{issue.detail}</p>
              </div>
              <div className="issues-page__row-side">
                <span className={`jobs-page__status jobs-page__status--${issue.severity}`}>{issue.severity}</span>
                <button
                  className="book-card__button book-card__button--ghost"
                  onClick={() => {
                    onNavigate(issue.action_path);
                  }}
                  type="button"
                >
                  {issue.action_label}
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          copy="No issues need attention right now."
          icon="issues"
          title="All clear"
        />
      )}
    </section>
  );
}
