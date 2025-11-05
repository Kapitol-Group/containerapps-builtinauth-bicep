from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.query_filter import QueryFilter


T = TypeVar("T", bound="QueryFilterGroup")


@_attrs_define
class QueryFilterGroup:
    """
    Attributes:
        logical_operator (int | Unset): Specifies if All (AND) or Any (OR) filters and filter groups should be used to
            filter records. Use 0 for All (AND) and 1 for Any (OR). Default is 0. Default: 0.
        query_filters (list[QueryFilter] | Unset):
        filter_groups (list[QueryFilterGroup] | Unset):
    """

    logical_operator: int | Unset = 0
    query_filters: list[QueryFilter] | Unset = UNSET
    filter_groups: list[QueryFilterGroup] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        logical_operator = self.logical_operator

        query_filters: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.query_filters, Unset):
            query_filters = []
            for query_filters_item_data in self.query_filters:
                query_filters_item = query_filters_item_data.to_dict()
                query_filters.append(query_filters_item)

        filter_groups: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.filter_groups, Unset):
            filter_groups = []
            for filter_groups_item_data in self.filter_groups:
                filter_groups_item = filter_groups_item_data.to_dict()
                filter_groups.append(filter_groups_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if logical_operator is not UNSET:
            field_dict["logicalOperator"] = logical_operator
        if query_filters is not UNSET:
            field_dict["queryFilters"] = query_filters
        if filter_groups is not UNSET:
            field_dict["filterGroups"] = filter_groups

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.query_filter import QueryFilter

        d = dict(src_dict)
        logical_operator = d.pop("logicalOperator", UNSET)

        _query_filters = d.pop("queryFilters", UNSET)
        query_filters: list[QueryFilter] | Unset = UNSET
        if _query_filters is not UNSET:
            query_filters = []
            for query_filters_item_data in _query_filters:
                query_filters_item = QueryFilter.from_dict(query_filters_item_data)

                query_filters.append(query_filters_item)

        _filter_groups = d.pop("filterGroups", UNSET)
        filter_groups: list[QueryFilterGroup] | Unset = UNSET
        if _filter_groups is not UNSET:
            filter_groups = []
            for filter_groups_item_data in _filter_groups:
                filter_groups_item = QueryFilterGroup.from_dict(filter_groups_item_data)

                filter_groups.append(filter_groups_item)

        query_filter_group = cls(
            logical_operator=logical_operator,
            query_filters=query_filters,
            filter_groups=filter_groups,
        )

        query_filter_group.additional_properties = d
        return query_filter_group

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
