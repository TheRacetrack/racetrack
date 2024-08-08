import json
from threading import Thread
from typing import Dict, Callable
import queue

import httpx
from fastapi.responses import StreamingResponse

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)

EVENT_RESULT = 'event: result\n'
EVENT_HEARTBEAT = 'event: keepalive_heartbeat'
DATA_MESSAGE = 'data: '


def stream_result_with_heartbeat(result_runner: Callable[[], Dict]):
    """
    Return result dict in SSE (Server-Sent Events) response, streaming heartbeat events to keep the connection alive
    """
    result_channel = queue.Queue(maxsize=0)

    def _runner():
        try:
            result = result_runner()
            result_channel.put(json.dumps({
                'result': result,
            }))
        except BaseException as e:
            result_channel.put(json.dumps({
                'error': str(e),
            }))

    Thread(target=_runner, daemon=True).start()

    def sse_generator():
        while True:
            try:
                event_data: str = result_channel.get(block=True, timeout=60)
                yield f'{EVENT_RESULT}data: {event_data}\n\n'
                result_channel.task_done()
                return
            except queue.Empty:
                yield f'{EVENT_HEARTBEAT}\n\n'

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


def make_sse_request(
    method: str,
    url: str,
    payload: Dict,
):
    response_buffer = ''
    with httpx.Client(timeout=3600) as client:
        with client.stream(method.upper(), url, json=payload) as stream_response:
            for line in stream_response.iter_lines():
                if line.strip() == 'event: keepalive_heartbeat':
                    logger.debug(f'keepalive heartbeat for {method} {url}')
                else:
                    response_buffer += line + '\n'

    validate_streaming_response(stream_response)
    response = extract_response_dict(response_buffer)
    error = response.get('error')
    if error:
        raise RuntimeError(f'Streaming Response error: {error}')
    return response['result']


def validate_streaming_response(response: httpx.Response):
    if response.is_success:
        return
    message = f'HTTP error "{response.status_code} {response.reason_phrase}" ' \
              f'for url {response.request.method} {response.url}'
    raise RuntimeError(message)


def extract_response_dict(response_text: str) -> Dict:
    prefix = EVENT_RESULT + DATA_MESSAGE
    last_occurrence = response_text.find(prefix)
    if last_occurrence == -1:
        raise ValueError('could not find result event in the SSE response')

    remainder = response_text[last_occurrence + len(prefix):]
    json_dict = json.loads(remainder)
    return json_dict
