from dataclasses import dataclass

from lifecycle.auth.authorize import list_permitted_jobs
from lifecycle.auth.subject import find_auth_subject_by_esc_id, find_auth_subject_by_job_family_name
from lifecycle.config.config import Config
from lifecycle.database.schema import tables
from lifecycle.job.esc import list_escs
from lifecycle.job.registry import list_job_registry
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.entities.dto import EscDto, JobDto
from racetrack_commons.urls import get_external_pub_url
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


@dataclass
class JobGraphNode:
    id: str
    type: str
    title: str
    subtitle: str | None = None


@dataclass
class JobGraphEdge:
    from_id: str
    to_id: str


@dataclass
class JobGraph:
    nodes: list[JobGraphNode]
    edges: list[JobGraphEdge]


def build_job_dependencies_graph(config: Config, auth_subject: tables.AuthSubject | None) -> JobGraph:
    jobs: list[JobDto] = list_job_registry(config, auth_subject)
    family_names = _group_job_families(jobs)
    escs: list[EscDto] = list(list_escs())

    nodes: list[JobGraphNode] = []
    for esc in escs:
        nodes.append(JobGraphNode(
            id=f'esc-{esc.id}',
            type='esc',
            title=f'{esc.name}',
            subtitle=f'ESC:\n{esc.id}',
        ))
    for family_name in family_names:
        job_family_details = list_job_family_details(jobs, family_name, config)
        nodes.append(JobGraphNode(
            id=f'job-family-{family_name}',
            type='job-family',
            title=f'{family_name}',
            subtitle=f'Job Family: {family_name}\nJobs:\n{job_family_details}',
        ))

    edges: list[JobGraphEdge] = []

    for family_name in family_names:
        try:
            auth_subject = find_auth_subject_by_job_family_name(family_name)
        except EntityNotFound:
            logger.warning(f'Could not find auth subject for job family {family_name}')
            continue
        dest_jobs = list_permitted_jobs(auth_subject, AuthScope.CALL_JOB.value, jobs)
        dest_families = _group_job_families(dest_jobs)

        for dest_family in dest_families:
            edges.append(JobGraphEdge(
                from_id=f'job-family-{family_name}',
                to_id=f'job-family-{dest_family}',
            ))

    for esc in escs:
        try:
            auth_subject = find_auth_subject_by_esc_id(esc.id)
        except EntityNotFound:
            logger.warning(f'Could not find auth subject for ESC {esc.id}')
            continue
        dest_jobs = list_permitted_jobs(auth_subject, AuthScope.CALL_JOB.value, jobs)
        dest_families = _group_job_families(dest_jobs)

        for dest_family in dest_families:
            edges.append(JobGraphEdge(
                from_id=f'esc-{esc.id}',
                to_id=f'job-family-{dest_family}',
            ))

    return JobGraph(nodes=nodes, edges=edges)


def list_job_family_details(jobs: list[JobDto], family_name: str, config: Config) -> str:
    family_jobs = [f for f in jobs if f.name == family_name]
    return '\n'.join(('- ' + _get_job_details(f, config) for f in family_jobs))


def _get_job_details(job: JobDto, config: Config) -> str:
    external_pub_url = get_external_pub_url(config.external_pub_url)
    url = f'{external_pub_url}/job/{job.name}/{job.version}'
    return f'{job.name} v{job.version} - {url}'


def _group_job_families(jobs: list[JobDto]) -> list[str]:
    return list(set([f.name for f in jobs]))
