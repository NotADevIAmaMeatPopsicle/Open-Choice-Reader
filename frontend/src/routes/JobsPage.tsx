import { ArtifactList } from "../components/ArtifactList";
import { useJobs } from "../hooks/useJobs";
import { useLibrary } from "../hooks/useLibrary";

type QueueBucket =
  | "cancel_requested"
  | "canceled"
  | "completed"
  | "failed"
  | "processing"
  | "queued"
  | "unknown";

function getQueueBucket(status: string): QueueBucket {
  switch (status) {
    case "cancel_requested":
      return "cancel_requested";
    case "canceled":
      return "canceled";
    case "completed":
      return "completed";
    case "failed":
      return "failed";
    case "processing":
      return "processing";
    case "queued":
      return "queued";
    default:
      return "unknown";
  }
}

function getQueueLabel(bucket: QueueBucket, status: string) {
  switch (bucket) {
    case "cancel_requested":
      return "Stopping export";
    case "canceled":
      return "Canceled";
    case "completed":
      return "Ready to download";
    case "failed":
      return "Needs attention";
    case "processing":
      return "Rendering now";
    case "unknown":
      return `Unexpected status: ${status}`;
    default:
      return "Queued up";
  }
}

function getQueueHint(bucket: QueueBucket) {
  switch (bucket) {
    case "cancel_requested":
      return "The worker will stop after its current safe checkpoint.";
    case "canceled":
      return "This export was canceled before it finished.";
    case "completed":
      return "Finished exports stay here until the artifacts are downloaded.";
    case "failed":
      return "Open the failure detail before re-queueing the export.";
    case "processing":
      return "This render is actively working through the audiobook export.";
    case "unknown":
      return "This export reported a new or unrecognized backend status.";
    default:
      return "This export is waiting for the worker to pick it up.";
  }
}

export function JobsPage() {
  const { actionError, cancelJob, error, isLoading, isMutatingJobId, jobs, retryJob } = useJobs();
  const { documents } = useLibrary();
  const documentTitles = new Map(documents.map((document) => [document.id, document.title]));
  const summaryCounts = jobs.reduce<Record<QueueBucket, number>>(
    (counts, job) => {
      const bucket = getQueueBucket(job.status);
      counts[bucket] += 1;
      return counts;
    },
    {
      queued: 0,
      processing: 0,
      completed: 0,
      failed: 0,
      canceled: 0,
      cancel_requested: 0,
      unknown: 0,
    },
  );

  return (
    <section aria-label="Jobs page" className="library-page jobs-page">
      <div className="jobs-page__header">
        <div className="library-page__title-block">
          <h2>Export Queue</h2>
          <p>Check what is queued, what finished cleanly, and what needs a retry.</p>
        </div>
        <p className="library-page__summary jobs-page__summary">{jobs.length} exports tracked</p>
      </div>
      {isLoading && jobs.length === 0 ? <p>Loading jobs...</p> : null}
      {error ? (
        <p role="alert" style={{ margin: 0, color: "#ffb4ab" }}>
          {error}
        </p>
      ) : null}
      {!error && actionError ? (
        <p role="alert" style={{ margin: 0, color: "#ffb4ab" }}>
          {actionError}
        </p>
      ) : null}
      {!isLoading && !error && jobs.length === 0 ? <p>No export jobs yet.</p> : null}
      {jobs.length > 0 ? (
        <>
          <ul aria-label="Queue summary" className="jobs-page__summary-grid">
            <li className="jobs-page__summary-card">
              <p className="jobs-page__summary-count">{summaryCounts.queued}</p>
              <p className="jobs-page__summary-label">queued up</p>
            </li>
            <li className="jobs-page__summary-card">
              <p className="jobs-page__summary-count">{summaryCounts.processing}</p>
              <p className="jobs-page__summary-label">rendering now</p>
            </li>
            <li className="jobs-page__summary-card">
              <p className="jobs-page__summary-count">{summaryCounts.completed}</p>
              <p className="jobs-page__summary-label">ready to download</p>
            </li>
            <li className="jobs-page__summary-card">
              <p className="jobs-page__summary-count">{summaryCounts.failed}</p>
              <p className="jobs-page__summary-label">needs attention</p>
            </li>
            {summaryCounts.cancel_requested > 0 ? (
              <li className="jobs-page__summary-card">
                <p className="jobs-page__summary-count">{summaryCounts.cancel_requested}</p>
                <p className="jobs-page__summary-label">stopping</p>
              </li>
            ) : null}
            {summaryCounts.canceled > 0 ? (
              <li className="jobs-page__summary-card">
                <p className="jobs-page__summary-count">{summaryCounts.canceled}</p>
                <p className="jobs-page__summary-label">canceled</p>
              </li>
            ) : null}
            {summaryCounts.unknown > 0 ? (
              <li className="jobs-page__summary-card">
                <p className="jobs-page__summary-count">{summaryCounts.unknown}</p>
                <p className="jobs-page__summary-label">unexpected status</p>
              </li>
            ) : null}
          </ul>
          <ul aria-label="Export jobs" className="jobs-page__list">
            {jobs.map((job) => {
              const bucket = getQueueBucket(job.status);
              const title = documentTitles.get(job.document_id) ?? `Document ${job.document_id}`;

              return (
                <li className="jobs-page__card" key={job.id}>
                  <div className="jobs-page__card-header">
                    <div>
                      <p className="jobs-page__card-eyebrow">Job {job.id}</p>
                      <p className="jobs-page__card-title">{title}</p>
                      {documentTitles.has(job.document_id) ? (
                        <p className="jobs-page__card-detail">Document {job.document_id}</p>
                      ) : null}
                    </div>
                    <p className={`jobs-page__status jobs-page__status--${bucket}`}>
                      {getQueueLabel(bucket, job.status)}
                    </p>
                  </div>
                  <p className="jobs-page__card-detail">Preset {job.voice_preset_id}</p>
                  <p className="jobs-page__card-detail">
                    {job.format.toUpperCase()} export
                    {job.split_chapters ? " split by chapter" : " as one merged audiobook"}
                  </p>
                  {job.artifact_basename ? (
                    <p className="jobs-page__card-detail">Artifact label: {job.artifact_basename}</p>
                  ) : null}
                  <div className="jobs-page__progress" aria-label={`Job ${job.id} progress`}>
                    <span style={{ width: `${job.progress_percent ?? 0}%` }} />
                  </div>
                  <p className="jobs-page__card-detail">
                    {job.progress_percent ?? 0}% complete
                    {job.status_detail ? ` • ${job.status_detail}` : ""}
                  </p>
                  <p className="jobs-page__card-copy">{job.failure_detail ?? getQueueHint(bucket)}</p>
                  <ArtifactList artifacts={job.artifacts ?? []} jobId={job.id} />
                  <div className="jobs-page__actions">
                    {job.can_cancel ? (
                      <button
                        className="book-card__button book-card__button--ghost"
                        disabled={isMutatingJobId === job.id}
                        onClick={() => {
                          void cancelJob(job.id);
                        }}
                        type="button"
                      >
                        {isMutatingJobId === job.id ? "Updating..." : "Cancel export"}
                      </button>
                    ) : null}
                    {job.can_retry ? (
                      <button
                        className="book-card__button"
                        disabled={isMutatingJobId === job.id}
                        onClick={() => {
                          void retryJob(job.id);
                        }}
                        type="button"
                      >
                        {isMutatingJobId === job.id ? "Updating..." : "Retry export"}
                      </button>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      ) : null}
    </section>
  );
}
