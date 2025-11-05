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


T = TypeVar("T", bound="HeaderAndDivider")


@_attrs_define
class HeaderAndDivider:
    """
    Attributes:
        update_time (datetime.datetime | None | Unset):
        kms_key_id (None | Unset | UUID):
        create_time (datetime.datetime | Unset):
        id (UUID | Unset):
        updated_by (SystemUser | Unset):
        created_by (SystemUser | Unset):
    """

    update_time: datetime.datetime | None | Unset = UNSET
    kms_key_id: None | Unset | UUID = UNSET
    create_time: datetime.datetime | Unset = UNSET
    id: UUID | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        update_time: None | str | Unset
        if isinstance(self.update_time, Unset):
            update_time = UNSET
        elif isinstance(self.update_time, datetime.datetime):
            update_time = self.update_time.isoformat()
        else:
            update_time = self.update_time

        kms_key_id: None | str | Unset
        if isinstance(self.kms_key_id, Unset):
            kms_key_id = UNSET
        elif isinstance(self.kms_key_id, UUID):
            kms_key_id = str(self.kms_key_id)
        else:
            kms_key_id = self.kms_key_id

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

        created_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.created_by, Unset):
            created_by = self.created_by.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if kms_key_id is not UNSET:
            field_dict["KmsKeyId"] = kms_key_id
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if id is not UNSET:
            field_dict["Id"] = id
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.system_user import SystemUser

        d = dict(src_dict)

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

        def _parse_kms_key_id(data: object) -> None | Unset | UUID:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                kms_key_id_type_0 = UUID(data)

                return kms_key_id_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(None | Unset | UUID, data)

        kms_key_id = _parse_kms_key_id(d.pop("KmsKeyId", UNSET))

        _create_time = d.pop("CreateTime", UNSET)
        create_time: datetime.datetime | Unset
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        _id = d.pop("Id", UNSET)
        id: UUID | Unset
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

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

        header_and_divider = cls(
            update_time=update_time,
            kms_key_id=kms_key_id,
            create_time=create_time,
            id=id,
            updated_by=updated_by,
            created_by=created_by,
        )

        header_and_divider.additional_properties = d
        return header_and_divider

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
