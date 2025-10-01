from lifecycle.job.models_registry import read_job_family_model
from lifecycle.auth.subject import get_auth_subject_by_job_family, get_auth_token_by_subject


def get_job_family_jwt_token(job_name: str) -> str:
    family_model = read_job_family_model(job_name)
    auth_subject = get_auth_subject_by_job_family(family_model)
    auth_token = get_auth_token_by_subject(auth_subject)
    return auth_token.token
