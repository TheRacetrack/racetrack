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
    new_request_body: bytes = dto.request_body.encode()
    new_response_body: bytes = dto.response_body.encode()

    if model.status != dto.status \
            or model.started_at != new_started_at \
            or model.ended_at != new_ended_at \
            or model.error != dto.error \
            or model.job_name != dto.job_name \
            or model.job_version != dto.job_version \
            or model.job_path != dto.job_path \
            or model.request_method != dto.request_method \
            or model.request_url != dto.request_url \
            or model.request_headers != dto.request_headers \
            or model.request_body != new_request_body \
            or model.response_status_code != dto.response_status_code \
            or model.response_headers != dto.response_headers \
            or model.response_body != new_response_body \
            or model.attempts != dto.attempts \
            or model.pub_instance_addr != dto.pub_instance_addr:
        changed = True
    model.status = dto.status
    model.started_at = new_started_at
    model.ended_at = new_ended_at
    model.error = dto.error
    model.job_name = dto.job_name
    model.job_version = dto.job_version
    model.job_path = dto.job_path
    model.request_method = dto.request_method
    model.request_url = dto.request_url
    model.request_headers = dto.request_headers
    model.request_body = new_request_body
    model.response_status_code = dto.response_status_code
    model.response_headers = dto.response_headers
    model.response_body = new_response_body
    model.attempts = dto.attempts
    model.pub_instance_addr = dto.pub_instance_addr

    if changed:
        try:
            model.save(force_update=True)
        except models.AsyncJobCall.DoesNotExist:
            raise EntityNotFound(f'Async job call model has gone before updating: {model}')
    return model


def delete_async_job_call(call_id: str):
    model = get_async_job_call(call_id)
    model.delete()
