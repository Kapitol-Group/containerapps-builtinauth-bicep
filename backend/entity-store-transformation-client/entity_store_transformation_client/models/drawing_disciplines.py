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


T = TypeVar("T", bound="DrawingDisciplines")


@_attrs_define
class DrawingDisciplines:
    """
    Attributes:
        discipline_folder (str):
        rule (None | str | Unset):
        update_time (datetime.datetime | None | Unset):
        id (UUID | Unset):
        create_time (datetime.datetime | Unset):
        updated_by (SystemUser | Unset):
        created_by (SystemUser | Unset):
    """

    discipline_folder: str
    rule: None | str | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    id: UUID | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        discipline_folder = self.discipline_folder

        rule: None | str | Unset
        if isinstance(self.rule, Unset):
            rule = UNSET
        else:
            rule = self.rule

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

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

        created_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.created_by, Unset):
            created_by = self.created_by.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "DisciplineFolder": discipline_folder,
            }
        )
        if rule is not UNSET:
            field_dict["Rule"] = rule
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if id is not UNSET:
            field_dict["Id"] = id
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.system_user import SystemUser

        d = dict(src_dict)
        discipline_folder = d.pop("DisciplineFolder")

        def _parse_rule(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        rule = _parse_rule(d.pop("Rule", UNSET))

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

        _created_by = d.pop("CreatedBy", UNSET)
        created_by: SystemUser | Unset
        if isinstance(_created_by, Unset):
            created_by = UNSET
        else:
            created_by = SystemUser.from_dict(_created_by)

        drawing_disciplines = cls(
            discipline_folder=discipline_folder,
            rule=rule,
            update_time=update_time,
            id=id,
            create_time=create_time,
            updated_by=updated_by,
            created_by=created_by,
        )

        drawing_disciplines.additional_properties = d
        return drawing_disciplines

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
