import type { JobArtifactRecord } from "../api/types";

type ArtifactListProps = {
  artifacts: JobArtifactRecord[];
  jobId: number;
};

export function ArtifactList({ artifacts, jobId }: ArtifactListProps) {
  if (artifacts.length === 0) {
    return null;
  }

  return (
    <section className="artifact-list" aria-label={`Artifacts for job ${jobId}`}>
      <p className="artifact-list__title">Artifacts</p>
      <ul className="artifact-list__items">
        {artifacts.map((artifact) => (
          <li className="artifact-list__item" key={artifact.artifact_id}>
            <div>
              <a className="jobs-page__download-link" href={artifact.download_url}>
                {artifact.label}
              </a>
              <p className="jobs-page__card-detail">{artifact.filename}</p>
            </div>
            {artifact.section_title ? (
              <p className="jobs-page__card-detail">{artifact.section_title}</p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
