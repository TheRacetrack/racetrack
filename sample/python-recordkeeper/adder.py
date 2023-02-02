import uuid
import os
from typing import List

from rkclient import RKClient, RKClientFactory


def get_rkclient() -> RKClient:
    model_emitter_id = uuid.UUID('b5127931-4b71-1553-a300-329edf580ffd')
    rk_host = os.environ.get('RK_HOST', 'http://127.0.0.1:8082')
    return RKClientFactory.get(rk_host, model_emitter_id)


class AdderModel:

    def perform(self, numbers: List[float]) -> float:
        """
        Add numbers.
        :param numbers: Numbers to add.
        :return: Sum of the numbers.
        """
        rkclient = get_rkclient()
        deployment_pem_id = os.environ.get("JOB_DEPLOYMENT_PEM_ID")
        if not deployment_pem_id:
            print("Warning, not found JOB_DEPLOYMENT_PEM_ID")
        else:
            deployment_pem_id = uuid.UUID(deployment_pem_id)

        pem = rkclient.prepare_pem('racetrack:adder_model_called', predecessor_id=deployment_pem_id)
        rkclient.send_pem(pem)

        return sum(numbers)

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {
            'numbers': [40, 2],
        }
