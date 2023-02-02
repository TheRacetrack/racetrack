import time
import logging

from timeout import timeout


class TimeoutJob:
    def __init__(self):
        """job to either crash or timeout for testing purposes"""

    def perform(self, mode: str = "timeout", t: int = 250) -> dict:
        """perform for timeouts or crashing

        Args:
            mode: keyword for setting job mode, can be either
            - 'timeout' (sleep for given seconds),
            - 'timeout_kill' (sleep for given seconds, but kill if too long)
            - 'crash' (raise exception)
            - 'cpu' (consume CPU for given seconds)
            t: timeout in s.

        Returns:
            out: Dict with keys for whether the job is alive or not and the timeout used.
        """

        if mode == "timeout":
            logging.info("sleeping for %s seconds", t)
            time.sleep(t)
            out = {"Alive": True, "Timeout": t}
            logging.info("Done sleeping - waking up and returning standard output")
            return out

        elif mode == "timeout_kill":
            return self.safe_compute(t)

        elif mode == "crash":
            raise Exception("Windows12 has stopped working")

        elif mode == "cpu":
            start = time.time()
            while time.time() - start < t:
                continue
            return {'t': t}

        else:
            raise RuntimeError(f"Unknown mode: {mode}")

    @timeout(10)
    def safe_compute(self, t: float) -> float:
        count = t
        while count > 0:
            print(f'Im running and consuming your CPU: {count}')
            time.sleep(1)
            count -= 1
        return t**2


    def docs_input_example(self):
        """This method should simply return a synthetic example of the input taken to perform."""
        return {"mode": "timeout", "t": 250}
