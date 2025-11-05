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


T = TypeVar("T", bound="PMRBuildingPermitStatus")


@_attrs_define
class PMRBuildingPermitStatus:
    """
    Attributes:
        project_code (None | str | Unset):
        building_permit_number (None | str | Unset):
        title (None | str | Unset):
        status (None | str | Unset):
        update_time (datetime.datetime | None | Unset):
        created_by (SystemUser | Unset):
        updated_by (SystemUser | Unset):
        id (UUID | Unset):
        create_time (datetime.datetime | Unset):
    """

    project_code: None | str | Unset = UNSET
    building_permit_number: None | str | Unset = UNSET
    title: None | str | Unset = UNSET
    status: None | str | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    id: UUID | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        project_code: None | str | Unset
        if isinstance(self.project_code, Unset):
            project_code = UNSET
        else:
            project_code = self.project_code

        building_permit_number: None | str | Unset
        if isinstance(self.building_permit_number, Unset):
            building_permit_number = UNSET
        else:
            building_permit_number = self.building_permit_number

        title: None | str | Unset
        if isinstance(self.title, Unset):
            title = UNSET
        else:
            title = self.title

        status: None | str | Unset
        if isinstance(self.status, Unset):
            status = UNSET
        else:
            status = self.status

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

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if project_code is not UNSET:
            field_dict["ProjectCode"] = project_code
        if building_permit_number is not UNSET:
            field_dict["BuildingPermitNumber"] = building_permit_number
        if title is not UNSET:
            field_dict["Title"] = title
        if status is not UNSET:
            field_dict["Status"] = status
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by
        if id is not UNSET:
            field_dict["Id"] = id
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.system_user import SystemUser

        d = dict(src_dict)

        def _parse_project_code(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        project_code = _parse_project_code(d.pop("ProjectCode", UNSET))

        def _parse_building_permit_number(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        building_permit_number = _parse_building_permit_number(d.pop("BuildingPermitNumber", UNSET))

        def _parse_title(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        title = _parse_title(d.pop("Title", UNSET))

        def _parse_status(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        status = _parse_status(d.pop("Status", UNSET))

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

        _create_time = d.pop("CreateTime", UNSET)
        create_time: datetime.datetime | Unset
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        pmr_building_permit_status = cls(
            project_code=project_code,
            building_permit_number=building_permit_number,
            title=title,
            status=status,
            update_time=update_time,
            created_by=created_by,
            updated_by=updated_by,
            id=id,
            create_time=create_time,
        )

        pmr_building_permit_status.additional_properties = d
        return pmr_building_permit_status

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
