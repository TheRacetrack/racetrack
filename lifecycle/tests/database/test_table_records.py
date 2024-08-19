from lifecycle.database.base_engine import NoRowsAffected
from lifecycle.database.engine_factory import create_db_engine
from lifecycle.database.record_mapper import RecordMapper
from lifecycle.database.schema.tables import JobFamily, User
from lifecycle.database.table_model import new_uuid
from racetrack_client.log.errors import AlreadyExists
from racetrack_client.utils.time import now
from racetrack_client.log.logs import configure_logs


def test_record_operations():
    configure_logs()
    engine = create_db_engine()
    mapper = RecordMapper(engine)

    records = mapper.find_all(User)
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
    family_records: list[JobFamily] = mapper.find_all(JobFamily)
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
    mapper = RecordMapper(create_db_engine())

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
    object_builder = RecordMapper(create_db_engine())

    record: JobFamily = JobFamily(
        id=new_uuid(),
        name='brand-new',
    )
    object_builder.create(record)
    try:
        object_builder.create(record)
        assert False, 'it should raise exception'
    except AlreadyExists:
        pass
