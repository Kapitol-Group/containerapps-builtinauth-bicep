from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="QueryFilter")


@_attrs_define
class QueryFilter:
    """
    Attributes:
        field_name (str | Unset): Specifies the name of the field for filter operation.
        operator (str | Unset): Specifies the operator used for filter operation. Supported operators include: contains,
            not contains, startswith, endswith, =, !=, >, <, >=, <=, in, not in. Not all operators are supported for all
            field types.
        value (str | Unset): Specifies the value to use for the filter operation. An empty value with '=' operator does
            a null check and with '!=' operator does a not null check.
    """

    field_name: str | Unset = UNSET
    operator: str | Unset = UNSET
    value: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        field_name = self.field_name

        operator = self.operator

        value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if field_name is not UNSET:
            field_dict["fieldName"] = field_name
        if operator is not UNSET:
            field_dict["operator"] = operator
        if value is not UNSET:
            field_dict["value"] = value

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        field_name = d.pop("fieldName", UNSET)

        operator = d.pop("operator", UNSET)

        value = d.pop("value", UNSET)

        query_filter = cls(
            field_name=field_name,
            operator=operator,
            value=value,
        )

        query_filter.additional_properties = d
        return query_filter

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
