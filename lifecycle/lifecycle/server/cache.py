from racetrack_client.log.context_error import wrap_context
from racetrack_commons.deploy.job_type import JobType, gather_job_types
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.config import Config
from lifecycle.infrastructure.model import InfrastructureTarget
from lifecycle.database.base_engine import DbEngine
from lifecycle.database.engine_factory import create_db_engine
from lifecycle.database.record_mapper import RecordMapper


class LifecycleCache:
    infrastructure_targets: dict[str, InfrastructureTarget] = {}
    job_types: dict[str, JobType] = {}
    config: Config = Config()
    _db_engine: DbEngine | None = None
    _record_mapper: RecordMapper | None = None

    @classmethod
    def on_plugins_reload(cls, plugin_engine: PluginEngine):
        with wrap_context('gathering infrastructure targets'):
            cls.infrastructure_targets = {}
            for result in plugin_engine.invoke_plugin_hook(PluginCore.infrastructure_targets):
                if result:
                    cls.infrastructure_targets.update(result)

        with wrap_context('gathering available job types'):
            cls.job_types = gather_job_types(plugin_engine)

    @classmethod
    def db_engine(cls) -> DbEngine:
        if cls._db_engine is None:
            cls._db_engine = create_db_engine()
        return cls._db_engine

    @classmethod
    def record_mapper(cls) -> RecordMapper:
        if cls._record_mapper is None:
            cls._record_mapper = RecordMapper(cls.db_engine())
        return cls._record_mapper
