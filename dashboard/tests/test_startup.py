import asyncio
import backoff
import httpx

from dashboard.api.server import create_fastapi_app
from racetrack_client.log.logs import configure_logs
from racetrack_commons.api.asgi.asgi_server import serve_asgi_in_background
from racetrack_commons.socket import free_tcp_port


def test_api_server_startup():
    async def test_async():
        configure_logs(log_level='debug')
        port = free_tcp_port()
        app = create_fastapi_app()
        with serve_asgi_in_background(app, port):
            _wait_until_server_ready(port)

            response = httpx.get(f'http://127.0.0.1:{port}')
            assert response.status_code == 307

            response = httpx.get(f'http://127.0.0.1:{port}/live')
            assert response.status_code == 200
            assert response.json() == {'live': True, 'service': 'dashboard'}

            response = httpx.get(f'http://127.0.0.1:{port}/dashboard/api/status')
            assert response.status_code == 200
            assert response.json().get('git_version')

    asyncio.run(test_async())


@backoff.on_exception(backoff.fibo, httpx.RequestError, max_time=5, jitter=None)
def _wait_until_server_ready(port: int):
    response = httpx.get(f'http://127.0.0.1:{port}/ready')
    assert response.status_code == 200
