from fatman_wrapper.entrypoint import list_entrypoint_parameters
from fatman_wrapper.loader import instantiate_class_entrypoint


def test_wrapped_endpoints():
    model = instantiate_class_entrypoint('sample/adder_model.py', 'AdderModel')
    params = list_entrypoint_parameters(model)
    assert len(params) == 2
    assert params[0] == {'name': 'numbers', 'type': 'typing.List[float]'} \
        or params[0] == {'name': 'numbers', 'type': 'List'}
    assert params[1] == {'name': 'radix', 'default_value': 10, 'type': 'int'}
