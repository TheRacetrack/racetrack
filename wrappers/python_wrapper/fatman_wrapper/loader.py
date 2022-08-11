import importlib.util
import inspect
import os
import sys
from importlib.abc import Loader
from pathlib import Path
from typing import Type, Optional

from fatman_wrapper.entrypoint import FatmanEntrypoint
from fatman_wrapper.forward import instantiate_host_entrypoint
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


def instantiate_entrypoint(
        model_path: str,
        class_name: Optional[str] = None,
        entrypoint_hostname: Optional[str] = None,
) -> FatmanEntrypoint:
    if entrypoint_hostname:
        return instantiate_host_entrypoint(entrypoint_hostname)
    else:
        return instantiate_class_entrypoint(model_path, class_name)


def instantiate_class_entrypoint(entrypoint_path: str, class_name: Optional[str]) -> FatmanEntrypoint:
    """
    Create Fatman Entrypoint instance from a class found in a specified Python file.
    It is done by loading the module dynamically and searching for a first defined class
     or particular one if the name was given.
    """
    sys.path.append(os.getcwd())

    assert Path(entrypoint_path).is_file(), f'{entrypoint_path} file not found'
    spec = importlib.util.spec_from_file_location("fatman", entrypoint_path)
    ext_module = importlib.util.module_from_spec(spec)
    loader: Optional[Loader] = spec.loader
    assert loader is not None, 'no module loader'
    loader.exec_module(ext_module)

    if class_name:
        assert hasattr(ext_module, class_name), f'class name {class_name} was not found'
        model_class = getattr(ext_module, class_name)
    else:
        model_class = find_entrypoint_class(ext_module)
    logger.info(f'loaded fatman class: {model_class.__name__}')
    return model_class()


def find_entrypoint_class(ext_module) -> Type[FatmanEntrypoint]:
    """
    Find a class defined in a Python module given as an entrypoint for a Job.
    This function doesn't check whether the class implements FatmanEntrypoint interface.
    The interface should be implemented implicitly, by implementing required methods.
    """
    class_members = [c[1] for c in inspect.getmembers(ext_module, inspect.isclass)]
    class_members = [c for c in class_members if c.__module__ == 'fatman']  # omit classes loaded by imports
    assert len(class_members) > 0, 'no class has been found in module'
    assert len(class_members) == 1, 'multiple classes found in a module, the name should be set explicitly.'
    return class_members[0]
