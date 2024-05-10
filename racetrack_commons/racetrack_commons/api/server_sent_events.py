import json
from typing import Dict

from httpx import Response

RESULT_EVENT = 'event: result\n'
DATA_MESSAGE = 'data: '


def validate_streaming_response(response: Response):
    if response.is_success:
        return
    message = f'HTTP error "{response.status_code} {response.reason_phrase}" ' \
              f'for url {response.request.method} {response.url}'
    raise RuntimeError(message)


def extract_response_dict(response_text: str) -> Dict:
    prefix = RESULT_EVENT + DATA_MESSAGE
    last_occurrence = response_text.find(prefix)
    if last_occurrence == -1:
        raise ValueError('could not find result event in the SSE response')

    remainder = response_text[last_occurrence + len(prefix):]
    json_dict = json.loads(remainder)
    return json_dict
