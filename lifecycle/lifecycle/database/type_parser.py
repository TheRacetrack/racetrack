import dataclasses
import json
from datetime import datetime, timezone
from dateutil import parser as dt_parser
from typing import Type, TypeVar, Union, Any, cast, get_origin, get_args
import types

from racetrack_client.log.context_error import ContextError


T = TypeVar("T")
U = TypeVar("U")

def parse_typed_object(obj: Any, clazz: Type[T]) -> T | None:
    """
    Cast object value to its expected type, using annotated types
    :param obj: object value to be transformed into its expected type
    :param clazz: object's expected type
    """
    if obj is None:
        return None
    
    # automatic type conversion
    if type(obj) is str and clazz is datetime:
        return cast(T, dt_parser.parse(obj).replace(tzinfo=timezone.utc))
    
    if dataclasses.is_dataclass(clazz):
        assert isinstance(obj, dict), f'expected dict type to parse into a dataclass, got {type(obj)}'
        field_types = {field.name: field.type for field in dataclasses.fields(clazz)}
        dataclass_kwargs: dict[Any, Any] = dict()
        for key, value in obj.items():
            if key not in field_types:
                raise KeyError(f'unexpected field "{key}" provided to type {clazz}')

            field_type = cast(type, field_types[key])

            dataclass_kwargs[key] = parse_typed_object(value, field_type)
        return cast(T, clazz(**dataclass_kwargs))
    
    elif get_origin(clazz) in {Union, types.UnionType}:  # Union or Optional type
        union_types = get_args(clazz)
        left_types = []
        for union_type in union_types:
            if dataclasses.is_dataclass(union_type):
                return parse_typed_object(obj, cast(type[T], union_type))
            elif union_type is types.NoneType:
                continue
            else:
                left_types.append(union_type)
        if not left_types:
            raise ValueError(f'none of the union types "{clazz}" match to a given value: {obj}')
        if len(left_types) > 1:
            raise ValueError(f'too many ambiguous union types {left_types} ({clazz}) matching to a given value: {obj}')
        return parse_typed_object(obj, left_types[0])
    
    elif get_origin(clazz) is None and isinstance(obj, clazz):
        return cast(T, obj)
    
    else:
        try:
            return clazz(obj) #type: ignore
        except BaseException as e:
            raise ValueError(f'failed to parse "{obj}" ({type(obj)}) to type {clazz}: {e}')


def parse_dict_typed_values(data: dict[str, Any], clazz: Type[T]) -> dict[str, Any]:
    """
    Cast dictionary values to the expected types, matching the field annotations from a dataclass
    :param data: fields dictionary to be transformed into expected type. It doesn't need to contain all dataclass fields
    :param clazz: expected dataclass type to take the fields from
    :return: dictionary with the same keys as the input, but with values casted to the expected types
    """
    if not data:
        return {}
    assert dataclasses.is_dataclass(clazz), f'expected dataclass type to parse into a dict, got {clazz}'
    field_types = {field.name: field.type for field in dataclasses.fields(clazz)}
    typed_data: dict[str, Any] = dict()
    for key, value in data.items():
        if key not in field_types:
            raise KeyError(f'unexpected field "{key}" provided for type {clazz}')

        field_type = cast(type, field_types[key])

        typed_data[key] = parse_typed_object(value, field_type)
    return typed_data


def parse_json_column(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ContextError(f'Unparsable JSON content ({text})') from e
