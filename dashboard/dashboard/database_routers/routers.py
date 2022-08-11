import os

"""
Routers for exclusively SQLite or Postgres deployment.

Reference: https://docs.djangoproject.com/en/3.2/topics/db/multi-db/#automatic-database-routing
"""


class Router:
    def __init__(self):
        self.db_type = os.environ.get('DJANGO_DB_TYPE', 'sqlite')

    def db_for_read(self, model, **hints):
        return self.db_type

    def db_for_write(self, model, **hints):
        return self.db_type

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
