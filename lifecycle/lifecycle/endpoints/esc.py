from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from lifecycle.auth.subject import get_auth_subject_by_esc
from racetrack_client.utils.datamodel import parse_dict_datamodel
from racetrack_commons.entities.dto import EscDto
from lifecycle.job.esc import list_escs, create_esc, read_esc_model
from lifecycle.auth.check import check_staff_user


def setup_esc_endpoints(api: APIRouter):

    class EscPayloadModel(BaseModel):
        name: str = Field(
            description='name of ESC',
            examples=['alice'],
        )
        id: Optional[str] = Field(
            default=None,
            description='ESC Identity ID',
            examples=['b13f4ae8-6be7-4907-9951-4be79d9d684c'],
        )

    @api.get('/escs')
    def _get_all_escs(request: Request) -> list[EscDto]:
        """Get list of all ESC"""
        check_staff_user(request)
        return list(list_escs())

    @api.post('/escs')
    def _create_esc(payload: EscPayloadModel, request: Request) -> EscDto:
        """Create new ESC"""
        check_staff_user(request)
        esc = parse_dict_datamodel(payload.model_dump(), EscDto)
        return create_esc(esc)

    @api.get('/escs/{esc_id}/auth_data')
    def _get_esc_auth_data(esc_id: str, request: Request):
        """Get ESC's all details with auth token"""
        check_staff_user(request)
        esc_model = read_esc_model(esc_id)
        auth_subject = get_auth_subject_by_esc(esc_model)
        return {
            'id': esc_id,
            'name': esc_model.name,
            'token': auth_subject.token,
        }
