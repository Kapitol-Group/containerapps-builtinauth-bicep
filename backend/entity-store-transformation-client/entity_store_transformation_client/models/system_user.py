from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.user_type import UserType
from ..types import UNSET, Unset

T = TypeVar("T", bound="SystemUser")


@_attrs_define
class SystemUser:
    """
    Attributes:
        is_active (bool | Unset):
        create_time (datetime.datetime | Unset):
        email (None | str | Unset):
        update_time (datetime.datetime | None | Unset):
        name (str | Unset):
        id (UUID | Unset):
        type_ (UserType | Unset):
    """

    is_active: bool | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    email: None | str | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    name: str | Unset = UNSET
    id: UUID | Unset = UNSET
    type_: UserType | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        is_active = self.is_active

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        email: None | str | Unset
        if isinstance(self.email, Unset):
            email = UNSET
        else:
            email = self.email

        update_time: None | str | Unset
        if isinstance(self.update_time, Unset):
            update_time = UNSET
        elif isinstance(self.update_time, datetime.datetime):
            update_time = self.update_time.isoformat()
        else:
            update_time = self.update_time

        name = self.name

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        type_: int | Unset = UNSET
        if not isinstance(self.type_, Unset):
            type_ = self.type_.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if is_active is not UNSET:
            field_dict["IsActive"] = is_active
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if email is not UNSET:
            field_dict["Email"] = email
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if name is not UNSET:
            field_dict["Name"] = name
        if id is not UNSET:
            field_dict["Id"] = id
        if type_ is not UNSET:
            field_dict["Type"] = type_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        is_active = d.pop("IsActive", UNSET)

        _create_time = d.pop("CreateTime", UNSET)
        create_time: datetime.datetime | Unset
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        def _parse_email(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        email = _parse_email(d.pop("Email", UNSET))

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

        name = d.pop("Name", UNSET)

        _id = d.pop("Id", UNSET)
        id: UUID | Unset
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        _type_ = d.pop("Type", UNSET)
        type_: UserType | Unset
        if isinstance(_type_, Unset):
            type_ = UNSET
        else:
            type_ = UserType(_type_)

        system_user = cls(
            is_active=is_active,
            create_time=create_time,
            email=email,
            update_time=update_time,
            name=name,
            id=id,
            type_=type_,
        )

        system_user.additional_properties = d
        return system_user

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
