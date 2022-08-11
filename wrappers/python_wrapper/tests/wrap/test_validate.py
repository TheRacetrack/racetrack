import pytest

from fatman_wrapper.entrypoint import FatmanEntrypoint
from fatman_wrapper.validate import validate_entrypoint


def test_docs_input_example_not_serializable():
    class TestEntrypoint(FatmanEntrypoint):
        def perform(self, **kwargs):
            pass

        def docs_input_example(self):
            return {"input": "image bytes".encode()}

    entrypoint = TestEntrypoint()

    with pytest.raises(RuntimeError) as excinfo:
        validate_entrypoint(entrypoint)
    assert 'invalid docs input example' in str(excinfo.value)
    assert 'failed to encode input example (for /perform endpoint) to JSON' in str(excinfo.value)
    assert 'Object of type bytes is not JSON serializable' in str(excinfo.value)


def test_docs_input_example_over_maximum_size():
    class TestEntrypoint(FatmanEntrypoint):
        def perform(self, **kwargs):
            pass

        def docs_input_example(self):
            return {"input": "toolooooong" * 100_000}

    entrypoint = TestEntrypoint()

    with pytest.raises(RuntimeError) as excinfo:
        validate_entrypoint(entrypoint)
    assert 'invalid docs input example' in str(excinfo.value)
    assert 'exceeds maximum size' in str(excinfo.value)


def test_docs_input_example_not_a_dict():
    class TestEntrypoint(FatmanEntrypoint):
        def perform(self, **kwargs):
            pass

        def docs_input_example(self):
            return "not-a-dict"

    entrypoint = TestEntrypoint()

    with pytest.raises(RuntimeError) as excinfo:
        validate_entrypoint(entrypoint)
    assert 'input example (for /perform endpoint) is not a dict' in str(excinfo.value)
