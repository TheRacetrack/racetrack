# base64 tokens are obsolete, they're still supported for backwards compatibility
import base64
import json
from binascii import Error
from typing import Tuple


def decode_esc_auth_base64(esc_auth_encoded: str) -> Tuple[str, str, bool]:
    esc_auth_json, ok = _decode_from_base64(esc_auth_encoded)
    if not ok:
        return '', '', False
    esc_auth = json.loads(esc_auth_json)

    try:
        esc_id = esc_auth['esc-id']
        token = esc_auth['api-key']
        return esc_id, token, True
    except KeyError:
        return '', '', False


def _decode_from_base64(content_base64: str) -> Tuple[str, bool]:
    try:
        content_base64_bytes = content_base64.encode(encoding='UTF-8', errors='strict')
        content_bytes = base64.b64decode(content_base64_bytes, validate=True)
        content = content_bytes.decode(encoding='UTF-8', errors='strict')
        return content, True
    except (UnicodeDecodeError, Error):
        return '', False
