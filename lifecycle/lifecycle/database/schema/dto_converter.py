from lifecycle.database.schema import tables
from racetrack_commons.entities.dto import JobFamilyDto


def job_family_record_to_dto(model: tables.JobFamily) -> JobFamilyDto:
    return JobFamilyDto(
        id=model.id,
        name=model.name,
    )
