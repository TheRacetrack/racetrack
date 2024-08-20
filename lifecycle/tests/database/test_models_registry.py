from lifecycle.config.config import Config
from lifecycle.job.models_registry import (
    create_job_model,
    delete_job_model,
    job_exists,
    job_family_exists,
    list_job_family_models,
    list_job_models,
    read_job_family_model,
    read_job_model,
    read_latest_job_model,
    read_latest_wildcard_job_model,
    update_job,
)
from lifecycle.job.registry import read_job
from racetrack_client.manifest.manifest import GitManifest, Manifest
from racetrack_client.utils.time import datetime_to_timestamp, now
from racetrack_commons.entities.dto import JobDto, JobStatus


def test_managing_job_models():
    config = Config()

    jobs = list_job_models()
    assert not jobs
    families = list_job_family_models()
    assert not families

    create_time = now().replace(microsecond=0)
    create_timestamp = datetime_to_timestamp(create_time)
    job1 = JobDto(
        name='tester',
        version='0.0.0-alpha',
        status=JobStatus.RUNNING.value,
        create_time=create_timestamp,
        update_time=create_timestamp,
        manifest=Manifest(
            name='tester',
            owner_email='test@example.com',
            git=GitManifest(
                remote='github.com',
            ),
        ),
        internal_name='tester-0.0.0-alpha',
        infrastructure_target='docker',
    )
    job1_record = create_job_model(job1)
    job1_id = job1_record.id
    assert job1_id

    job2 = job1.model_copy()
    job2.version = '2.0.0'
    job2_record = create_job_model(job2)
    job2_id = job2_record.id

    jobs = list_job_models()
    assert len(jobs) == 2
    assert jobs[0].id == job1_id
    assert jobs[1].id == job2_id
    assert read_job_model('tester', '0.0.0-alpha').id == job1_id
    assert read_job_model('tester', '0.0.0-alpha').create_time.replace(microsecond=0) == create_time
    assert read_job('tester', '0.0.0-alpha', config).create_time == create_timestamp
    assert job_exists('tester', '0.0.0-alpha')
    assert not job_exists('tester', '0.0.0')
    assert job_family_exists('tester')
    assert not job_family_exists('none')
    families = list_job_family_models()
    assert len(families) == 1
    assert families[0].name == 'tester'
    assert read_job_family_model('tester').name == 'tester'
    assert read_latest_job_model('tester').version == '2.0.0'
    assert read_latest_wildcard_job_model('tester', '2.x.x').version == '2.0.0'

    delete_job_model('tester', '0.0.0-alpha')
    assert not job_exists('tester', '0.0.0-alpha')

    job2.status = JobStatus.ERROR.value
    update_job(job2)
    assert read_job_model('tester', '2.0.0').status == JobStatus.ERROR.value
