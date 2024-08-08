import os
from lifecycle.database.engine_factory import create_db_engine
from lifecycle.database.object_mapper import ObjectMapper
from lifecycle.database.tables import JobFamilyTable


def test_db_models():
    cwd = os.getcwd()
    try:
        os.chdir('..')

        engine = create_db_engine()
        object_builder = ObjectMapper(engine)

        # record: JobFamilyTable = object_builder.find_one(JobFamilyTable, filters={'id': '123'})
        # assert record is not None

        records = object_builder.list_all(JobFamilyTable)
        assert len(records) == 0
        

    finally:
        os.chdir(cwd)