from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.pmr_project_mapping import PMRProjectMapping


T = TypeVar("T", bound="PMRProjectMappingQueryResponse")


@_attrs_define
class PMRProjectMappingQueryResponse:
    """
    Attributes:
        total_record_count (int | Unset): The total number of records matching the specified query filters in the
            service. Can be used with start and limit properties of QueryRequest to implement pagination.
        value (list[PMRProjectMapping] | Unset):
    """

    total_record_count: int | Unset = UNSET
    value: list[PMRProjectMapping] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        total_record_count = self.total_record_count

        value: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.value, Unset):
            value = []
            for value_item_data in self.value:
                value_item = value_item_data.to_dict()
                value.append(value_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if total_record_count is not UNSET:
            field_dict["totalRecordCount"] = total_record_count
        if value is not UNSET:
            field_dict["value"] = value

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.pmr_project_mapping import PMRProjectMapping

        d = dict(src_dict)
        total_record_count = d.pop("totalRecordCount", UNSET)

        _value = d.pop("value", UNSET)
        value: list[PMRProjectMapping] | Unset = UNSET
        if _value is not UNSET:
            value = []
            for value_item_data in _value:
                value_item = PMRProjectMapping.from_dict(value_item_data)

                value.append(value_item)

        pmr_project_mapping_query_response = cls(
            total_record_count=total_record_count,
            value=value,
        )

        pmr_project_mapping_query_response.additional_properties = d
        return pmr_project_mapping_query_response

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
