class EntityNotFound(RuntimeError):
    pass


class AlreadyExists(RuntimeError):
    pass


class ValidationError(RuntimeError):
    pass

class IncompatibleOptions(RuntimeError):
    pass
