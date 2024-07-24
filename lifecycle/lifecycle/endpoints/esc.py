from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from racetrack_client.utils.datamodel import parse_dict_datamodel
from racetrack_client.utils.time import datetime_to_timestamp
from racetrack_commons.entities.dto import EscDto
from lifecycle.job.esc import list_escs, create_esc, read_esc_model
from lifecycle.auth.check import check_staff_user
from lifecycle.auth.subject import get_auth_subject_by_esc, get_auth_tokens_by_subject, revoke_token
from lifecycle.django.registry import models


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


class AuthTokenData(BaseModel):
    id: str
    token: str
    expiry_time: int | None
    active: bool
    last_use_time: int | None


class EscAuthData(BaseModel):
    id: str
    name: str
    tokens: list[AuthTokenData]


def setup_esc_endpoints(api: APIRouter):

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
    def _get_esc_auth_data(esc_id: str, request: Request) -> EscAuthData:
        """Get ESC's all details with auth token"""
        check_staff_user(request)
        esc_model = read_esc_model(esc_id)
        auth_subject: models.AuthSubject = get_auth_subject_by_esc(esc_model)
        auth_tokens: list[models.AuthToken] = get_auth_tokens_by_subject(auth_subject)
        return EscAuthData(
            id=esc_id,
            name=esc_model.name,
            tokens=[AuthTokenData(
                id=model.id,
                token=model.token,
                expiry_time=datetime_to_timestamp(model.expiry_time) if model.expiry_time is not None else None,
                active=model.active,
                last_use_time=datetime_to_timestamp(model.last_use_time) if model.last_use_time is not None else None,
            ) for model in auth_tokens],
        )

    @api.delete('/escs/{esc_id}/auth_token/{token_id}')
    def _revoke_esc_token(esc_id: str, token_id: str, request: Request):
        check_staff_user(request)
        read_esc_model(esc_id)
        revoke_token(token_id)
