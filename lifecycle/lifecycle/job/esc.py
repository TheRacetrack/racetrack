from typing import Iterable
from lifecycle.auth.subject import get_auth_subject_by_esc, create_auth_token

from lifecycle.database.schema import tables
from lifecycle.database.schema.dto_converter import esc_record_to_dto
from lifecycle.database.table_model import new_uuid
from lifecycle.server.cache import LifecycleCache
from racetrack_client.log.errors import EntityNotFound, AlreadyExists
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.dto import EscDto

logger = get_logger(__name__)


def read_esc(esc_id: str) -> EscDto:
    """Read existing ESC data"""
    esc = read_esc_model(esc_id)
    return esc_record_to_dto(esc)


def read_esc_model(esc_id: str) -> tables.Esc:
    try:
        return LifecycleCache.record_mapper().find_one(tables.Esc, id=esc_id)
    except EntityNotFound:
        raise EntityNotFound(f'ESC with ID {esc_id} was not found')


def create_esc(esc_dto: EscDto) -> EscDto:
    assert esc_dto.name, 'ESC name can not be empty'
    esc_model = tables.Esc(
        id=new_uuid(),
        name=esc_dto.name,
    )

    mapper = LifecycleCache.record_mapper()
    if esc_dto.id is not None:
        esc_model.id = esc_dto.id
        if mapper.exists(tables.Esc, id=esc_dto.id):
            raise AlreadyExists('ESC with given ID already exists')
    mapper.create(esc_model)

    auth_subject = get_auth_subject_by_esc(esc_model)
    create_auth_token(auth_subject)

    return esc_record_to_dto(esc_model)


def list_escs() -> Iterable[EscDto]:
    all_esc = LifecycleCache.record_mapper().list_all(tables.Esc)
    for esc_model in all_esc:
        yield esc_record_to_dto(esc_model)
