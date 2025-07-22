from lifecycle.deployer.base import JobDeployer
from lifecycle.infrastructure.infra_target import get_infrastructure_target


def get_job_deployer(
    infrastructure_name: str | None,
) -> JobDeployer:
    infra_target = get_infrastructure_target(infrastructure_name)

    if infra_target.job_deployer is None:
                raise ValueError("job deployer is None")

    return infra_target.job_deployer
