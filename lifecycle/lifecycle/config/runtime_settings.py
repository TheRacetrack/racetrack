import json
from lifecycle.database.schema import tables
from lifecycle.server.cache import LifecycleCache
from racetrack_client.log.errors import EntityNotFound

JsonType = dict | list | int | str | bool | None

# Runtime Settings

# whether maintenance mode is enabled or not. Boolean type.
# When enabled, users are unable to make changes. Thus, deploying jobs, deleting, moving is disabled.
MAINTENANCE_MODE = "maintenance_mode"


def read_setting(name: str) -> JsonType:
    try:
        str_val = LifecycleCache.record_mapper().find_one(tables.Setting, name=name).value
        if not str_val:
            return None
        return json.loads(str_val)
    except EntityNotFound:
        return None


def save_setting(name: str, value: JsonType):
    str_val = json.dumps(value) if value else None
    model = tables.Setting(
        name=name,
        value=str_val,
    )
    LifecycleCache.record_mapper().create_or_update(model)
