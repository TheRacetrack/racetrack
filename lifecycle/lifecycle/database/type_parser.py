import dataclasses
from datetime import datetime, timezone
from dateutil import parser as dt_parser
from typing import Type, TypeVar, Union, Any, get_origin, get_args
import types

T = TypeVar("T")


def parse_typed_object(obj: Any, clazz: Type[T]) -> T:
    """
    Cast object value to its expected type, using annotated types
    :param obj: object value to be transformed into its expected type
    :param clazz: object's expected type
    """
    if obj is None:
        return None
    
    # automatic type conversion
    if type(obj) is str and clazz is datetime:
        return dt_parser.parse(obj).replace(tzinfo=timezone.utc)
    
    if dataclasses.is_dataclass(clazz):
        assert isinstance(obj, dict), f'expected dict type to parse into a dataclass, got {type(obj)}'
        field_types = {field.name: field.type for field in dataclasses.fields(clazz)}
        dataclass_kwargs = dict()
        for key, value in obj.items():
            if key not in field_types:
                raise KeyError(f'unexpected field "{key}" provided to type {clazz}')
            dataclass_kwargs[key] = parse_typed_object(value, field_types[key])
        return clazz(**dataclass_kwargs)
    
    elif get_origin(clazz) in {Union, types.UnionType}:  # Union or Optional type
        union_types = get_args(clazz)
        left_types = []
        for union_type in union_types:
            if dataclasses.is_dataclass(union_type):
                if obj is not None:
                    return parse_typed_object(obj, union_type)
            elif union_type is types.NoneType:
                if obj is None:
                    return None
            else:
                left_types.append(union_type)
        if not left_types:
            raise ValueError(f'none of the union types "{clazz}" match to a given value: {obj}')
        if len(left_types) > 1:
            raise ValueError(f'too many ambiguous union types {left_types} ({clazz}) matching to a given value: {obj}')
        return parse_typed_object(obj, left_types[0])
    
    elif get_origin(clazz) is None and isinstance(obj, clazz):
        return obj
    
    else:
        try:
            return clazz(obj)
        except BaseException as e:
            raise ValueError(f'failed to parse "{obj}" ({type(obj)}) to type {clazz}: {e}')
