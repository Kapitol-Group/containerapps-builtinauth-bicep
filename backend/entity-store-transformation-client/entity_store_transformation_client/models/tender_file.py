from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.tender_process_status import TenderProcessStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.drawing_disciplines import DrawingDisciplines
    from ..models.system_user import SystemUser
    from ..models.tender_submission import TenderSubmission


T = TypeVar("T", bound="TenderFile")


@_attrs_define
class TenderFile:
    """
    Attributes:
        submission_id (TenderSubmission):
        original_path (None | str | Unset):
        original_filename (None | str | Unset):
        document_type (None | str | Unset):
        hash_ (None | str | Unset):
        destination_path (None | str | Unset):
        destination_filename (None | str | Unset):
        drawing_number (None | str | Unset):
        drawing_revision (None | str | Unset):
        drawing_title (None | str | Unset):
        discipline (DrawingDisciplines | Unset):
        provider (None | str | Unset):
        status (TenderProcessStatus | Unset):
        transaction_id (None | str | Unset):
        create_time (datetime.datetime | Unset):
        update_time (datetime.datetime | None | Unset):
        updated_by (SystemUser | Unset):
        id (UUID | Unset):
        created_by (SystemUser | Unset):
    """

    submission_id: TenderSubmission
    original_path: None | str | Unset = UNSET
    original_filename: None | str | Unset = UNSET
    document_type: None | str | Unset = UNSET
    hash_: None | str | Unset = UNSET
    destination_path: None | str | Unset = UNSET
    destination_filename: None | str | Unset = UNSET
    drawing_number: None | str | Unset = UNSET
    drawing_revision: None | str | Unset = UNSET
    drawing_title: None | str | Unset = UNSET
    discipline: DrawingDisciplines | Unset = UNSET
    provider: None | str | Unset = UNSET
    status: TenderProcessStatus | Unset = UNSET
    transaction_id: None | str | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    id: UUID | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        submission_id = self.submission_id.to_dict()

        original_path: None | str | Unset
        if isinstance(self.original_path, Unset):
            original_path = UNSET
        else:
            original_path = self.original_path

        original_filename: None | str | Unset
        if isinstance(self.original_filename, Unset):
            original_filename = UNSET
        else:
            original_filename = self.original_filename

        document_type: None | str | Unset
        if isinstance(self.document_type, Unset):
            document_type = UNSET
        else:
            document_type = self.document_type

        hash_: None | str | Unset
        if isinstance(self.hash_, Unset):
            hash_ = UNSET
        else:
            hash_ = self.hash_

        destination_path: None | str | Unset
        if isinstance(self.destination_path, Unset):
            destination_path = UNSET
        else:
            destination_path = self.destination_path

        destination_filename: None | str | Unset
        if isinstance(self.destination_filename, Unset):
            destination_filename = UNSET
        else:
            destination_filename = self.destination_filename

        drawing_number: None | str | Unset
        if isinstance(self.drawing_number, Unset):
            drawing_number = UNSET
        else:
            drawing_number = self.drawing_number

        drawing_revision: None | str | Unset
        if isinstance(self.drawing_revision, Unset):
            drawing_revision = UNSET
        else:
            drawing_revision = self.drawing_revision

        drawing_title: None | str | Unset
        if isinstance(self.drawing_title, Unset):
            drawing_title = UNSET
        else:
            drawing_title = self.drawing_title

        discipline: dict[str, Any] | Unset = UNSET
        if not isinstance(self.discipline, Unset):
            discipline = self.discipline.to_dict()

        provider: None | str | Unset
        if isinstance(self.provider, Unset):
            provider = UNSET
        else:
            provider = self.provider

        status: int | Unset = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        transaction_id: None | str | Unset
        if isinstance(self.transaction_id, Unset):
            transaction_id = UNSET
        else:
            transaction_id = self.transaction_id

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

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        created_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.created_by, Unset):
            created_by = self.created_by.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "SubmissionId": submission_id,
            }
        )
        if original_path is not UNSET:
            field_dict["OriginalPath"] = original_path
        if original_filename is not UNSET:
            field_dict["OriginalFilename"] = original_filename
        if document_type is not UNSET:
            field_dict["DocumentType"] = document_type
        if hash_ is not UNSET:
            field_dict["Hash"] = hash_
        if destination_path is not UNSET:
            field_dict["DestinationPath"] = destination_path
        if destination_filename is not UNSET:
            field_dict["DestinationFilename"] = destination_filename
        if drawing_number is not UNSET:
            field_dict["DrawingNumber"] = drawing_number
        if drawing_revision is not UNSET:
            field_dict["DrawingRevision"] = drawing_revision
        if drawing_title is not UNSET:
            field_dict["DrawingTitle"] = drawing_title
        if discipline is not UNSET:
            field_dict["Discipline"] = discipline
        if provider is not UNSET:
            field_dict["Provider"] = provider
        if status is not UNSET:
            field_dict["Status"] = status
        if transaction_id is not UNSET:
            field_dict["TransactionId"] = transaction_id
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by
        if id is not UNSET:
            field_dict["Id"] = id
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.drawing_disciplines import DrawingDisciplines
        from ..models.system_user import SystemUser
        from ..models.tender_submission import TenderSubmission

        d = dict(src_dict)
        submission_id = TenderSubmission.from_dict(d.pop("SubmissionId"))

        def _parse_original_path(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        original_path = _parse_original_path(d.pop("OriginalPath", UNSET))

        def _parse_original_filename(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        original_filename = _parse_original_filename(d.pop("OriginalFilename", UNSET))

        def _parse_document_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        document_type = _parse_document_type(d.pop("DocumentType", UNSET))

        def _parse_hash_(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        hash_ = _parse_hash_(d.pop("Hash", UNSET))

        def _parse_destination_path(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        destination_path = _parse_destination_path(d.pop("DestinationPath", UNSET))

        def _parse_destination_filename(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        destination_filename = _parse_destination_filename(d.pop("DestinationFilename", UNSET))

        def _parse_drawing_number(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        drawing_number = _parse_drawing_number(d.pop("DrawingNumber", UNSET))

        def _parse_drawing_revision(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        drawing_revision = _parse_drawing_revision(d.pop("DrawingRevision", UNSET))

        def _parse_drawing_title(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        drawing_title = _parse_drawing_title(d.pop("DrawingTitle", UNSET))

        _discipline = d.pop("Discipline", UNSET)
        discipline: DrawingDisciplines | Unset
        if isinstance(_discipline, Unset):
            discipline = UNSET
        else:
            discipline = DrawingDisciplines.from_dict(_discipline)

        def _parse_provider(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        provider = _parse_provider(d.pop("Provider", UNSET))

        _status = d.pop("Status", UNSET)
        status: TenderProcessStatus | Unset
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = TenderProcessStatus(_status)

        def _parse_transaction_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        transaction_id = _parse_transaction_id(d.pop("TransactionId", UNSET))

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

        _created_by = d.pop("CreatedBy", UNSET)
        created_by: SystemUser | Unset
        if isinstance(_created_by, Unset):
            created_by = UNSET
        else:
            created_by = SystemUser.from_dict(_created_by)

        tender_file = cls(
            submission_id=submission_id,
            original_path=original_path,
            original_filename=original_filename,
            document_type=document_type,
            hash_=hash_,
            destination_path=destination_path,
            destination_filename=destination_filename,
            drawing_number=drawing_number,
            drawing_revision=drawing_revision,
            drawing_title=drawing_title,
            discipline=discipline,
            provider=provider,
            status=status,
            transaction_id=transaction_id,
            create_time=create_time,
            update_time=update_time,
            updated_by=updated_by,
            id=id,
            created_by=created_by,
        )

        tender_file.additional_properties = d
        return tender_file

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
