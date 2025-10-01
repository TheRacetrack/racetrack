from django.db import close_old_connections


def db_access(function):
    """
    Decorator closing old, stale connections before accessing database.
    It helps to reconnect to DB properly.
    """

    def wrapper(*args, **kwargs):
        close_old_connections()
        return function(*args, **kwargs)

    return wrapper
