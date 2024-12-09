import asyncio

import backoff
import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from racetrack_client.log.logs import configure_logs
from racetrack_commons.api.asgi.asgi_server import serve_asgi_in_background
from racetrack_commons.socket import free_tcp_port


def test_server_sent_events():
    app = FastAPI()

    def sse_generator():
        for num in range(3):
            yield f'data: {{"progress": {num}}}\n\n'

    @app.get("/sse")
    def sse_endpoint():
        return StreamingResponse(sse_generator(), media_type="text/event-stream")

    @app.get("/ready")
    def ready_endpoint():
        return

    async def test_async():
        configure_logs()
        port = free_tcp_port()
        with serve_asgi_in_background(app, port):
            _wait_until_server_ready(port)
            _test_sse_client_get(port)
            _test_sse_client_stream(port)

    asyncio.run(test_async())


def _test_sse_client_get(port: int):
    response = httpx.get(f'http://127.0.0.1:{port}/sse')
    assert response.status_code == 200
    assert response.text == '''data: {"progress": 0}

data: {"progress": 1}

data: {"progress": 2}

'''


def _test_sse_client_stream(port: int):
    lines = []
    with httpx.Client(timeout=10) as client:
        with client.stream('GET', f'http://127.0.0.1:{port}/sse') as stream_response:
            for line in stream_response.iter_lines():
                lines.append(line)

    assert lines == [
        'data: {"progress": 0}',
        '',
        'data: {"progress": 1}',
        '',
        'data: {"progress": 2}',
        '',
    ]
    stream_response.raise_for_status()
    assert stream_response.status_code == 200


@backoff.on_exception(backoff.fibo, httpx.RequestError, max_time=5, jitter=None)
def _wait_until_server_ready(port: int):
    response = httpx.get(f'http://127.0.0.1:{port}/ready')
    assert response.status_code == 200
