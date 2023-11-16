from lifecycle.config.runtime_settings import read_setting, MAINTENANCE_MODE


def is_maintenance_mode() -> bool:
    setting_value = read_setting(MAINTENANCE_MODE)
    return setting_value is True


def ensure_no_maintenance():
    if is_maintenance_mode():
        raise RuntimeError('Racetrack is now in maintenance mode. Please try again later.')
