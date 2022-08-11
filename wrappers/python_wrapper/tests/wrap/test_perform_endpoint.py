from fatman_wrapper.wrapper import create_entrypoint_app
from fastapi.testclient import TestClient


def test_wrapped_endpoints():
    api_app = create_entrypoint_app('sample/adder_model.py', class_name='AdderModel')

    client = TestClient(api_app)

    response = client.post(
        '/api/v1/perform',
        json={'numbers': [40, 2]},
    )
    assert response.status_code == 200
    assert response.json() == 42
