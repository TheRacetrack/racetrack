from lifecycle.database.engine_factory import create_db_engine
from lifecycle.database.object_mapper import ObjectMapper
from lifecycle.database.tables import JobFamilyTable, AuthUserTable, new_uuid

from tests.utils import change_workdir


def test_db_models():
    with change_workdir('..'):
        engine = create_db_engine()
        object_builder = ObjectMapper(engine)

        records = object_builder.list_all(AuthUserTable)
        assert len(records) == 1

        user: AuthUserTable = object_builder.find_one(AuthUserTable, filters={'id': 1})
        assert user.id == 1
        assert user.username == 'admin'
        assert user.is_staff is True

        object_builder.create(JobFamilyTable(
            id=new_uuid(),
            name='primer',
        ))
        family_records = object_builder.list_all(JobFamilyTable)
        assert len(family_records) == 1
        assert family_records[0].name == 'primer'
