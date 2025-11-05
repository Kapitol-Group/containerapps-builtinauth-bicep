from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..models.project_contract_type import ProjectContractType
from ..models.project_role import ProjectRole
from ..models.project_role_capability import ProjectRoleCapability
from ..models.project_type import ProjectType
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.system_user import SystemUser


T = TypeVar("T", bound="EmployeeInternalExperience")


@_attrs_define
class EmployeeInternalExperience:
    """
    Attributes:
        client (str):
        company (str):
        project_value (str):
        project_duration (str):
        position (list[ProjectRole]):
        contract_type (ProjectContractType):
        employee_id (float):
        type_ (ProjectType):
        project_name (str):
        comments (None | str | Unset):
        capabilities (list[ProjectRoleCapability] | Unset):
        capability_other (None | str | Unset):
        create_time (datetime.datetime | Unset):
        update_time (datetime.datetime | None | Unset):
        created_by (SystemUser | Unset):
        id (UUID | Unset):
        updated_by (SystemUser | Unset):
    """

    client: str
    company: str
    project_value: str
    project_duration: str
    position: list[ProjectRole]
    contract_type: ProjectContractType
    employee_id: float
    type_: ProjectType
    project_name: str
    comments: None | str | Unset = UNSET
    capabilities: list[ProjectRoleCapability] | Unset = UNSET
    capability_other: None | str | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    id: UUID | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        client = self.client

        company = self.company

        project_value = self.project_value

        project_duration = self.project_duration

        position = []
        for position_item_data in self.position:
            position_item = position_item_data.value
            position.append(position_item)

        contract_type = self.contract_type.value

        employee_id = self.employee_id

        type_ = self.type_.value

        project_name = self.project_name

        comments: None | str | Unset
        if isinstance(self.comments, Unset):
            comments = UNSET
        else:
            comments = self.comments

        capabilities: list[int] | Unset = UNSET
        if not isinstance(self.capabilities, Unset):
            capabilities = []
            for capabilities_item_data in self.capabilities:
                capabilities_item = capabilities_item_data.value
                capabilities.append(capabilities_item)

        capability_other: None | str | Unset
        if isinstance(self.capability_other, Unset):
            capability_other = UNSET
        else:
            capability_other = self.capability_other

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

        id: str | Unset = UNSET
        if not isinstance(self.id, Unset):
            id = str(self.id)

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "Client": client,
                "Company": company,
                "ProjectValue": project_value,
                "ProjectDuration": project_duration,
                "Position": position,
                "ContractType": contract_type,
                "EmployeeID": employee_id,
                "Type": type_,
                "ProjectName": project_name,
            }
        )
        if comments is not UNSET:
            field_dict["Comments"] = comments
        if capabilities is not UNSET:
            field_dict["Capabilities"] = capabilities
        if capability_other is not UNSET:
            field_dict["CapabilityOther"] = capability_other
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by
        if id is not UNSET:
            field_dict["Id"] = id
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.system_user import SystemUser

        d = dict(src_dict)
        client = d.pop("Client")

        company = d.pop("Company")

        project_value = d.pop("ProjectValue")

        project_duration = d.pop("ProjectDuration")

        position = []
        _position = d.pop("Position")
        for position_item_data in _position:
            position_item = ProjectRole(position_item_data)

            position.append(position_item)

        contract_type = ProjectContractType(d.pop("ContractType"))

        employee_id = d.pop("EmployeeID")

        type_ = ProjectType(d.pop("Type"))

        project_name = d.pop("ProjectName")

        def _parse_comments(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        comments = _parse_comments(d.pop("Comments", UNSET))

        _capabilities = d.pop("Capabilities", UNSET)
        capabilities: list[ProjectRoleCapability] | Unset = UNSET
        if _capabilities is not UNSET:
            capabilities = []
            for capabilities_item_data in _capabilities:
                capabilities_item = ProjectRoleCapability(capabilities_item_data)

                capabilities.append(capabilities_item)

        def _parse_capability_other(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        capability_other = _parse_capability_other(d.pop("CapabilityOther", UNSET))

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

        employee_internal_experience = cls(
            client=client,
            company=company,
            project_value=project_value,
            project_duration=project_duration,
            position=position,
            contract_type=contract_type,
            employee_id=employee_id,
            type_=type_,
            project_name=project_name,
            comments=comments,
            capabilities=capabilities,
            capability_other=capability_other,
            create_time=create_time,
            update_time=update_time,
            created_by=created_by,
            id=id,
            updated_by=updated_by,
        )

        employee_internal_experience.additional_properties = d
        return employee_internal_experience

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
