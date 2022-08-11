from racetrack_commons.api.response import ResponseJSONEncoder, register_response_json_encoder

from pydantic.json import ENCODERS_BY_TYPE


class FatmanJSONEncoder(ResponseJSONEncoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            import numpy as np

            self.numpy_array = np.ndarray
        except ModuleNotFoundError:
            self.numpy_array = None

    def default(self, o):
        if self.numpy_array is not None and isinstance(o, self.numpy_array):
            return o.tolist()
        return super().default(o)


def register_fatman_json_encoder():
    register_response_json_encoder()

    try:
        import numpy as np
        ENCODERS_BY_TYPE[np.ndarray] = lambda o: o.tolist()
    except ModuleNotFoundError:
        pass
