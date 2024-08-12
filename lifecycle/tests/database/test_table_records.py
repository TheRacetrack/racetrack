from lifecycle.database.base_engine import NoRowsAffected
from lifecycle.database.engine_factory import create_db_engine
from lifecycle.database.object_mapper import ObjectMapper
from lifecycle.database.schema.tables import JobFamilyRecord, AuthUserRecord
from lifecycle.database.table_model import new_uuid

from racetrack_client.utils.time import now
from tests.utils import change_workdir


def test_record_operations():
    with change_workdir('..'):
        engine = create_db_engine()
        object_builder = ObjectMapper(engine)

        records = object_builder.list_all(AuthUserRecord)
        assert len(records) == 1

        user: AuthUserRecord = object_builder.find_one(AuthUserRecord, id=1)
        assert user.id == 1
        assert user.username == 'admin'
        assert user.is_staff is True
        assert user.date_joined < now()

        object_builder.create(JobFamilyRecord(
            id=new_uuid(),
            name='primer',
        ))
        assert object_builder.count(JobFamilyRecord) == 1
        family_records = object_builder.list_all(JobFamilyRecord)
        assert len(family_records) == 1
        assert family_records[0].name == 'primer'

        record_id = family_records[0].id
        family_records[0].name = 'new'
        object_builder.update(JobFamilyRecord, family_records[0])
        new_record = object_builder.find_one(JobFamilyRecord, id=record_id)
        assert new_record.name == 'new'

        object_builder.delete(JobFamilyRecord, id=record_id)
        assert object_builder.count(JobFamilyRecord) == 0
        
        try:
            object_builder.delete(JobFamilyRecord, id=record_id)
            assert False, 'it should raise NoRowsAffected exception'
        except NoRowsAffected:
            pass
