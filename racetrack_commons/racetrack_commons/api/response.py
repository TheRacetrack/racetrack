import dataclasses
import json
from datetime import date, datetime
from pathlib import PosixPath

from pydantic import BaseModel
from pydantic.json import ENCODERS_BY_TYPE

from racetrack_client.utils.datamodel import convert_to_json_serializable
from racetrack_client.utils.quantity import Quantity


class ResponseJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return convert_to_json_serializable(dataclasses.asdict(o))
        if isinstance(o, BaseModel):
            return convert_to_json_serializable(o.dict())
        if isinstance(o, PosixPath):
            return str(o)
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        elif hasattr(o, '__to_json__'):
            return getattr(o, '__to_json__')()
        return super().default(o)


def register_response_json_encoder():

    ENCODERS_BY_TYPE[BaseModel] = lambda o: convert_to_json_serializable(o.dict())
    ENCODERS_BY_TYPE[PosixPath] = lambda o: str(o)
    ENCODERS_BY_TYPE[date] = lambda o: o.isoformat()
    ENCODERS_BY_TYPE[datetime] = lambda o: o.isoformat()
    ENCODERS_BY_TYPE[Quantity] = lambda o: getattr(o, '__to_json__')()
