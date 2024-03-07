from racetrack_client.log.errors import EntityNotFound
from racetrack_client.utils.time import timestamp_to_datetime
from racetrack_commons.entities.dto import AsyncJobCallDto
from lifecycle.django.registry import models


def get_async_job_call(call_id: str) -> models.AsyncJobCall:
    try:
        return models.AsyncJobCall.objects.get(id=call_id)
    except models.AsyncJobCall.DoesNotExist:
        raise EntityNotFound(f'Async job call with id "{call_id}" was not found')


def save_async_job_call(dto: AsyncJobCallDto) -> models.AsyncJobCall:
    changed = False
    try:
        model = get_async_job_call(dto.id)
    except EntityNotFound:
        model = models.AsyncJobCall(id=dto.id)
        changed = True

    new_started_at = timestamp_to_datetime(dto.started_at)
    new_ended_at = timestamp_to_datetime(dto.ended_at) if dto.ended_at is not None else None

    if model.status != dto.status \
            or model.started_at != new_started_at \
            or model.ended_at != new_ended_at \
            or model.error != dto.error \
            or model.job_name != dto.job_name \
            or model.job_version != dto.job_version \
            or model.job_path != dto.job_path \
            or model.url != dto.url \
            or model.method != dto.method \
            or model.request_data != dto.request_data \
            or model.response_data != dto.response_data \
            or model.response_json != dto.response_json \
            or model.response_status_code != dto.response_status_code \
            or model.pub_instance != dto.pub_instance \
            or model.attempts != dto.attempts:
        changed = True
    model.status = dto.status
    model.started_at = new_started_at
    model.ended_at = new_ended_at
    model.error = dto.error
    model.job_name = dto.job_name
    model.job_version = dto.job_version
    model.job_path = dto.job_path
    model.url = dto.url
    model.method = dto.method
    model.request_data = dto.request_data
    model.response_data = dto.response_data
    model.response_json = dto.response_json
    model.response_status_code = dto.response_status_code
    model.pub_instance = dto.pub_instance
    model.attempts = dto.attempts

    if changed:
        try:
            model.save(force_update=True)
        except models.AsyncJobCall.DoesNotExist:
            raise EntityNotFound(f'Async job call model has gone before updating: {model}')
    return model
