import json

from lifecycle.config import Config
from lifecycle.database.base_engine import NoRowsAffected
from lifecycle.database.condition_builder import QueryCondition
from lifecycle.database.engine_factory import create_db_engine
from lifecycle.database.record_mapper import RecordMapper
from lifecycle.database.schema.tables import AuthResourcePermission, JobFamily, User, AuthSubject, Job
from lifecycle.database.table_model import new_uuid, table_name
from racetrack_client.log.errors import AlreadyExists
from racetrack_client.utils.time import now
from racetrack_client.log.logs import configure_logs
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.entities.dto import JobStatus


def test_record_operations():
    configure_logs()
    mapper = RecordMapper(create_db_engine(Config()))

    records = mapper.list_all(User)
    assert len(records) == 1

    user: User = mapper.find_one(User, id=1)
    assert user.id == 1
    assert user.username == 'admin'
    assert user.is_staff is True
    assert user.date_joined < now()

    mapper.create(JobFamily(
        id=new_uuid(),
        name='primer',
    ))
    assert mapper.count(JobFamily) == 1
    family_records: list[JobFamily] = mapper.list_all(JobFamily)
    assert len(family_records) == 1
    assert family_records[0].name == 'primer'

    record_id = family_records[0].id
    family_records[0].name = 'new'
    mapper.update(family_records[0])
    new_record = mapper.find_one(JobFamily, id=record_id)
    assert new_record.name == 'new'

    mapper.delete(JobFamily, id=record_id)
    assert mapper.count(JobFamily) == 0
    
    try:
        mapper.delete(JobFamily, id=record_id)
        assert False, 'it should raise NoRowsAffected exception'
    except NoRowsAffected:
        pass

    assert not mapper.exists(JobFamily, id='nil')


def test_create_or_update():
    configure_logs()
    mapper = RecordMapper(create_db_engine(Config()))

    record: JobFamily = JobFamily(
        id=new_uuid(),
        name='brand-new',
    )
    mapper.create_or_update(record)
    assert mapper.count(JobFamily) == 1
    mapper.create_or_update(JobFamily(
        id=record.id,
        name='brand-brand-new',
    ))
    assert mapper.count(JobFamily) == 1
    assert mapper.find_one(JobFamily, id=record.id).name == 'brand-brand-new'


def test_violate_primary_key():
    configure_logs()
    mapper = RecordMapper(create_db_engine(Config()))

    record: JobFamily = JobFamily(
        id=new_uuid(),
        name='brand-new',
    )
    mapper.create(record)
    try:
        mapper.create(record)
        assert False, 'it should raise exception'
    except AlreadyExists:
        pass


def test_create_with_auto_increment():
    configure_logs()
    mapper = RecordMapper(create_db_engine(Config()))

    job_family = JobFamily(
        id=new_uuid(),
        name='primer',
    )
    mapper.create(job_family)
    auth_subject: AuthSubject = AuthSubject(
        id=new_uuid(),
        job_family_id=job_family.id,
        user_id=None,
        esc_id=None,
    )
    mapper.create(auth_subject)
    permission: AuthResourcePermission = AuthResourcePermission(
        id=None,
        auth_subject_id=auth_subject.id,
        scope=AuthScope.CALL_JOB.value,
        job_family_id=None,
        job_id=None,
        endpoint=None,
    )
    mapper.create(permission)

    new_id = permission.id
    assert new_id is not None
    new_record = mapper.find_one(AuthResourcePermission, auth_subject_id=auth_subject.id)
    assert new_record.id == new_id


def test_update_only_changed_fields():
    configure_logs()
    db_engine = create_db_engine(Config(database_log_queries=True))
    mapper = RecordMapper(db_engine)

    family_id = new_uuid()
    job_family = JobFamily(id=family_id, name='primer')
    mapper.create(job_family)

    job_family = mapper.find_one(JobFamily, id=family_id)
    job_family.name = 'updated'
    mapper.update(job_family, only_changed=True)
    assert db_engine.last_query() == 'update registry_jobfamily set name = ? where id = ?'
    assert db_engine.last_query() is None

    mapper.update(job_family, only_changed=True)
    assert db_engine.last_query() is None
    assert mapper.find_one(JobFamily, id=family_id).name == 'updated'

    job_family.name = 'fresher'
    mapper.update(job_family, only_changed=False)
    assert db_engine.last_query() == 'update registry_jobfamily set id = ?, name = ? where id = ?'
    assert mapper.find_one(JobFamily, id=family_id).name == 'fresher'


def test_delete_cascade():
    configure_logs()
    mapper = RecordMapper(create_db_engine(Config(database_log_queries=True)))

    job_family = JobFamily(id=new_uuid(), name='primer')
    mapper.create(job_family)
    job = _create_test_job('primer', job_family.id)
    mapper.create(job)
    assert mapper.count(Job) == 1
    assert mapper.count(JobFamily) == 1

    mapper.delete_record(job_family)
    assert mapper.count(Job) == 0
    assert mapper.count(JobFamily) == 0


def test_json_column():
    mapper = RecordMapper(create_db_engine(Config(database_log_queries=True)))

    job_family = JobFamily(id=new_uuid(), name='primer')
    mapper.create(job_family)
    stats_content = json.dumps({"number_of_restarts": 2})
    job = _create_test_job('primer', job_family.id, version='0.0.0', infrastructure_stats=stats_content)
    mapper.create(job)

    job: Job = mapper.find_one(Job, id=job.id)
    assert job.infrastructure_stats == '{"number_of_restarts": 2}'


def test_filtering_many_records():
    mapper = RecordMapper(create_db_engine(Config(database_log_queries=True)))

    job_family = JobFamily(id=new_uuid(), name='primer')
    mapper.create(job_family)
    job1 = _create_test_job('primer', job_family.id, version='1.1.1', error='')
    mapper.create(job1)
    job2 = _create_test_job('primer', job_family.id, version='2.2.2', error='bad')
    mapper.create(job2)
    job3 = _create_test_job('primer', job_family.id, version='3.3.3', error='')
    mapper.create(job3)

    assert mapper.exists_record(job1)

    records = mapper.find_many(Job, family_id=job_family.id)
    assert len(records) == 3
    records = mapper.find_many(Job, order_by=['-version'], error='', name='primer')
    assert len(records) == 2
    assert [r.version for r in records] == ['3.3.3', '1.1.1']

    placeholder: str = mapper.placeholder
    table_family = table_name(JobFamily)
    table_job = table_name(Job)
    join_expression = f'left join {table_family} on {table_family}.id = {table_job}.family_id'
    filter_condition = QueryCondition.operator_and(
        QueryCondition(f'{table_family}.name = {placeholder}', 'primer'),
        QueryCondition(f'{table_job}.error is not null'),
        QueryCondition(f'{table_job}.error = {placeholder}', 'bad'),
    )
    records = mapper.filter(Job, join_expression=join_expression, condition=filter_condition)
    assert len(records) == 1
    assert records[0].version == '2.2.2'

    assert mapper.exists_on_condition(
        Job, join_expression=join_expression, condition=filter_condition,
    )

    records = mapper.filter_by_fields(Job, order_by=['version'], offset=1, limit=1)
    assert [r.version for r in records] == ['2.2.2']

    records = mapper.filter_by_fields(Job, order_by=['version'], error='bad')
    assert [r.version for r in records] == ['2.2.2']


def test_auto_assign_id():
    configure_logs()
    mapper = RecordMapper(create_db_engine(Config()))

    record = User(id=0, password='encrypted', username='new-admin', first_name='', last_name='', email='admin@example.com', is_active=False, is_staff=False, is_superuser=False, date_joined=now(), last_login=None)
    mapper.create(record)
    new_record = mapper.find_one(User, username='new-admin')
    assert new_record.id > 0

    record = JobFamily(id='', name='new-one')
    mapper.create(record)
    new_record = mapper.find_one(JobFamily, name='new-one')
    assert new_record.id, 'ID should be assigned automatically'


def test_create_from_dict():
    configure_logs()
    mapper = RecordMapper(create_db_engine(Config()))

    record = mapper.create_from_dict(JobFamily, {'name': 'new-one'})
    assert record.id, 'ID should be assigned automatically'
    record = mapper.find_one(JobFamily, name='new-one')
    assert record.id, 'ID should be assigned automatically'


def test_update_from_dict():
    configure_logs()
    mapper = RecordMapper(create_db_engine(Config()))

    record = mapper.create_from_dict(JobFamily, {'name': 'old-one'})
    mapper.update_from_dict(JobFamily, record.id, {'name': 'new-one-updated'})
    record = mapper.find_one(JobFamily, name='new-one-updated')
    assert record.name, 'new-one-updated'


def _create_test_job(
    name: str,
    family_id: str,
    version: str = '0.0.0',
    infrastructure_stats: str | None = None,
    error: str | None = None,
) -> Job:
    return Job(
        id=new_uuid(),
        family_id=family_id,
        name=name,
        version=version,
        status=JobStatus.RUNNING.value,
        create_time=now(),
        update_time=now(),
        manifest=None,
        internal_name=None,
        error=error,
        notice=None,
        image_tag=None,
        deployed_by=None,
        last_call_time=None,
        infrastructure_target=None,
        replica_internal_names=None,
        job_type_version='python3:1.0.0',
        infrastructure_stats=infrastructure_stats,
    )
