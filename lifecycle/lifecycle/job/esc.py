from typing import Iterable
from lifecycle.auth.subject import get_auth_subject_by_esc, regenerate_auth_token

from lifecycle.django.registry import models
from lifecycle.django.registry.database import db_access
from lifecycle.job.dto_converter import esc_model_to_dto
from racetrack_client.log.errors import EntityNotFound, AlreadyExists
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.dto import EscDto

logger = get_logger(__name__)


def read_esc(esc_id: str) -> EscDto:
    """Read existing ESC data"""
    esc = read_esc_model(esc_id)
    return esc_model_to_dto(esc)


@db_access
def read_esc_model(esc_id: str) -> models.Esc:
    try:
        return models.Esc.objects.get(id=esc_id)
    except models.Esc.DoesNotExist:
        raise EntityNotFound(f'ESC with ID {esc_id} was not found')


@db_access
def create_esc(esc_dto: EscDto) -> EscDto:
    esc_model = models.Esc()
    esc_model.name = esc_dto.name

    if esc_dto.id is not None:
        esc_model.id = esc_dto.id
        if models.Esc.objects.filter(id=esc_dto.id).exists():
            raise AlreadyExists('ESC already exists')
    esc_model.save()
    # Esc needs to have id (done in save() above) before we can create auth token

    get_auth_subject_by_esc(esc_model)

    return esc_model_to_dto(esc_model)


@db_access
def generate_esc_auth(esc_id: str) -> EscDto:
    try:
        esc_model = models.Esc.objects.get(id=esc_id)
        auth_subject = get_auth_subject_by_esc(esc_model)
        regenerate_auth_token(auth_subject)
        logger.info(f'Auth token generated for ESC {esc_id}')
        return esc_model_to_dto(esc_model)
    except models.Esc.DoesNotExist:
        raise EntityNotFound(f'ESC with ID {esc_id} was not found')


@db_access
def list_escs() -> Iterable[EscDto]:
    all_esc = models.Esc.objects.all()
    for esc_model in all_esc:
        yield esc_model_to_dto(esc_model)
