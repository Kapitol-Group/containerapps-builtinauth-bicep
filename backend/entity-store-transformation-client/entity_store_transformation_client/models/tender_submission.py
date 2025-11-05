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
    from ..models.tender_project import TenderProject
    from ..models.title_block_validation_users import TitleBlockValidationUsers


T = TypeVar("T", bound="TenderSubmission")


@_attrs_define
class TenderSubmission:
    """
    Attributes:
        project_id (TenderProject):
        reference (str):
        submitted_by (TitleBlockValidationUsers):
        validated_by (TitleBlockValidationUsers):
        archive_name (str):
        is_addendum (bool):
        created_by (SystemUser | Unset):
        update_time (datetime.datetime | None | Unset):
        create_time (datetime.datetime | Unset):
        updated_by (SystemUser | Unset):
        id (UUID | Unset):
    """

    project_id: TenderProject
    reference: str
    submitted_by: TitleBlockValidationUsers
    validated_by: TitleBlockValidationUsers
    archive_name: str
    is_addendum: bool
    created_by: SystemUser | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    id: UUID | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        project_id = self.project_id.to_dict()

        reference = self.reference

        submitted_by = self.submitted_by.to_dict()

        validated_by = self.validated_by.to_dict()

        archive_name = self.archive_name

        is_addendum = self.is_addendum

        created_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.created_by, Unset):
            created_by = self.created_by.to_dict()

        update_time: None | str | Unset
        if isinstance(self.update_time, Unset):
            update_time = UNSET
        elif isinstance(self.update_time, datetime.datetime):
            update_time = self.update_time.isoformat()
        else:
            update_time = self.update_time

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ProjectId": project_id,
                "Reference": reference,
                "SubmittedBy": submitted_by,
                "ValidatedBy": validated_by,
                "ArchiveName": archive_name,
                "IsAddendum": is_addendum,
            }
        )
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by
        if id is not UNSET:
            field_dict["Id"] = id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.system_user import SystemUser
        from ..models.tender_project import TenderProject
        from ..models.title_block_validation_users import TitleBlockValidationUsers

        d = dict(src_dict)
        project_id = TenderProject.from_dict(d.pop("ProjectId"))

        reference = d.pop("Reference")

        submitted_by = TitleBlockValidationUsers.from_dict(d.pop("SubmittedBy"))

        validated_by = TitleBlockValidationUsers.from_dict(d.pop("ValidatedBy"))

        archive_name = d.pop("ArchiveName")

        is_addendum = d.pop("IsAddendum")

        _created_by = d.pop("CreatedBy", UNSET)
        created_by: SystemUser | Unset
        if isinstance(_created_by, Unset):
            created_by = UNSET
        else:
            created_by = SystemUser.from_dict(_created_by)

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

        _id = d.pop("Id", UNSET)
        id: UUID | Unset
        if isinstance(_id, Unset):
            id = UNSET
        else:
            id = UUID(_id)

        tender_submission = cls(
            project_id=project_id,
            reference=reference,
            submitted_by=submitted_by,
            validated_by=validated_by,
            archive_name=archive_name,
            is_addendum=is_addendum,
            created_by=created_by,
            update_time=update_time,
            create_time=create_time,
            updated_by=updated_by,
            id=id,
        )

        tender_submission.additional_properties = d
        return tender_submission

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
