from typing import Dict, Callable, Any, List

from fatman_wrapper.docs import get_input_example, get_perform_docs
from fatman_wrapper.entrypoint import FatmanEntrypoint
from fatman_wrapper.loader import instantiate_class_entrypoint
from fatman_wrapper.validate import validate_entrypoint


def test_input_example():
    entrypoint = instantiate_class_entrypoint('sample/adder_model.py', 'AdderModel')
    example_input = get_input_example(entrypoint)
    assert example_input == {
        'numbers': [300, 60, 5],
        'radix': 10,
    }


def test_perform_docs():
    entrypoint = instantiate_class_entrypoint('sample/adder_model.py', 'AdderModel')
    docs = get_perform_docs(entrypoint)
    assert docs == """Add numbers.
:param numbers: Numbers to add.
:param radix: Radix of the numbers.
:return: Sum of the numbers."""


def test_input_example_of_auxiliary_endpoint():
    class TestAuxEntrypoint(FatmanEntrypoint):
        def perform(self, numbers: List[float]):
            return sum(numbers)

        def auxiliary_endpoints(self) -> Dict[str, Callable]:
            return {
                '/explain': self.explain,
            }

        def explain(self, x: float, y: float) -> Dict[str, float]:
            result = self.perform([x, y])
            return {'x_importance': x / result, 'y_importance': y / result}

        def docs_input_examples(self) -> Dict[str, Dict[str, Any]]:
            return {
                '/perform': {
                    'numbers': [300, 60, 5],
                },
                '/explain': {
                    'x': 7,
                    'y': 8,
                },
            }

    entrypoint = TestAuxEntrypoint()

    validate_entrypoint(entrypoint)
    perform_example_input = get_input_example(entrypoint, endpoint='/perform')
    assert perform_example_input == {
        'numbers': [300, 60, 5],
    }
    aux_example_input = get_input_example(entrypoint, endpoint='/explain')
    assert aux_example_input == {
        'x': 7,
        'y': 8,
    }
