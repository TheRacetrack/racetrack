import psutil

from image_builder.config.config import Config
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.shell import shell

logger = get_logger(__name__)


def prune_build_cache(config: Config):
    if not config.build_cache_retention_hours:
        return

    if is_any_image_building():
        logger.info('build cache pruning skipped because there are active builds')
        return

    logger.info('pruning build cache...')

    shell(f'docker system prune -a --filter "until={config.build_cache_retention_hours}h" --force')


def is_any_image_building() -> bool:
    for proc in psutil.process_iter():
        try:
            cmdline = ' '.join(proc.cmdline())
        except psutil.NoSuchProcess:
            continue
        if cmdline.startswith('docker build'):
            return True
    return False
