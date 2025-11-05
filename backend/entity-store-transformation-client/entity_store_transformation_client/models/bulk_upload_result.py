from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="BulkUploadResult")


@_attrs_define
class BulkUploadResult:
    """
    Attributes:
        total_records (int | Unset): The total number of records to be uploaded to Data Service.
        inserted_records (int | Unset): The total number of records uploaded to Data Service.
        error_file_link (str | Unset): The file link for bulk upload error.
    """

    total_records: int | Unset = UNSET
    inserted_records: int | Unset = UNSET
    error_file_link: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        total_records = self.total_records

        inserted_records = self.inserted_records

        error_file_link = self.error_file_link

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if total_records is not UNSET:
            field_dict["totalRecords"] = total_records
        if inserted_records is not UNSET:
            field_dict["insertedRecords"] = inserted_records
        if error_file_link is not UNSET:
            field_dict["errorFileLink"] = error_file_link

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        total_records = d.pop("totalRecords", UNSET)

        inserted_records = d.pop("insertedRecords", UNSET)

        error_file_link = d.pop("errorFileLink", UNSET)

        bulk_upload_result = cls(
            total_records=total_records,
            inserted_records=inserted_records,
            error_file_link=error_file_link,
        )

        bulk_upload_result.additional_properties = d
        return bulk_upload_result

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
