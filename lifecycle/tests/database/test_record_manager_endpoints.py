from lifecycle.config import Config
from lifecycle.database.engine_factory import create_db_engine
from lifecycle.database.record_mapper import RecordMapper
from lifecycle.endpoints.records import list_all_tables, create_record, RecordFieldsPayload, \
    count_table_records, CountRecordsRequest, list_table_records, FetchManyRecordsRequest, get_one_record, \
    update_record, delete_record, FetchManyRecordsResponse
from racetrack_client.log.errors import EntityNotFound


def test_list_all_tables():
    metadatas = [meta for meta in list_all_tables()]
    assert 'JobFamily' in [meta.class_name for meta in metadatas]
    assert 'registry_job' in [meta.table_name for meta in metadatas]


def test_endpoints_operations():
    mapper = RecordMapper(create_db_engine(Config()))

    create_record(mapper, RecordFieldsPayload(fields={'name': 'primer'}), 'registry_jobfamily')
    create_record(mapper, RecordFieldsPayload(fields={'name': 'adder'}), 'registry_jobfamily')

    assert count_table_records(mapper, CountRecordsRequest(), 'registry_jobfamily') == 2

    response = list_table_records(mapper, FetchManyRecordsRequest(), 'registry_jobfamily')
    assert response.columns == ['id', 'name']
    assert response.primary_key_column == 'id'
    assert set(record.fields['name'] for record in response.records) == {'primer', 'adder'}
    ids = [record.fields['id'] for record in response.records]
    assert ids[0] != ids[1]

    response = list_table_records(mapper, FetchManyRecordsRequest(filters={'name': 'adder'}), 'registry_jobfamily')
    assert [record.fields['name'] for record in response.records] == ['adder']

    response = list_table_records(mapper, FetchManyRecordsRequest(order_by=['name'], columns=['name']), 'registry_jobfamily')
    assert response == FetchManyRecordsResponse(
        columns=['name'],
        primary_key_column='id',
        records=[
            RecordFieldsPayload(fields={'name': 'adder'}),
            RecordFieldsPayload(fields={'name': 'primer'}),
        ],
    )

    record = get_one_record(mapper, 'registry_jobfamily', ids[0])
    assert record.fields == {'id': ids[0], 'name': 'primer'}

    update_record(mapper, RecordFieldsPayload(fields={'name': 'primer2'}), 'registry_jobfamily', ids[0])
    record = get_one_record(mapper, 'registry_jobfamily', ids[0])
    assert record.fields['name'] == 'primer2'

    delete_record(mapper, 'registry_jobfamily', ids[0])
    delete_record(mapper, 'registry_jobfamily', ids[1])
    assert count_table_records(mapper, CountRecordsRequest(), 'registry_jobfamily') == 0

    try:
        get_one_record(mapper, 'registry_jobfamily', ids[0])
        assert False, 'Should have raised EntityNotFound'
    except EntityNotFound:
        pass
