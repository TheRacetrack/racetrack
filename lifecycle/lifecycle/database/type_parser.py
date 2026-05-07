import dataclasses
import json
from datetime import datetime, timezone
from dateutil import parser as dt_parser
from typing import Type, TypeGuard, TypeVar, Union, Any, cast, get_origin, get_args, overload
import types

from racetrack_client.log.context_error import ContextError


T = TypeVar("T")


# there is a lie here - UnionType is not strictly a 'type', but in ways important to us it does behave like it
def is_type_or_union(field_type: Any) -> TypeGuard[type]:
    if isinstance(field_type, type):
        return True
    return get_origin(field_type) in {Union, types.UnionType}


# overload definitions are strictly for typing only
@overload
def parse_typed_object(obj: None, clazz: Type[T]) -> None:
    ...


@overload
def parse_typed_object(obj: Any, clazz: Type[T]) -> T:
    ...


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
        # typing has issues understanding type narrowing and does not understand that T==datetime
        return cast(T, dt_parser.parse(obj).replace(tzinfo=timezone.utc))

    if dataclasses.is_dataclass(clazz):
        assert isinstance(obj, dict), f'expected dict type to parse into a dataclass, got {type(obj)}'
        field_types = {field.name: field.type for field in dataclasses.fields(clazz)}
        dataclass_kwargs: dict[Any, Any] = dict()
        for key, value in obj.items():
            if key not in field_types:
                raise KeyError(f'unexpected field "{key}" provided to type {clazz}')

            field_type = field_types[key]
            if not is_type_or_union(field_type):
                raise KeyError(f'field types need to be actual instances of \'type\', but field type for {key} is {field_type!r} {type(field_type).__name__}')

            dataclass_kwargs[key] = parse_typed_object(value, field_type)
        # after type narrowing typing lost information that clazz is type[T]
        return cast(T, clazz(**dataclass_kwargs))

    elif get_origin(clazz) in {Union, types.UnionType}:  # Union or Optional type
        union_types = get_args(clazz)
        left_types = []
        for union_type in union_types:
            if dataclasses.is_dataclass(union_type) and isinstance(union_type, type):
                return parse_typed_object(obj, union_type)
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
        return obj

    else:
        try:
            # mypy loses all context here treating clazz as object and believes you cannot call it with argument
            return clazz(obj)  # type: ignore[call-arg]
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

        field_type = field_types[key]
        if not is_type_or_union(field_type):
            raise KeyError(f'field types need to be actual instances of \'type\', but field type for {key} is {field_type!r} {type(field_type).__name__}')

        typed_data[key] = parse_typed_object(value, field_type)
    return typed_data


def parse_json_column(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ContextError(f'Unparsable JSON content ({text})') from e
