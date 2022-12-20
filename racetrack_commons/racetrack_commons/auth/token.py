import os
from typing import List, Optional
import uuid

import jwt
from pydantic import BaseModel, Extra

from racetrack_client.utils.datamodel import datamodel_to_dict, parse_dict_datamodel
from racetrack_commons.auth.auth import AuthSubjectType, UnauthorizedError
from racetrack_commons.auth.b64_token import decode_esc_auth_base64
from racetrack_commons.auth.scope import AuthScope
from racetrack_client.log.logs import get_logger
from racetrack_client.log.exception import log_exception

logger = get_logger(__name__)


class AuthTokenPayload(BaseModel, extra=Extra.forbid):
    # unique token ID used to generate a token
    seed: str
    # whom the token refers to
    subject: str
    # AuthSubjectType value
    subject_type: str
    # AuthScope values
    scopes: Optional[List[str]] = None


def encode_jwt(payload: AuthTokenPayload, signature_key: str) -> str:
    """
    Convert Auth payload to JWT Token
    :param signature_key: Auth Secret key for generating and verifying JWT tokens
    """
    payload_dict = datamodel_to_dict(payload)
    return jwt.encode(payload_dict, signature_key, algorithm="HS256")


def verify_and_decode_jwt(token: str, signature_key: str) -> AuthTokenPayload:
    """Verify JWT signature and decode payload from a token"""
    try:
        payload_dict = jwt.decode(token, signature_key, algorithms=["HS256"],
                                  options={"verify_signature": True})
        return parse_dict_datamodel(payload_dict, AuthTokenPayload)

    except Exception as e:
        payload = decode_token_fallback(token)
        if payload is not None:
            return payload
        
        log_exception(e)
        raise UnauthorizedError('invalid JWT token', details=f'{e}, token={token}')


def decode_jwt(token: str) -> AuthTokenPayload:
    """Decode payload from a token without verifying signature"""
    try:
        payload_dict = jwt.decode(token, options={"verify_signature": False})
        return parse_dict_datamodel(payload_dict, AuthTokenPayload)

    except Exception as e:
        payload = decode_token_fallback(token)
        if payload is not None:
            return payload

        log_exception(e)
        raise UnauthorizedError('invalid JWT token', details=f'{e}, token={token}')


def generate_service_token(
    subject_name: str,
):
    auth_secret_key = os.environ.get('AUTH_KEY')
    assert auth_secret_key, 'fill AUTH_KEY var with your secret key'
    token = generate_internal_token(subject_name, auth_secret_key, scopes=[AuthScope.FULL_ACCESS])
    print(f'Service: {subject_name}\nLIFECYCLE_TOKEN:\n{token}\n')


def generate_internal_token(
    subject_name: str, 
    signature_key: str, 
    scopes: List[AuthScope] = [AuthScope.FULL_ACCESS],
) -> str:
    """Generate an auth token for internal Racetrack service to communicate with Lifecycle API"""
    payload = AuthTokenPayload(
        seed=str(uuid.uuid4()),
        subject=subject_name,
        subject_type=AuthSubjectType.INTERNAL.value,
        scopes=[scope.value for scope in scopes],
    )
    return encode_jwt(payload, signature_key)


def decode_token_fallback(token: str) -> Optional[AuthTokenPayload]:
    """
    Decode old base64 ESC token.
    base64 tokens are obsolete, but we still support them for backwards compatibility
    """
    try:
        esc_id, seed, ok = decode_esc_auth_base64(token)
        if not ok:
            return None
    except Exception:
        return None

    logger.warning(f'found obsolete base64 token for ESC {esc_id}. Please migrate to newer tokens')
    return AuthTokenPayload(
        seed=seed,
        subject=esc_id,
        subject_type=AuthSubjectType.ESC.value,
    )
