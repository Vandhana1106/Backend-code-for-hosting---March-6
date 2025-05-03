# db_router.py
from threading import local

class RoundRobinRouter:
    _state = local()

    def __init__(self):
        self.databases = ['default', 'replica1', 'replica2']
        if not hasattr(self._state, 'index'):
            self._state.index = 0

    def db_for_read(self, model, **hints):
        db = self.databases[self._state.index]
        self._state.index = (self._state.index + 1) % len(self.databases)
        return db

    def db_for_write(self, model, **hints):
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'default'
