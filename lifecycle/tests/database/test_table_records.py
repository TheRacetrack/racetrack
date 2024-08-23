from lifecycle.config import Config
from lifecycle.database.base_engine import NoRowsAffected
from lifecycle.database.base_query_builder import BaseQueryBuilder
from lifecycle.database.engine_factory import create_db_engine
from lifecycle.database.record_mapper import RecordMapper
from lifecycle.database.schema.tables import AuthResourcePermission, JobFamily, User, AuthSubject
from lifecycle.database.table_model import new_uuid
from racetrack_client.log.errors import AlreadyExists
from racetrack_client.utils.time import now
from racetrack_client.log.logs import configure_logs
from racetrack_commons.auth.scope import AuthScope


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

    job_family.name = 'updated'
    mapper.update(job_family, only_changed=True)
    assert db_engine.last_query() == 'update job_family set name = ? where id = ?'
    assert db_engine.last_query() is None

    mapper.update(job_family, only_changed=True)
    assert db_engine.last_query() is None
    assert mapper.find_one(JobFamily, id=family_id).name == 'updated'

    job_family.name = 'fresher'
    mapper.update(job_family, only_changed=False)
    assert db_engine.last_query() == 'update job_family set id = ?, name = ? where id = ?'
    assert mapper.find_one(JobFamily, id=family_id).name == 'fresher'