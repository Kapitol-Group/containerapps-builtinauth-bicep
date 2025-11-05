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


T = TypeVar("T", bound="EmployeeDetails")


@_attrs_define
class EmployeeDetails:
    """
    Attributes:
        employee_dei (str):
        employee_gender (str):
        employee_visa_na (bool | None | Unset):
        employee_visa_type (None | str | Unset):
        course_qual_trade (None | str | Unset):
        professional_awards (None | str | Unset):
        professional_qualifications (None | str | Unset):
        employee_home_address_suburb (None | str | Unset):
        employee_kg_phone_number (None | str | Unset):
        employee_id (None | str | Unset):
        employee_company (None | str | Unset):
        employee_kg_email (None | str | Unset):
        employee_visa_number (None | str | Unset):
        employee_start_date (datetime.date | None | Unset):
        employee_position_title (None | str | Unset):
        university (None | str | Unset):
        employee_first_surname (None | str | Unset):
        visa_effective_from (datetime.date | None | Unset):
        visa_effective_to (datetime.date | None | Unset):
        university_other (None | str | Unset):
        accreditations (None | str | Unset):
        course_qual (None | str | Unset):
        course_qual_other (None | str | Unset):
        created_by (SystemUser | Unset):
        create_time (datetime.datetime | Unset):
        updated_by (SystemUser | Unset):
        id (UUID | Unset):
        update_time (datetime.datetime | None | Unset):
    """

    employee_dei: str
    employee_gender: str
    employee_visa_na: bool | None | Unset = UNSET
    employee_visa_type: None | str | Unset = UNSET
    course_qual_trade: None | str | Unset = UNSET
    professional_awards: None | str | Unset = UNSET
    professional_qualifications: None | str | Unset = UNSET
    employee_home_address_suburb: None | str | Unset = UNSET
    employee_kg_phone_number: None | str | Unset = UNSET
    employee_id: None | str | Unset = UNSET
    employee_company: None | str | Unset = UNSET
    employee_kg_email: None | str | Unset = UNSET
    employee_visa_number: None | str | Unset = UNSET
    employee_start_date: datetime.date | None | Unset = UNSET
    employee_position_title: None | str | Unset = UNSET
    university: None | str | Unset = UNSET
    employee_first_surname: None | str | Unset = UNSET
    visa_effective_from: datetime.date | None | Unset = UNSET
    visa_effective_to: datetime.date | None | Unset = UNSET
    university_other: None | str | Unset = UNSET
    accreditations: None | str | Unset = UNSET
    course_qual: None | str | Unset = UNSET
    course_qual_other: None | str | Unset = UNSET
    created_by: SystemUser | Unset = UNSET
    create_time: datetime.datetime | Unset = UNSET
    updated_by: SystemUser | Unset = UNSET
    id: UUID | Unset = UNSET
    update_time: datetime.datetime | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        employee_dei = self.employee_dei

        employee_gender = self.employee_gender

        employee_visa_na: bool | None | Unset
        if isinstance(self.employee_visa_na, Unset):
            employee_visa_na = UNSET
        else:
            employee_visa_na = self.employee_visa_na

        employee_visa_type: None | str | Unset
        if isinstance(self.employee_visa_type, Unset):
            employee_visa_type = UNSET
        else:
            employee_visa_type = self.employee_visa_type

        course_qual_trade: None | str | Unset
        if isinstance(self.course_qual_trade, Unset):
            course_qual_trade = UNSET
        else:
            course_qual_trade = self.course_qual_trade

        professional_awards: None | str | Unset
        if isinstance(self.professional_awards, Unset):
            professional_awards = UNSET
        else:
            professional_awards = self.professional_awards

        professional_qualifications: None | str | Unset
        if isinstance(self.professional_qualifications, Unset):
            professional_qualifications = UNSET
        else:
            professional_qualifications = self.professional_qualifications

        employee_home_address_suburb: None | str | Unset
        if isinstance(self.employee_home_address_suburb, Unset):
            employee_home_address_suburb = UNSET
        else:
            employee_home_address_suburb = self.employee_home_address_suburb

        employee_kg_phone_number: None | str | Unset
        if isinstance(self.employee_kg_phone_number, Unset):
            employee_kg_phone_number = UNSET
        else:
            employee_kg_phone_number = self.employee_kg_phone_number

        employee_id: None | str | Unset
        if isinstance(self.employee_id, Unset):
            employee_id = UNSET
        else:
            employee_id = self.employee_id

        employee_company: None | str | Unset
        if isinstance(self.employee_company, Unset):
            employee_company = UNSET
        else:
            employee_company = self.employee_company

        employee_kg_email: None | str | Unset
        if isinstance(self.employee_kg_email, Unset):
            employee_kg_email = UNSET
        else:
            employee_kg_email = self.employee_kg_email

        employee_visa_number: None | str | Unset
        if isinstance(self.employee_visa_number, Unset):
            employee_visa_number = UNSET
        else:
            employee_visa_number = self.employee_visa_number

        employee_start_date: None | str | Unset
        if isinstance(self.employee_start_date, Unset):
            employee_start_date = UNSET
        elif isinstance(self.employee_start_date, datetime.date):
            employee_start_date = self.employee_start_date.isoformat()
        else:
            employee_start_date = self.employee_start_date

        employee_position_title: None | str | Unset
        if isinstance(self.employee_position_title, Unset):
            employee_position_title = UNSET
        else:
            employee_position_title = self.employee_position_title

        university: None | str | Unset
        if isinstance(self.university, Unset):
            university = UNSET
        else:
            university = self.university

        employee_first_surname: None | str | Unset
        if isinstance(self.employee_first_surname, Unset):
            employee_first_surname = UNSET
        else:
            employee_first_surname = self.employee_first_surname

        visa_effective_from: None | str | Unset
        if isinstance(self.visa_effective_from, Unset):
            visa_effective_from = UNSET
        elif isinstance(self.visa_effective_from, datetime.date):
            visa_effective_from = self.visa_effective_from.isoformat()
        else:
            visa_effective_from = self.visa_effective_from

        visa_effective_to: None | str | Unset
        if isinstance(self.visa_effective_to, Unset):
            visa_effective_to = UNSET
        elif isinstance(self.visa_effective_to, datetime.date):
            visa_effective_to = self.visa_effective_to.isoformat()
        else:
            visa_effective_to = self.visa_effective_to

        university_other: None | str | Unset
        if isinstance(self.university_other, Unset):
            university_other = UNSET
        else:
            university_other = self.university_other

        accreditations: None | str | Unset
        if isinstance(self.accreditations, Unset):
            accreditations = UNSET
        else:
            accreditations = self.accreditations

        course_qual: None | str | Unset
        if isinstance(self.course_qual, Unset):
            course_qual = UNSET
        else:
            course_qual = self.course_qual

        course_qual_other: None | str | Unset
        if isinstance(self.course_qual_other, Unset):
            course_qual_other = UNSET
        else:
            course_qual_other = self.course_qual_other

        created_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.created_by, Unset):
            created_by = self.created_by.to_dict()

        create_time: str | Unset = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        updated_by: dict[str, Any] | Unset = UNSET
        if not isinstance(self.updated_by, Unset):
            updated_by = self.updated_by.to_dict()

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

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "EmployeeDEI": employee_dei,
                "EmployeeGender": employee_gender,
            }
        )
        if employee_visa_na is not UNSET:
            field_dict["EmployeeVisaNA"] = employee_visa_na
        if employee_visa_type is not UNSET:
            field_dict["EmployeeVisaType"] = employee_visa_type
        if course_qual_trade is not UNSET:
            field_dict["CourseQualTrade"] = course_qual_trade
        if professional_awards is not UNSET:
            field_dict["ProfessionalAwards"] = professional_awards
        if professional_qualifications is not UNSET:
            field_dict["ProfessionalQualifications"] = professional_qualifications
        if employee_home_address_suburb is not UNSET:
            field_dict["EmployeeHomeAddressSuburb"] = employee_home_address_suburb
        if employee_kg_phone_number is not UNSET:
            field_dict["EmployeeKGPhoneNumber"] = employee_kg_phone_number
        if employee_id is not UNSET:
            field_dict["EmployeeID"] = employee_id
        if employee_company is not UNSET:
            field_dict["EmployeeCompany"] = employee_company
        if employee_kg_email is not UNSET:
            field_dict["EmployeeKGEmail"] = employee_kg_email
        if employee_visa_number is not UNSET:
            field_dict["EmployeeVisaNumber"] = employee_visa_number
        if employee_start_date is not UNSET:
            field_dict["EmployeeStartDate"] = employee_start_date
        if employee_position_title is not UNSET:
            field_dict["EmployeePositionTitle"] = employee_position_title
        if university is not UNSET:
            field_dict["University"] = university
        if employee_first_surname is not UNSET:
            field_dict["EmployeeFirstSurname"] = employee_first_surname
        if visa_effective_from is not UNSET:
            field_dict["VisaEffectiveFrom"] = visa_effective_from
        if visa_effective_to is not UNSET:
            field_dict["VisaEffectiveTo"] = visa_effective_to
        if university_other is not UNSET:
            field_dict["UniversityOther"] = university_other
        if accreditations is not UNSET:
            field_dict["Accreditations"] = accreditations
        if course_qual is not UNSET:
            field_dict["CourseQual"] = course_qual
        if course_qual_other is not UNSET:
            field_dict["CourseQualOther"] = course_qual_other
        if created_by is not UNSET:
            field_dict["CreatedBy"] = created_by
        if create_time is not UNSET:
            field_dict["CreateTime"] = create_time
        if updated_by is not UNSET:
            field_dict["UpdatedBy"] = updated_by
        if id is not UNSET:
            field_dict["Id"] = id
        if update_time is not UNSET:
            field_dict["UpdateTime"] = update_time

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.system_user import SystemUser

        d = dict(src_dict)
        employee_dei = d.pop("EmployeeDEI")

        employee_gender = d.pop("EmployeeGender")

        def _parse_employee_visa_na(data: object) -> bool | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(bool | None | Unset, data)

        employee_visa_na = _parse_employee_visa_na(d.pop("EmployeeVisaNA", UNSET))

        def _parse_employee_visa_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        employee_visa_type = _parse_employee_visa_type(d.pop("EmployeeVisaType", UNSET))

        def _parse_course_qual_trade(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        course_qual_trade = _parse_course_qual_trade(d.pop("CourseQualTrade", UNSET))

        def _parse_professional_awards(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        professional_awards = _parse_professional_awards(d.pop("ProfessionalAwards", UNSET))

        def _parse_professional_qualifications(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        professional_qualifications = _parse_professional_qualifications(d.pop("ProfessionalQualifications", UNSET))

        def _parse_employee_home_address_suburb(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        employee_home_address_suburb = _parse_employee_home_address_suburb(d.pop("EmployeeHomeAddressSuburb", UNSET))

        def _parse_employee_kg_phone_number(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        employee_kg_phone_number = _parse_employee_kg_phone_number(d.pop("EmployeeKGPhoneNumber", UNSET))

        def _parse_employee_id(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        employee_id = _parse_employee_id(d.pop("EmployeeID", UNSET))

        def _parse_employee_company(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        employee_company = _parse_employee_company(d.pop("EmployeeCompany", UNSET))

        def _parse_employee_kg_email(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        employee_kg_email = _parse_employee_kg_email(d.pop("EmployeeKGEmail", UNSET))

        def _parse_employee_visa_number(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        employee_visa_number = _parse_employee_visa_number(d.pop("EmployeeVisaNumber", UNSET))

        def _parse_employee_start_date(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                employee_start_date_type_0 = isoparse(data).date()

                return employee_start_date_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        employee_start_date = _parse_employee_start_date(d.pop("EmployeeStartDate", UNSET))

        def _parse_employee_position_title(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        employee_position_title = _parse_employee_position_title(d.pop("EmployeePositionTitle", UNSET))

        def _parse_university(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        university = _parse_university(d.pop("University", UNSET))

        def _parse_employee_first_surname(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        employee_first_surname = _parse_employee_first_surname(d.pop("EmployeeFirstSurname", UNSET))

        def _parse_visa_effective_from(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                visa_effective_from_type_0 = isoparse(data).date()

                return visa_effective_from_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        visa_effective_from = _parse_visa_effective_from(d.pop("VisaEffectiveFrom", UNSET))

        def _parse_visa_effective_to(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                visa_effective_to_type_0 = isoparse(data).date()

                return visa_effective_to_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        visa_effective_to = _parse_visa_effective_to(d.pop("VisaEffectiveTo", UNSET))

        def _parse_university_other(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        university_other = _parse_university_other(d.pop("UniversityOther", UNSET))

        def _parse_accreditations(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        accreditations = _parse_accreditations(d.pop("Accreditations", UNSET))

        def _parse_course_qual(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        course_qual = _parse_course_qual(d.pop("CourseQual", UNSET))

        def _parse_course_qual_other(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        course_qual_other = _parse_course_qual_other(d.pop("CourseQualOther", UNSET))

        _created_by = d.pop("CreatedBy", UNSET)
        created_by: SystemUser | Unset
        if isinstance(_created_by, Unset):
            created_by = UNSET
        else:
            created_by = SystemUser.from_dict(_created_by)

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

        employee_details = cls(
            employee_dei=employee_dei,
            employee_gender=employee_gender,
            employee_visa_na=employee_visa_na,
            employee_visa_type=employee_visa_type,
            course_qual_trade=course_qual_trade,
            professional_awards=professional_awards,
            professional_qualifications=professional_qualifications,
            employee_home_address_suburb=employee_home_address_suburb,
            employee_kg_phone_number=employee_kg_phone_number,
            employee_id=employee_id,
            employee_company=employee_company,
            employee_kg_email=employee_kg_email,
            employee_visa_number=employee_visa_number,
            employee_start_date=employee_start_date,
            employee_position_title=employee_position_title,
            university=university,
            employee_first_surname=employee_first_surname,
            visa_effective_from=visa_effective_from,
            visa_effective_to=visa_effective_to,
            university_other=university_other,
            accreditations=accreditations,
            course_qual=course_qual,
            course_qual_other=course_qual_other,
            created_by=created_by,
            create_time=create_time,
            updated_by=updated_by,
            id=id,
            update_time=update_time,
        )

        employee_details.additional_properties = d
        return employee_details

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
