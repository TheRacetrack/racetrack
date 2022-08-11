import time


class WaiterModel:
    def __init__(self) -> None:
        time.sleep(1)

    def perform(self, timeout: float) -> float:
        time.sleep(timeout)
        return timeout

    def docs_input_example(self) -> dict:
        return {
            'timeout': 3,
        }
