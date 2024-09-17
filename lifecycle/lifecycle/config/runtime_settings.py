import json
from lifecycle.django.registry import models
from racetrack_client.log.errors import EntityNotFound

JsonType = dict | list | int | str | bool | None

# Runtime Settings

# whether maintenance mode is enabled or not. Boolean type.
# When enabled, users are unable to make changes. Thus, deploying jobs, deleting, moving is disabled.
MAINTENANCE_MODE = "maintenance_mode"


def read_setting(name: str) -> JsonType:
    try:
        return models.Setting.objects.get(name=name).value
    except models.Setting.DoesNotExist:
        return None


def save_setting(name: str, value: JsonType):
    model = models.Setting(
        name=name,
        value=value,
    )
    model.save()
