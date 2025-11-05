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


T = TypeVar("T", bound="PMRProjectMapping")


@_attrs_define
class PMRProjectMapping:
    """
    Attributes:
        project_code (None | str | Unset):
        project_stake_holder (None | str | Unset):
        create_time (datetime.datetime | Unset):
        updated_by (SystemUser | Unset):
        update_time (datetime.datetime | None | Unset):
        id (UUID | Unset):
        created_by (SystemUser | Unset):
    """

    project_code: None | str | Unset = UNSET
    project_stake_holder: None | str | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    id: UUID | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        project_code: None | str | Unset
        if isinstance(self.project_code, Unset):
            project_code = UNSET
        else:
            project_code = self.project_code

        project_stake_holder: None | str | Unset
        if isinstance(self.project_stake_holder, Unset):
            project_stake_holder = UNSET
        else:
            project_stake_holder = self.project_stake_holder

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

        update_time: None | str | Unset
        if isinstance(self.update_time, Unset):
            update_time = UNSET
        elif isinstance(self.update_time, datetime.datetime):
            update_time = self.update_time.isoformat()
        else:
            update_time = self.update_time

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        created_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.created_by, Unset):
            created_by = self.created_by.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if project_code is not UNSET:
            field_dict["ProjectCode"] = project_code
        if project_stake_holder is not UNSET:
            field_dict["ProjectStakeHolder"] = project_stake_holder
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if id is not UNSET:
            field_dict["Id"] = id
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by

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

        def _parse_project_stake_holder(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        project_stake_holder = _parse_project_stake_holder(d.pop("ProjectStakeHolder", UNSET))

        _create_time = d.pop("CreateTime", UNSET)
        create_time: datetime.datetime | Unset
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        _updated_by = d.pop("UpdatedBy", UNSET)
        updated_by: SystemUser | Unset
        if isinstance(_updated_by, Unset):
            updated_by = UNSET
        else:
            updated_by = SystemUser.from_dict(_updated_by)

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

        pmr_project_mapping = cls(
            project_code=project_code,
            project_stake_holder=project_stake_holder,
            create_time=create_time,
            updated_by=updated_by,
            update_time=update_time,
            id=id,
            created_by=created_by,
        )

        pmr_project_mapping.additional_properties = d
        return pmr_project_mapping

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
