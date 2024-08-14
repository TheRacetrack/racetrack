from lifecycle.database.base_engine import NoRowsAffected
from lifecycle.database.engine_factory import create_db_engine
from lifecycle.database.record_mapper import RecordMapper
from lifecycle.database.schema.tables import JobFamily, User
from lifecycle.database.table_model import new_uuid
from racetrack_client.utils.time import now
from racetrack_client.log.logs import configure_logs


def test_record_operations():
    configure_logs()
    engine = create_db_engine()
    object_builder = RecordMapper(engine)

    records = object_builder.find_all(User)
    assert len(records) == 1

    user: User = object_builder.find_one(User, id=1)
    assert user.id == 1
    assert user.username == 'admin'
    assert user.is_staff is True
    assert user.date_joined < now()

    object_builder.create(JobFamily(
        id=new_uuid(),
        name='primer',
    ))
    assert object_builder.count(JobFamily) == 1
    family_records: list[JobFamily] = object_builder.find_all(JobFamily)
    assert len(family_records) == 1
    assert family_records[0].name == 'primer'

    record_id = family_records[0].id
    family_records[0].name = 'new'
    object_builder.update(family_records[0])
    new_record = object_builder.find_one(JobFamily, id=record_id)
    assert new_record.name == 'new'

    object_builder.delete(JobFamily, id=record_id)
    assert object_builder.count(JobFamily) == 0
    
    try:
        object_builder.delete(JobFamily, id=record_id)
        assert False, 'it should raise NoRowsAffected exception'
    except NoRowsAffected:
        pass

    assert not object_builder.exists(JobFamily, id='nil')


def test_create_or_update():
    configure_logs()
    object_builder = RecordMapper(create_db_engine())

    record: JobFamily = JobFamily(
        id=new_uuid(),
        name='brand-new',
    )
    object_builder.create_or_update(record)
    assert object_builder.count(JobFamily) == 1
    object_builder.create_or_update(JobFamily(
        id=record.id,
        name='brand-brand-new',
    ))
    assert object_builder.count(JobFamily) == 1
    assert object_builder.find_one(JobFamily, id=record.id).name == 'brand-brand-new'
