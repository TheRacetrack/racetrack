from typing import Dict, List, Tuple
from racetrack_client.utils.semver import SemanticVersion
from racetrack_client.utils.time import days_ago
from racetrack_commons.entities.dto import JobDto, JobStatus


def enrich_jobs_purge_info(jobs: List[JobDto]) -> List[Dict]:
    """Enrich jobs with removal candidates info: score and reasons"""
    job_dicts = []
    for job in jobs:
        score, reasons = assess_job_usability(job, jobs)
        job_dict = job.dict()
        job_dict['purge_score'] = -score
        job_dict['purge_reasons'] = '\n'.join(reasons)
        job_dict['purge_newer_versions'] = _count_job_newer_versions(job, jobs)
        job_dicts.append(job_dict)
    return sorted(job_dicts, key=lambda f: -f['purge_score'])


def assess_job_usability(job: JobDto, all_jobs: List[JobDto]) -> Tuple[float, List[str]]:
    """
    Assess usability of a job.
    Return score number representing penalty points with descriptions of reasons.
    A lower value means a better candidate for removal.
    Positive score means the job shouldn't be removed.
    """
    score: float = 0
    reasons = []

    if job.status == JobStatus.ORPHANED.value:
        score -= 100
        reasons.append('Orphaned job is most likely a useless remnant.')
    elif job.status == JobStatus.LOST.value:
        score -= 50
        reasons.append('Job is lost - can\'t be found in a cluster. It should be redeployed or removed.')
    elif job.status == JobStatus.ERROR.value:
        score -= 20
        reasons.append('Job is failing. It should be fixed or removed.')

    deployed_days_ago = days_ago(job.update_time)
    if deployed_days_ago >= 1:  # wait a day until we decide it was never called
        never_called = job.last_call_time is None or job.last_call_time == 0
        if never_called:
            score -= 10
            reasons.append('Job seems to be unused as it was never called.')
        else:
            last_call_days_ago = days_ago(job.last_call_time)
            if last_call_days_ago > 1:
                score -= 10 * _interpolate(last_call_days_ago, 0, 30)
                reasons.append(f'Job hasn\'t been called for {last_call_days_ago:.1f} days.')

    newer_versions = _count_job_newer_versions(job, all_jobs)
    if newer_versions > 0:
        score -= 1 * newer_versions
        reasons.append(f'Job has {newer_versions} newer versions.')

    return score, reasons


def _count_job_newer_versions(job: JobDto, all_jobs: List[JobDto]) -> int:
    """Count how many job (from the same family) are newer than this one"""
    count = 0
    job_version = SemanticVersion(job.version)
    family_jobs = [f for f in all_jobs if f.name == job.name]
    for f in family_jobs:
        if SemanticVersion(f.version) > job_version:
            count += 1
    return count


def _interpolate(value: float, min_value: float, max_value: float) -> float:
    if value < min_value:
        return 0
    if value > max_value:
        return 1
    return (value - min_value) / (max_value - min_value)
