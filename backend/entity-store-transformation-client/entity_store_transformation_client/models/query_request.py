from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.query_filter_group import QueryFilterGroup
    from ..models.sort_option import SortOption


T = TypeVar("T", bound="QueryRequest")


@_attrs_define
class QueryRequest:
    """
    Attributes:
        selected_fields (list[str] | Unset): (Optional) Specifies the list of fields to be returned for each record from
            the query. If left as null or the list is empty, all fields for the record will be returned. Default is null.
        filter_group (QueryFilterGroup | Unset):
        start (int | Unset): (Optional) Specifies the number of records to skip before starting to return records from
            the query. Can be used along with limit property to implement pagination. Default value is 0 if not specified.
            The default sort order is based on Id field, use sortOptions to change the sort order.
        limit (int | Unset): (Optional) Specifies the maximum number of records to read from service. Can be used along
            with start property to implement pagination. Default value is 100 if not specified. The maximum value can be
            1000.
        sort_options (list[SortOption] | Unset): (Optional) Specifies the list of fields used to sort returned records.
            The default sort order is based on Id field if sortOptions are not provided.
    """

    selected_fields: list[str] | Unset = UNSET
    filter_group: QueryFilterGroup | Unset = UNSET
    start: int | Unset = UNSET
    limit: int | Unset = UNSET
    sort_options: list[SortOption] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        selected_fields: list[str] | Unset = UNSET
        if not isinstance(self.selected_fields, Unset):
            selected_fields = self.selected_fields

        filter_group: dict[str, Any] | Unset = UNSET
        if not isinstance(self.filter_group, Unset):
            filter_group = self.filter_group.to_dict()

        start = self.start

        limit = self.limit

        sort_options: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.sort_options, Unset):
            sort_options = []
            for sort_options_item_data in self.sort_options:
                sort_options_item = sort_options_item_data.to_dict()
                sort_options.append(sort_options_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if selected_fields is not UNSET:
            field_dict["selectedFields"] = selected_fields
        if filter_group is not UNSET:
            field_dict["filterGroup"] = filter_group
        if start is not UNSET:
            field_dict["start"] = start
        if limit is not UNSET:
            field_dict["limit"] = limit
        if sort_options is not UNSET:
            field_dict["sortOptions"] = sort_options

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.query_filter_group import QueryFilterGroup
        from ..models.sort_option import SortOption

        d = dict(src_dict)
        selected_fields = cast(list[str], d.pop("selectedFields", UNSET))

        _filter_group = d.pop("filterGroup", UNSET)
        filter_group: QueryFilterGroup | Unset
        if isinstance(_filter_group, Unset):
            filter_group = UNSET
        else:
            filter_group = QueryFilterGroup.from_dict(_filter_group)

        start = d.pop("start", UNSET)

        limit = d.pop("limit", UNSET)

        _sort_options = d.pop("sortOptions", UNSET)
        sort_options: list[SortOption] | Unset = UNSET
        if _sort_options is not UNSET:
            sort_options = []
            for sort_options_item_data in _sort_options:
                sort_options_item = SortOption.from_dict(sort_options_item_data)

                sort_options.append(sort_options_item)

        query_request = cls(
            selected_fields=selected_fields,
            filter_group=filter_group,
            start=start,
            limit=limit,
            sort_options=sort_options,
        )

        query_request.additional_properties = d
        return query_request

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
