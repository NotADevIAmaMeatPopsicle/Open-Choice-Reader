from app.services.cache_eviction import maybe_evict_stale_cached_audio
from app.services.jobs import claim_next_queued_job, reclaim_stale_jobs
from app.worker.jobs import process_export_job


def run_once() -> int:
    reclaim_stale_jobs()
    maybe_evict_stale_cached_audio()

    job = claim_next_queued_job()
    if job is None:
        return 0

    process_export_job(job)
    return 1
