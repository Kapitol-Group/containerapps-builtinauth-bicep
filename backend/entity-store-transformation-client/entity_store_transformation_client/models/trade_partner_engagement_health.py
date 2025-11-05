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


T = TypeVar("T", bound="TradePartnerEngagementHealth")


@_attrs_define
class TradePartnerEngagementHealth:
    """
    Attributes:
        pmrid (None | str | Unset):
        trade_partner_name (None | str | Unset):
        engagementphasecurrentactivityunderway (None | str | Unset):
        engagement_health (None | str | Unset):
        id (UUID | Unset):
        kms_key_id (None | Unset | UUID):
        create_time (datetime.datetime | Unset):
        update_time (datetime.datetime | None | Unset):
        created_by (SystemUser | Unset):
        updated_by (SystemUser | Unset):
    """

    pmrid: None | str | Unset = UNSET
    trade_partner_name: None | str | Unset = UNSET
    engagementphasecurrentactivityunderway: None | str | Unset = UNSET
    engagement_health: None | str | Unset = UNSET
    id: UUID | Unset = UNSET
    kms_key_id: None | Unset | UUID = UNSET
    create_time: datetime.datetime | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        pmrid: None | str | Unset
        if isinstance(self.pmrid, Unset):
            pmrid = UNSET
        else:
            pmrid = self.pmrid

        trade_partner_name: None | str | Unset
        if isinstance(self.trade_partner_name, Unset):
            trade_partner_name = UNSET
        else:
            trade_partner_name = self.trade_partner_name

        engagementphasecurrentactivityunderway: None | str | Unset
        if isinstance(self.engagementphasecurrentactivityunderway, Unset):
            engagementphasecurrentactivityunderway = UNSET
        else:
            engagementphasecurrentactivityunderway = self.engagementphasecurrentactivityunderway

        engagement_health: None | str | Unset
        if isinstance(self.engagement_health, Unset):
            engagement_health = UNSET
        else:
            engagement_health = self.engagement_health

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

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

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if pmrid is not UNSET:
            field_dict["PMRID"] = pmrid
        if trade_partner_name is not UNSET:
            field_dict["TradePartnerName"] = trade_partner_name
        if engagementphasecurrentactivityunderway is not UNSET:
            field_dict["Engagementphasecurrentactivityunderway"] = engagementphasecurrentactivityunderway
        if engagement_health is not UNSET:
            field_dict["EngagementHealth"] = engagement_health
        if id is not UNSET:
            field_dict["Id"] = id
        if kms_key_id is not UNSET:
            field_dict["KmsKeyId"] = kms_key_id
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by
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

        def _parse_trade_partner_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        trade_partner_name = _parse_trade_partner_name(d.pop("TradePartnerName", UNSET))

        def _parse_engagementphasecurrentactivityunderway(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        engagementphasecurrentactivityunderway = _parse_engagementphasecurrentactivityunderway(
            d.pop("Engagementphasecurrentactivityunderway", UNSET)
        )

        def _parse_engagement_health(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        engagement_health = _parse_engagement_health(d.pop("EngagementHealth", UNSET))

        _id = d.pop("Id", UNSET)
        id: UUID | Unset
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

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

        trade_partner_engagement_health = cls(
            pmrid=pmrid,
            trade_partner_name=trade_partner_name,
            engagementphasecurrentactivityunderway=engagementphasecurrentactivityunderway,
            engagement_health=engagement_health,
            id=id,
            kms_key_id=kms_key_id,
            create_time=create_time,
            update_time=update_time,
            created_by=created_by,
            updated_by=updated_by,
        )

        trade_partner_engagement_health.additional_properties = d
        return trade_partner_engagement_health

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
