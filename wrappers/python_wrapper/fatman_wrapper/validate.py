from fatman_wrapper.docs import get_input_example
from fatman_wrapper.entrypoint import FatmanEntrypoint, list_auxiliary_endpoints
from racetrack_client.log.context_error import wrap_context
from racetrack_commons.api.response import ResponseJSONEncoder


MAX_INPUT_EXAMPLE_JSON_SIZE = 1024 * 1024  # 1MB


def validate_entrypoint(entrypoint: FatmanEntrypoint):
    """Validate if Fatman entrypoint methods are correct. Raise exception in case of error"""
    with wrap_context('invalid docs input example'):
        _validate_docs_input_examples(entrypoint)


def _validate_docs_input_examples(entrypoint: FatmanEntrypoint):
    auxiliary_endpoints = sorted(list_auxiliary_endpoints(entrypoint).keys())
    endpoints = ['/perform'] + auxiliary_endpoints
    for endpoint in endpoints:
        _validate_docs_input_example(entrypoint, endpoint)


def _validate_docs_input_example(entrypoint: FatmanEntrypoint, endpoint: str):
    docs_input_example = get_input_example(entrypoint, endpoint)
    if not isinstance(docs_input_example, dict):
        raise RuntimeError(f'input example (for {endpoint} endpoint) is not a dict')
    with wrap_context(f'failed to encode input example (for {endpoint} endpoint) to JSON'):
        raw_json = ResponseJSONEncoder().encode(docs_input_example)
    if len(raw_json) > MAX_INPUT_EXAMPLE_JSON_SIZE:
        raise RuntimeError(f'input example (for {endpoint} endpoint) encoded to JSON ({len(raw_json)} bytes) '
                           f'exceeds maximum size ({MAX_INPUT_EXAMPLE_JSON_SIZE} bytes)')
