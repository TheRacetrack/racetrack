from contextlib import contextmanager


class ContextError(RuntimeError):
    """
    Error wrapping other error, adding context message
    and printing it in a Go manner - from most general to the real cause,
    eg: 'initializing app: loading config: file is missing'

    Usage:
        try:
            raise RuntimeError('file is missing')
        except Exception as e:
            raise ContextError('loading config') from e
    """

    def __init__(self, context_message: str, cause: BaseException = None):
        super().__init__()
        self.context_message = context_message
        if cause is not None:
            self.__cause__ = cause

    def __str__(self):
        if self.__cause__ is None:
            return self.context_message
        else:
            return f'{self.context_message}: {self.__cause__}'


@contextmanager
def wrap_context(context_name: str):
    """Apply context to occurred errors and propagate them further"""
    try:
        yield
    except Exception as e:
        raise ContextError(context_name) from e
