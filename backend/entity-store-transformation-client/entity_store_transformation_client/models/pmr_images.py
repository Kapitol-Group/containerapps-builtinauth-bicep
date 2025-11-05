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


T = TypeVar("T", bound="PMRImages")


@_attrs_define
class PMRImages:
    """
    Attributes:
        pmrid (None | str | Unset):
        image_code (None | str | Unset):
        image_string (None | str | Unset):
        update_time (datetime.datetime | None | Unset):
        updated_by (SystemUser | Unset):
        create_time (datetime.datetime | Unset):
        id (UUID | Unset):
        created_by (SystemUser | Unset):
    """

    pmrid: None | str | Unset = UNSET
    image_code: None | str | Unset = UNSET
    image_string: None | str | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    id: UUID | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        pmrid: None | str | Unset
        if isinstance(self.pmrid, Unset):
            pmrid = UNSET
        else:
            pmrid = self.pmrid

        image_code: None | str | Unset
        if isinstance(self.image_code, Unset):
            image_code = UNSET
        else:
            image_code = self.image_code

        image_string: None | str | Unset
        if isinstance(self.image_string, Unset):
            image_string = UNSET
        else:
            image_string = self.image_string

        update_time: None | str | Unset
        if isinstance(self.update_time, Unset):
            update_time = UNSET
        elif isinstance(self.update_time, datetime.datetime):
            update_time = self.update_time.isoformat()
        else:
            update_time = self.update_time

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        created_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.created_by, Unset):
            created_by = self.created_by.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if pmrid is not UNSET:
            field_dict["PMRID"] = pmrid
        if image_code is not UNSET:
            field_dict["ImageCode"] = image_code
        if image_string is not UNSET:
            field_dict["ImageString"] = image_string
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if id is not UNSET:
            field_dict["Id"] = id
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.system_user import SystemUser

        d = dict(src_dict)

        def _parse_pmrid(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        pmrid = _parse_pmrid(d.pop("PMRID", UNSET))

        def _parse_image_code(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        image_code = _parse_image_code(d.pop("ImageCode", UNSET))

        def _parse_image_string(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        image_string = _parse_image_string(d.pop("ImageString", UNSET))

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

        _updated_by = d.pop("UpdatedBy", UNSET)
        updated_by: SystemUser | Unset
        if isinstance(_updated_by, Unset):
            updated_by = UNSET
        else:
            updated_by = SystemUser.from_dict(_updated_by)

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

        _created_by = d.pop("CreatedBy", UNSET)
        created_by: SystemUser | Unset
        if isinstance(_created_by, Unset):
            created_by = UNSET
        else:
            created_by = SystemUser.from_dict(_created_by)

        pmr_images = cls(
            pmrid=pmrid,
            image_code=image_code,
            image_string=image_string,
            update_time=update_time,
            updated_by=updated_by,
            create_time=create_time,
            id=id,
            created_by=created_by,
        )

        pmr_images.additional_properties = d
        return pmr_images

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
