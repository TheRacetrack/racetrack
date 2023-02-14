from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from racetrack_client.utils.datamodel import parse_dict_datamodel
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.entities.dto import EscDto
from lifecycle.config import Config
from lifecycle.job.esc import list_escs, create_esc
from lifecycle.auth.check import check_auth


def setup_esc_endpoints(api: APIRouter, config: Config):

    class EscPayloadModel(BaseModel):
        name: str = Field(
            description='name of ESC',
            example='alice',
        )
        id: Optional[str] = Field(
            default=None,
            description='ESC Identity ID',
            example='b13f4ae8-6be7-4907-9951-4be79d9d684c',
        )

    @api.get('/escs')
    def _get_all_escs(request: Request):
        """Get list of all ESC"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        return list(list_escs())

    @api.post('/escs')
    def _create_esc(payload: EscPayloadModel, request: Request):
        """Create new ESC"""
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        esc = parse_dict_datamodel(payload, EscDto)
        return create_esc(esc)
