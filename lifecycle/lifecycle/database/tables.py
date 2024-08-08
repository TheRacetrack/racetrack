from abc import ABC
from typing import Any, Self
from dataclasses import dataclass, asdict
    

class TableModel(ABC):
    def __init__(self, **row_data):
        for field_name, value in row_data.items():
            setattr(self, field_name, value)
    
    @classmethod
    def table_name(cls) -> str:
        metadata = getattr(cls, 'Metadata')
        assert metadata is not None, f'Metadata class not specified in {self.__class__}'
        table_name = getattr(metadata, 'table_name')
        assert metadata is not None, f'table_name not specified in {self.__class__}.Metadata'
        return table_name
    
    @classmethod
    def fields(cls) -> list[str]:
        field_annotations: dict[str, type] = cls.__annotations__
        return list(field_annotations.keys())

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Self:
        return cls(**row)

    def to_row(self) -> dict[str, Any]:
        return asdict(self)
    

@dataclass
class JobFamilyTable(TableModel):
    class Metadata:
        table_name = 'registry_jobfamily'

    id: str
    name: str

    # @staticmethod
    # def from_row(row: dict[str, Any]) -> 'JobFamilyTable':
    #     return JobFamilyTable(**row)
