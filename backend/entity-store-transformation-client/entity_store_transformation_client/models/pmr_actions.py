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


T = TypeVar("T", bound="PMRActions")


@_attrs_define
class PMRActions:
    """
    Attributes:
        item (float | None | Unset):
        issue (None | str | Unset):
        status (None | str | Unset):
        assigned (None | str | Unset):
        due_date (datetime.date | None | Unset):
        pmrid (None | str | Unset):
        id (UUID | Unset):
        create_time (datetime.datetime | Unset):
        updated_by (SystemUser | Unset):
        update_time (datetime.datetime | None | Unset):
        created_by (SystemUser | Unset):
    """

    item: float | None | Unset = UNSET
    issue: None | str | Unset = UNSET
    status: None | str | Unset = UNSET
    assigned: None | str | Unset = UNSET
    due_date: datetime.date | None | Unset = UNSET
    pmrid: None | str | Unset = UNSET
    id: UUID | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        item: float | None | Unset
        if isinstance(self.item, Unset):
            item = UNSET
        else:
            item = self.item

        issue: None | str | Unset
        if isinstance(self.issue, Unset):
            issue = UNSET
        else:
            issue = self.issue

        status: None | str | Unset
        if isinstance(self.status, Unset):
            status = UNSET
        else:
            status = self.status

        assigned: None | str | Unset
        if isinstance(self.assigned, Unset):
            assigned = UNSET
        else:
            assigned = self.assigned

        due_date: None | str | Unset
        if isinstance(self.due_date, Unset):
            due_date = UNSET
        elif isinstance(self.due_date, datetime.date):
            due_date = self.due_date.isoformat()
        else:
            due_date = self.due_date

        pmrid: None | str | Unset
        if isinstance(self.pmrid, Unset):
            pmrid = UNSET
        else:
            pmrid = self.pmrid

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

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

        created_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.created_by, Unset):
            created_by = self.created_by.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if item is not UNSET:
            field_dict["Item"] = item
        if issue is not UNSET:
            field_dict["Issue"] = issue
        if status is not UNSET:
            field_dict["Status"] = status
        if assigned is not UNSET:
            field_dict["Assigned"] = assigned
        if due_date is not UNSET:
            field_dict["DueDate"] = due_date
        if pmrid is not UNSET:
            field_dict["PMRID"] = pmrid
        if id is not UNSET:
            field_dict["Id"] = id
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.system_user import SystemUser

        d = dict(src_dict)

        def _parse_item(data: object) -> float | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(float | None | Unset, data)

        item = _parse_item(d.pop("Item", UNSET))

        def _parse_issue(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        issue = _parse_issue(d.pop("Issue", UNSET))

        def _parse_status(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        status = _parse_status(d.pop("Status", UNSET))

        def _parse_assigned(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        assigned = _parse_assigned(d.pop("Assigned", UNSET))

        def _parse_due_date(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                due_date_type_0 = isoparse(data).date()

                return due_date_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        due_date = _parse_due_date(d.pop("DueDate", UNSET))

        def _parse_pmrid(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        pmrid = _parse_pmrid(d.pop("PMRID", UNSET))

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

        pmr_actions = cls(
            item=item,
            issue=issue,
            status=status,
            assigned=assigned,
            due_date=due_date,
            pmrid=pmrid,
            id=id,
            create_time=create_time,
            updated_by=updated_by,
            update_time=update_time,
            created_by=created_by,
        )

        pmr_actions.additional_properties = d
        return pmr_actions

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
