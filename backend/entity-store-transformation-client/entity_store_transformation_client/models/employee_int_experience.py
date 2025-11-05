from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.project_role import ProjectRole
from ..models.project_role_capability import ProjectRoleCapability
from ..models.project_type import ProjectType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.system_user import SystemUser


T = TypeVar("T", bound="EmployeeIntExperience")


@_attrs_define
class EmployeeIntExperience:
    """
    Attributes:
        project_name (str):
        employee_id (float):
        role (ProjectRole):
        type_ (ProjectType):
        start_date (datetime.date | None | Unset):
        end_date (datetime.date | None | Unset):
        is_current (bool | None | Unset):
        role_capability (list[ProjectRoleCapability] | Unset):
        create_time (datetime.datetime | Unset):
        update_time (datetime.datetime | None | Unset):
        role_other (None | str | Unset):
        id (UUID | Unset):
        created_by (SystemUser | Unset):
        updated_by (SystemUser | Unset):
    """

    project_name: str
    employee_id: float
    role: ProjectRole
    type_: ProjectType
    start_date: datetime.date | None | Unset = UNSET
    end_date: datetime.date | None | Unset = UNSET
    is_current: bool | None | Unset = UNSET
    role_capability: list[ProjectRoleCapability] | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    role_other: None | str | Unset = UNSET
    id: UUID | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        project_name = self.project_name

        employee_id = self.employee_id

        role = self.role.value

        type_ = self.type_.value

        start_date: None | str | Unset
        if isinstance(self.start_date, Unset):
            start_date = UNSET
        elif isinstance(self.start_date, datetime.date):
            start_date = self.start_date.isoformat()
        else:
            start_date = self.start_date

        end_date: None | str | Unset
        if isinstance(self.end_date, Unset):
            end_date = UNSET
        elif isinstance(self.end_date, datetime.date):
            end_date = self.end_date.isoformat()
        else:
            end_date = self.end_date

        is_current: bool | None | Unset
        if isinstance(self.is_current, Unset):
            is_current = UNSET
        else:
            is_current = self.is_current

        role_capability: list[int] | Unset = UNSET
        if not isinstance(self.role_capability, Unset):
            role_capability = []
            for role_capability_item_data in self.role_capability:
                role_capability_item = role_capability_item_data.value
                role_capability.append(role_capability_item)

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        update_time: None | str | Unset
        if isinstance(self.update_time, Unset):
            update_time = UNSET
        elif isinstance(self.update_time, datetime.datetime):
            update_time = self.update_time.isoformat()
        else:
            update_time = self.update_time

        role_other: None | str | Unset
        if isinstance(self.role_other, Unset):
            role_other = UNSET
        else:
            role_other = self.role_other

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        created_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.created_by, Unset):
            created_by = self.created_by.to_dict()

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ProjectName": project_name,
                "EmployeeID": employee_id,
                "Role": role,
                "Type": type_,
            }
        )
        if start_date is not UNSET:
            field_dict["StartDate"] = start_date
        if end_date is not UNSET:
            field_dict["EndDate"] = end_date
        if is_current is not UNSET:
            field_dict["IsCurrent"] = is_current
        if role_capability is not UNSET:
            field_dict["RoleCapability"] = role_capability
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if role_other is not UNSET:
            field_dict["RoleOther"] = role_other
        if id is not UNSET:
            field_dict["Id"] = id
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.system_user import SystemUser

        d = dict(src_dict)
        project_name = d.pop("ProjectName")

        employee_id = d.pop("EmployeeID")

        role = ProjectRole(d.pop("Role"))

        type_ = ProjectType(d.pop("Type"))

        def _parse_start_date(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                start_date_type_0 = isoparse(data).date()

                return start_date_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        start_date = _parse_start_date(d.pop("StartDate", UNSET))

        def _parse_end_date(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                end_date_type_0 = isoparse(data).date()

                return end_date_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        end_date = _parse_end_date(d.pop("EndDate", UNSET))

        def _parse_is_current(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        is_current = _parse_is_current(d.pop("IsCurrent", UNSET))

        _role_capability = d.pop("RoleCapability", UNSET)
        role_capability: list[ProjectRoleCapability] | Unset = UNSET
        if _role_capability is not UNSET:
            role_capability = []
            for role_capability_item_data in _role_capability:
                role_capability_item = ProjectRoleCapability(role_capability_item_data)

                role_capability.append(role_capability_item)

        _create_time = d.pop("CreateTime", UNSET)
        create_time: datetime.datetime | Unset
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

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

        def _parse_role_other(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        role_other = _parse_role_other(d.pop("RoleOther", UNSET))

        _id = d.pop("Id", UNSET)
        id: UUID | Unset
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

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

        employee_int_experience = cls(
            project_name=project_name,
            employee_id=employee_id,
            role=role,
            type_=type_,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
            role_capability=role_capability,
            create_time=create_time,
            update_time=update_time,
            role_other=role_other,
            id=id,
            created_by=created_by,
            updated_by=updated_by,
        )

        employee_int_experience.additional_properties = d
        return employee_int_experience

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
