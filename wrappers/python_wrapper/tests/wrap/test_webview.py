import os

from fastapi.testclient import TestClient
import pytest

from fatman_wrapper.wrapper import create_entrypoint_app


@pytest.fixture(scope="function")
def revert_workdir():
    workdir = os.getcwd()
    yield
    os.chdir(workdir)


def test_requesting_webview_pages(revert_workdir):
    os.chdir('sample/webview')
    os.environ['FATMAN_NAME'] = 'skynet'
    os.environ['FATMAN_VERSION'] = '0.0.1'
    api_app = create_entrypoint_app('webview_model.py', class_name='FatmanEntrypoint')

    client = TestClient(api_app)

    response = client.get('/pub/fatman/skynet/0.0.1/api/v1/webview')
    assert response.status_code == 200, 'webview without a slash is forwarded automatically'
    html = response.text
    assert 'Hello world. Here\'s a webview' in html, 'webview returns HTML'

    response = client.get('/pub/fatman/skynet/0.0.1/api/v1/webview/')
    assert response.status_code == 200
    html = response.text
    assert 'Hello world. Here\'s a webview' in html, 'webview returns HTML'
    assert 'href="/pub/fatman/skynet/0.0.1/api/v1/webview/static/style.css"' in html, 'links in HTML have valid prefixes'

    response = client.get('/pub/fatman/skynet/latest/api/v1/webview/')
    assert response.status_code == 200
    html = response.text
    assert 'Hello world. Here\'s a webview' in html, 'webview can be called by latest version'

    response = client.get('/pub/fatman/skynet/latest/api/v1/webview/static/style.css')
    assert response.status_code == 200
    content = response.text
    assert 'background-color' in content, 'static resources are served'
