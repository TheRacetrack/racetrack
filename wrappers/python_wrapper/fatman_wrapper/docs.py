import inspect
from typing import Optional, Any, Dict

from fatman_wrapper.entrypoint import FatmanEntrypoint


def get_input_example(entrypoint: FatmanEntrypoint, endpoint: str = '/perform') -> Dict[str, Any]:
    """Return exemplary input for a Fatman endpoint (/perform endpoint or auxiliary endpoint)"""
    if hasattr(entrypoint, 'docs_input_examples'):
        docs_input_examples = getattr(entrypoint, 'docs_input_examples')()
        if not isinstance(docs_input_examples, dict):
            raise RuntimeError('docs_input_examples outcome is not a dict')
        if endpoint in docs_input_examples:
            return docs_input_examples[endpoint]
    if endpoint == '/perform' and hasattr(entrypoint, 'docs_input_example'):
        return getattr(entrypoint, 'docs_input_example')()
    return {}


def get_perform_docs(entrypoint: FatmanEntrypoint) -> Optional[str]:
    """Return docstring attached to a perform function"""
    if hasattr(entrypoint, 'perform'):
        perform_func = getattr(entrypoint, 'perform')
        return inspect.getdoc(perform_func)
    return None
