from inspect import getfullargspec
from typing import Callable, Dict, Any

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


def safe_call(function: Callable, **kwargs):
    """
    Call a function with arguments, keeping backwards-compatibility between caller and the implementation.
    Omit redundant arguments that are absent in the function signature.
    Particularly useful, when caller passes additional arguments to the plugin, but plugin uses older interface.
    """
    args, varargs, _, defaults, kwonlyargs, kwonlydefaults, annotations = getfullargspec(function)
    expected_arguments: set[str] = set()  # arguments declared in the function implementation
    for arg in args:
        expected_arguments.add(arg)
    if varargs is not None:
        expected_arguments.add(varargs)
    for arg in kwonlyargs:
        expected_arguments.add(arg)

    adjusted_kwargs: Dict[str, Any] = kwargs.copy()
    for key in kwargs.keys():
        if key not in expected_arguments:
            del adjusted_kwargs[key]
            logger.warning(f'Omitting argument "{key}" that is missing in the implementation of "{function.__name__}"')

    return function(**adjusted_kwargs)
