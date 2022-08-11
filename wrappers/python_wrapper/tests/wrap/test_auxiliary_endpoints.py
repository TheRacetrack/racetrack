from typing import Callable, Dict
from fatman_wrapper.api import create_api_app
from fatman_wrapper.health import HealthState
from fastapi.testclient import TestClient


def test_auxiliary_endpoints():
    class TestEntrypoint:
        def perform(self, x: float, y: float) -> float:
            """
            Add numbers.
            :param x: First element to add.
            :param y: Second element to add.
            :return: Sum of the numbers.
            """
            return x + y

        def auxiliary_endpoints(self) -> Dict[str, Callable]:
            return {
                '/explain': self.explain,
                '/random': self.random,
            }

        def explain(self, x: float, y: float) -> Dict[str, float]:
            """
            Explain feature importance of a model result.
            :param x: First element to add.
            :param y: Second element to add.
            :return: Dict of feature importance.
            """
            result = self.perform(x, y)
            return {'x_importance': x / result, 'y_importance': y / result}

        def random(self) -> float:
            """Return random number"""
            return 4  # chosen by fair dice roll

        def docs_input_examples(self) -> Dict[str, Dict]:
            return {
                '/perform': {
                    'x': 40,
                    'y': 2,
                },
                '/explain': {
                    'x': 1,
                    'y': 2,
                },
                '/random': {},
            }

    entrypoint = TestEntrypoint()
    fastapi_app = create_api_app(entrypoint, HealthState(live=True, ready=True))

    client = TestClient(fastapi_app)

    response = client.post(
        "/api/v1/perform",
        json={"x": 40, "y": 2},
    )
    assert response.status_code == 200
    assert response.json() == 42

    response = client.post(
        "/api/v1/explain",
        json={"x": 2, "y": 8},
    )
    assert response.status_code == 200
    assert response.json() == {'x_importance': 0.2, 'y_importance': 0.8}

    response = client.post(
        "/api/v1/random",
        json={},
    )
    assert response.status_code == 200
    assert response.json() == 4
