from contextlib import contextmanager
import time

from racetrack_client.log.context_error import ContextError
from image_builder.config import Config
from image_builder.metrics import metric_image_building_phase_duration, metric_image_building_phase_done
from image_builder.progress import update_deployment_phase


@contextmanager
def phase_context(
    phase_name: str,
    metric_labels: dict[str, str],
    deployment_id: str,
    config: Config,
    metric_phase: str | None = None,
):
    """Apply context to occurred errors and propagate them further"""
    phase_start_time = time.time()
    update_deployment_phase(config, deployment_id, phase_name)
    try:
        yield
        metric_phase = metric_phase or phase_name
        metric_image_building_phase_duration.labels(**metric_labels, phase=metric_phase).inc(time.time() - phase_start_time)
        metric_image_building_phase_done.labels(**metric_labels, phase=metric_phase).inc(1)
    except BaseException as e:
        raise ContextError(phase_name) from e
