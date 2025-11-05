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


T = TypeVar("T", bound="PMRSubmissions")


@_attrs_define
class PMRSubmissions:
    """
    Attributes:
        pmrid (None | str | Unset):
        es21 (None | str | Unset):
        es22 (None | str | Unset):
        es23 (None | str | Unset):
        es24 (None | str | Unset):
        es25 (None | str | Unset):
        es26 (None | str | Unset):
        hse41 (None | str | Unset):
        hse42 (None | str | Unset):
        q51 (None | str | Unset):
        d61 (None | str | Unset):
        t81 (None | str | Unset):
        cs91 (None | str | Unset):
        p71 (None | str | Unset):
        create_time (datetime.datetime | Unset):
        created_by (SystemUser | Unset):
        id (UUID | Unset):
        update_time (datetime.datetime | None | Unset):
        updated_by (SystemUser | Unset):
    """

    pmrid: None | str | Unset = UNSET
    es21: None | str | Unset = UNSET
    es22: None | str | Unset = UNSET
    es23: None | str | Unset = UNSET
    es24: None | str | Unset = UNSET
    es25: None | str | Unset = UNSET
    es26: None | str | Unset = UNSET
    hse41: None | str | Unset = UNSET
    hse42: None | str | Unset = UNSET
    q51: None | str | Unset = UNSET
    d61: None | str | Unset = UNSET
    t81: None | str | Unset = UNSET
    cs91: None | str | Unset = UNSET
    p71: None | str | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    id: UUID | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        pmrid: None | str | Unset
        if isinstance(self.pmrid, Unset):
            pmrid = UNSET
        else:
            pmrid = self.pmrid

        es21: None | str | Unset
        if isinstance(self.es21, Unset):
            es21 = UNSET
        else:
            es21 = self.es21

        es22: None | str | Unset
        if isinstance(self.es22, Unset):
            es22 = UNSET
        else:
            es22 = self.es22

        es23: None | str | Unset
        if isinstance(self.es23, Unset):
            es23 = UNSET
        else:
            es23 = self.es23

        es24: None | str | Unset
        if isinstance(self.es24, Unset):
            es24 = UNSET
        else:
            es24 = self.es24

        es25: None | str | Unset
        if isinstance(self.es25, Unset):
            es25 = UNSET
        else:
            es25 = self.es25

        es26: None | str | Unset
        if isinstance(self.es26, Unset):
            es26 = UNSET
        else:
            es26 = self.es26

        hse41: None | str | Unset
        if isinstance(self.hse41, Unset):
            hse41 = UNSET
        else:
            hse41 = self.hse41

        hse42: None | str | Unset
        if isinstance(self.hse42, Unset):
            hse42 = UNSET
        else:
            hse42 = self.hse42

        q51: None | str | Unset
        if isinstance(self.q51, Unset):
            q51 = UNSET
        else:
            q51 = self.q51

        d61: None | str | Unset
        if isinstance(self.d61, Unset):
            d61 = UNSET
        else:
            d61 = self.d61

        t81: None | str | Unset
        if isinstance(self.t81, Unset):
            t81 = UNSET
        else:
            t81 = self.t81

        cs91: None | str | Unset
        if isinstance(self.cs91, Unset):
            cs91 = UNSET
        else:
            cs91 = self.cs91

        p71: None | str | Unset
        if isinstance(self.p71, Unset):
            p71 = UNSET
        else:
            p71 = self.p71

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        created_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.created_by, Unset):
            created_by = self.created_by.to_dict()

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

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if pmrid is not UNSET:
            field_dict["PMRID"] = pmrid
        if es21 is not UNSET:
            field_dict["ES21"] = es21
        if es22 is not UNSET:
            field_dict["ES22"] = es22
        if es23 is not UNSET:
            field_dict["ES23"] = es23
        if es24 is not UNSET:
            field_dict["ES24"] = es24
        if es25 is not UNSET:
            field_dict["ES25"] = es25
        if es26 is not UNSET:
            field_dict["ES26"] = es26
        if hse41 is not UNSET:
            field_dict["HSE41"] = hse41
        if hse42 is not UNSET:
            field_dict["HSE42"] = hse42
        if q51 is not UNSET:
            field_dict["Q51"] = q51
        if d61 is not UNSET:
            field_dict["D61"] = d61
        if t81 is not UNSET:
            field_dict["T81"] = t81
        if cs91 is not UNSET:
            field_dict["CS91"] = cs91
        if p71 is not UNSET:
            field_dict["P71"] = p71
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by
        if id is not UNSET:
            field_dict["Id"] = id
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by

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

        def _parse_es21(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        es21 = _parse_es21(d.pop("ES21", UNSET))

        def _parse_es22(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        es22 = _parse_es22(d.pop("ES22", UNSET))

        def _parse_es23(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        es23 = _parse_es23(d.pop("ES23", UNSET))

        def _parse_es24(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        es24 = _parse_es24(d.pop("ES24", UNSET))

        def _parse_es25(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        es25 = _parse_es25(d.pop("ES25", UNSET))

        def _parse_es26(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        es26 = _parse_es26(d.pop("ES26", UNSET))

        def _parse_hse41(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        hse41 = _parse_hse41(d.pop("HSE41", UNSET))

        def _parse_hse42(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        hse42 = _parse_hse42(d.pop("HSE42", UNSET))

        def _parse_q51(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        q51 = _parse_q51(d.pop("Q51", UNSET))

        def _parse_d61(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        d61 = _parse_d61(d.pop("D61", UNSET))

        def _parse_t81(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        t81 = _parse_t81(d.pop("T81", UNSET))

        def _parse_cs91(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        cs91 = _parse_cs91(d.pop("CS91", UNSET))

        def _parse_p71(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        p71 = _parse_p71(d.pop("P71", UNSET))

        _create_time = d.pop("CreateTime", UNSET)
        create_time: datetime.datetime | Unset
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        _created_by = d.pop("CreatedBy", UNSET)
        created_by: SystemUser | Unset
        if isinstance(_created_by, Unset):
            created_by = UNSET
        else:
            created_by = SystemUser.from_dict(_created_by)

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

        _updated_by = d.pop("UpdatedBy", UNSET)
        updated_by: SystemUser | Unset
        if isinstance(_updated_by, Unset):
            updated_by = UNSET
        else:
            updated_by = SystemUser.from_dict(_updated_by)

        pmr_submissions = cls(
            pmrid=pmrid,
            es21=es21,
            es22=es22,
            es23=es23,
            es24=es24,
            es25=es25,
            es26=es26,
            hse41=hse41,
            hse42=hse42,
            q51=q51,
            d61=d61,
            t81=t81,
            cs91=cs91,
            p71=p71,
            create_time=create_time,
            created_by=created_by,
            id=id,
            update_time=update_time,
            updated_by=updated_by,
        )

        pmr_submissions.additional_properties = d
        return pmr_submissions

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
