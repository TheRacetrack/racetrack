import os
from typing import Dict, Any, List

import requests


class FatmanEntrypoint:
    def perform(self, numbers: List[float]) -> float:
        """Round result from another model"""
        partial = self.call_fatman('adder', '/api/v1/perform', {'numbers': numbers})
        return round(partial)

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {
            'numbers': [0.2, 0.9],
        }

    def call_fatman(
        self,
        fatman_name: str,
        path: str = '/api/v1/perform',
        payload: Dict = None,
        version: str = 'latest',
    ) -> Any:
        try:
            src_fatman = os.environ['FATMAN_NAME']
            internal_pub_url = os.environ['PUB_URL']
            url = f'{internal_pub_url}/fatman/{fatman_name}/{version}{path}'

            tracing_header = os.environ.get('REQUEST_TRACING_HEADER', 'X-Request-Tracing-Id')
            if hasattr(self, 'request_context'):
                request = getattr(self, 'request_context').get()
                tracing_id = request.headers.get(tracing_header) or ''
            else:
                tracing_id = ''

            r = requests.post(url, json=payload, headers={
                'X-Racetrack-Auth': os.environ['AUTH_TOKEN'],
                tracing_header: tracing_id,
            })
            r.raise_for_status()
            return r.json()
            
        except requests.HTTPError as e:
            raise RuntimeError(f'failed to call fatman "{fatman_name} {version}" by {src_fatman}: {e}: {e.response.text}') from e
        except BaseException as e:
            raise RuntimeError(f'failed to call fatman "{fatman_name} {version}" by {src_fatman}: {e}') from e
