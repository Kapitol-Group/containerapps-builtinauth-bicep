from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.system_user import SystemUser


T = TypeVar("T", bound="DocumentUnderstandingFldTol")


@_attrs_define
class DocumentUnderstandingFldTol:
    """
    Attributes:
        porject_name (str):
        field_name (str):
        field_tolerance (float):
        updated_by (SystemUser | Unset):
        id (UUID | Unset):
        update_time (datetime.datetime | None | Unset):
        created_by (SystemUser | Unset):
        create_time (datetime.datetime | Unset):
    """

    porject_name: str
    field_name: str
    field_tolerance: float
    updated_by: SystemUser | Unset = UNSET
    id: UUID | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        porject_name = self.porject_name

        field_name = self.field_name

        field_tolerance = self.field_tolerance

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        update_time: None | str | Unset
        if isinstance(self.update_time, Unset):
            update_time = UNSET
        elif isinstance(self.update_time, datetime.datetime):
            update_time = self.update_time.isoformat()
        else:
            update_time = self.update_time

        created_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.created_by, Unset):
            created_by = self.created_by.to_dict()

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "PorjectName": porject_name,
                "FieldName": field_name,
                "FieldTolerance": field_tolerance,
            }
        )
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by
        if id is not UNSET:
            field_dict["Id"] = id
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.system_user import SystemUser

        d = dict(src_dict)
        porject_name = d.pop("PorjectName")

        field_name = d.pop("FieldName")

        field_tolerance = d.pop("FieldTolerance")

        _updated_by = d.pop("UpdatedBy", UNSET)
        updated_by: SystemUser | Unset
        if isinstance(_updated_by, Unset):
            updated_by = UNSET
        else:
            updated_by = SystemUser.from_dict(_updated_by)

        _id = d.pop("Id", UNSET)
        id: UUID | Unset
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        def _parse_update_time(data: object) -> datetime.datetime | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                update_time_type_0 = isoparse(data)

                return update_time_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None | Unset, data)

        update_time = _parse_update_time(d.pop("UpdateTime", UNSET))

        _created_by = d.pop("CreatedBy", UNSET)
        created_by: SystemUser | Unset
        if isinstance(_created_by, Unset):
            created_by = UNSET
        else:
            created_by = SystemUser.from_dict(_created_by)

        _create_time = d.pop("CreateTime", UNSET)
        create_time: datetime.datetime | Unset
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        document_understanding_fld_tol = cls(
            porject_name=porject_name,
            field_name=field_name,
            field_tolerance=field_tolerance,
            updated_by=updated_by,
            id=id,
            update_time=update_time,
            created_by=created_by,
            create_time=create_time,
        )

        document_understanding_fld_tol.additional_properties = d
        return document_understanding_fld_tol

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
