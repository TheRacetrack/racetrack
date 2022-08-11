from abc import ABC, abstractmethod
from inspect import getfullargspec
from typing import Dict, List, Optional, Tuple, Iterable, Any, Callable, Mapping, Union

WsgiApplication = Callable[
    [
        Mapping[str, object],  # environ
        Callable,  # start_response() function
    ],
    Iterable[bytes]  # bytestring chunks response stream
]


class FatmanEntrypoint(ABC):
    @abstractmethod
    def perform(self, **kwargs):
        """Call model/service main action"""
        raise NotImplementedError()

    def webview_app(self, base_url: str) -> WsgiApplication:
        """
        Create WSGI app serving custom UI pages
        :param base_url Base URL prefix where WSGI app is deployed.
        """
        return None

    def docs_input_examples(self) -> Dict[str, Dict[str, Any]]:
        """Return mapping of Fatman's endpoints to corresponding exemplary inputs."""
        return {}

    def docs_input_example(self) -> Dict[str, Any]:
        """Return example input values for perform endpoint."""
        return {}

    def auxiliary_endpoints(self) -> Dict[str, Callable]:
        """Dict of custom endpoint paths (besides "/perform") handled by Entrypoint methods"""
        return {}

    def static_endpoints(self) -> Dict[str, Union[Tuple, str]]:
        """
        Dict of endpoint paths mapped to corresponding static files that ought be served.
        Value can be either filename, or tuple of filename and its mimetype
        """
        return {}

    def metrics(self) -> List[Dict]:
        """
        Collect current metrics values
        :return list of metric dicts, eg:
            [
                {
                    'name': 'fatman_is_crazy',
                    'description': 'Whether your fatman is crazy or not',
                    'value': 1,
                    'labels': {
                        'color': 'blue',
                    },
                },
            ]
        """
        return []


def perform_entrypoint(entrypoint: FatmanEntrypoint, payload: Dict[str, Any]) -> Dict:
    """Call model/service main action"""
    if entrypoint is None:
        raise ValueError('undefined entrypoint')

    if not hasattr(entrypoint, 'perform'):
        raise ValueError("entrypoint doesn't have 'perform' method implemented")

    try:
        output = entrypoint.perform(**payload)
    except TypeError as e:
        raise ValueError(f'failed to call a function: {e}')
    return output


def list_entrypoint_parameters(entrypoint: FatmanEntrypoint) -> List[Dict]:
    """Inspect entrypoint function and return names, default values, types of all function's parameters"""
    if not hasattr(entrypoint, 'perform'):
        raise ValueError("entrypoint doesn't have 'perform' method implemented")

    function = getattr(entrypoint, 'perform')
    args, varargs, _, defaults, kwonlyargs, kwonlydefaults, annotations = getfullargspec(function)
    required_params = list(_list_entrypoint_required_parameters(args, varargs, defaults, annotations))
    optional_params = list(_list_entrypoint_optional_parameters(args, defaults, kwonlyargs, kwonlydefaults, annotations))
    return required_params + optional_params


def _list_entrypoint_required_parameters(
    args: List[str],
    varargs: Optional[str],
    defaults: Optional[Tuple],
    annotations: Dict,
) -> Iterable[Dict]:
    required_args_len = len(args) - len(defaults) if defaults is not None else len(args)
    required_args = args[:required_args_len]
    if not required_args:
        return
    if required_args[0] == 'self':
        required_args = required_args[1:]

    for arg in required_args:
        yield {
            'name': arg,
            'type': _get_arg_type(annotations, arg),
        }

    if varargs is not None:
        yield {
            'name': varargs,
            'type': f'List[{_get_arg_type(annotations, varargs)}]',
        }


def _list_entrypoint_optional_parameters(
    args: List[str],
    defaults: Optional[Tuple],
    kwonlyargs: List[str],
    kwonlydefaults: Optional[Dict[str, Any]],
    annotations: Dict[str, str],
) -> Iterable[Dict]:
    required_args_len = len(args) - len(defaults) if defaults is not None else len(args)
    optional_args = args[required_args_len:]
    for i, arg in enumerate(optional_args):
        yield {
            'name': arg,
            'default_value': defaults[i] if defaults is not None else None,
            'type': _get_arg_type(annotations, arg),
        }

    if not kwonlydefaults:
        kwonlydefaults = dict()

    for arg in kwonlyargs:
        yield {
            'name': arg,
            'default_value': kwonlydefaults.get(arg),
            'type': _get_arg_type(annotations, arg),
        }


def _get_arg_type(annotations: Dict, arg: str) -> Optional[str]:
    type_annotation = annotations.get(arg)
    if type_annotation is None:
        return None
    if hasattr(type_annotation, '__name__'):
        return type_annotation.__name__
    return str(type_annotation)


def list_auxiliary_endpoints(entrypoint: FatmanEntrypoint) -> Dict[str, Callable]:
    if not hasattr(entrypoint, 'auxiliary_endpoints'):
        return {}
    return getattr(entrypoint, 'auxiliary_endpoints')()


def list_static_endpoints(entrypoint: FatmanEntrypoint) -> Dict[str, Union[Tuple, str]]:
    if not hasattr(entrypoint, 'static_endpoints'):
        return {}
    return getattr(entrypoint, 'static_endpoints')()
