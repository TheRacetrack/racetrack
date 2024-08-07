from enum import Enum


class AuthSubjectType(Enum):
    USER = 'user'
    ESC = 'esc'
    JOB_FAMILY = 'job_family'
    # internal communication of Racetrack services
    # Internal tokens are not kept in a database, they're signed with the AUTH_KEY
    INTERNAL = 'internal'


class UnauthorizedError(RuntimeError):
    def __init__(self, cause: str, details: str = ''):
        super().__init__()
        self.cause = cause
        self.details = details

    def __str__(self):
        return self.describe(debug=True)

    def describe(self, debug: bool = False):
        if not debug or not self.details:
            return self.cause
        else:
            return f'{self.cause}: {self.details}'
