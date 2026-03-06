"""M-Files API helper for project lookup, metadata search, and content download."""
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

import requests

logger = logging.getLogger(__name__)


class MFilesClientError(Exception):
    """Raised when M-Files API calls fail or return invalid data."""


class MFilesConfigurationError(MFilesClientError):
    """Raised when required M-Files configuration is missing."""


class MFilesClient:
    """Small wrapper around the M-Files endpoints used by this application."""

    def __init__(self, base_url: str, client_id: str, client_secret: str, timeout_seconds: int = 20):
        self.base_url = (base_url or '').rstrip('/')
        self.client_id = (client_id or '').strip()
        self.client_secret = (client_secret or '').strip()
        self.timeout_seconds = timeout_seconds

    def _ensure_configured(self) -> None:
        missing = []
        if not self.base_url:
            missing.append('MFILES_BASE_URL')
        if not self.client_id:
            missing.append('MFILES_CLIENT_ID')
        if not self.client_secret:
            missing.append('MFILES_CLIENT_SECRET')

        if missing:
            raise MFilesConfigurationError(
                f"M-Files API is not configured. Missing environment variables: {', '.join(missing)}"
            )

    def _build_headers(self, accept: str = 'application/json') -> Dict[str, str]:
        return {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'Accept': accept,
        }

    def _parse_json_response(self, response: requests.Response, path: str) -> Dict:
        if not response.ok:
            body_preview = response.text.strip().replace('\n', ' ')[:240]
            raise MFilesClientError(
                f"M-Files API request failed ({response.status_code}): {body_preview or response.reason}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise MFilesClientError('M-Files API returned non-JSON response') from exc

        if not isinstance(payload, dict):
            raise MFilesClientError('M-Files API returned an unexpected JSON shape')

        cid = payload.get('cid')
        if cid:
            logger.info('M-Files request succeeded path=%s cid=%s', path, cid)

        return payload

    def _request_get(self, path: str, params: Optional[Dict] = None) -> Dict:
        self._ensure_configured()
        url = f"{self.base_url}{path}"
        try:
            response = requests.get(
                url,
                params=params,
                headers=self._build_headers(),
                timeout=self.timeout_seconds
            )
        except requests.RequestException as exc:
            raise MFilesClientError(f"M-Files request failed: {exc}") from exc

        return self._parse_json_response(response, path)

    def _request_post(self, path: str, payload: Dict[str, Any]) -> Dict:
        self._ensure_configured()
        url = f"{self.base_url}{path}"
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._build_headers(),
                timeout=self.timeout_seconds
            )
        except requests.RequestException as exc:
            raise MFilesClientError(f"M-Files request failed: {exc}") from exc

        return self._parse_json_response(response, path)

    def _request_content(self, path: str, params: Optional[Dict] = None) -> requests.Response:
        self._ensure_configured()
        url = f"{self.base_url}{path}"
        try:
            response = requests.get(
                url,
                params=params,
                headers=self._build_headers(accept='*/*'),
                timeout=self.timeout_seconds
            )
        except requests.RequestException as exc:
            raise MFilesClientError(f"M-Files content request failed: {exc}") from exc

        if not response.ok:
            body_preview = response.text.strip().replace('\n', ' ')[:240]
            raise MFilesClientError(
                f"M-Files content request failed ({response.status_code}): {body_preview or response.reason}"
            )

        return response

    def get_document_definition(self, doc_class: str = 'Drawing') -> Dict:
        params = {'docClass': doc_class} if doc_class else None
        definition_payload = self._request_get('/document/definition', params=params)
        if definition_payload.get('status') == 'failed':
            raise MFilesClientError('M-Files document definition request failed')
        return definition_payload

    def get_document_classes(self) -> List[Dict[str, str]]:
        payload = self._request_get('/document/definition')
        if payload.get('status') == 'failed':
            raise MFilesClientError('M-Files document class definition request failed')

        data = payload.get('data')
        raw_items: List[Dict[str, Any]] = []
        if isinstance(data, list):
            raw_items = [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            if 'name' in data or 'Name' in data:
                raw_items = [data]
            else:
                for value in data.values():
                    if isinstance(value, dict):
                        raw_items.append(value)
                    elif isinstance(value, list):
                        raw_items.extend(item for item in value if isinstance(item, dict))

        classes: List[Dict[str, str]] = []
        seen = set()
        for item in raw_items:
            raw_name = item.get('name') or item.get('Name')
            raw_id = item.get('ID') if item.get('ID') is not None else item.get('id')
            name = str(raw_name or '').strip()
            class_id = str(raw_id or '').strip()
            if not name:
                continue

            dedupe_key = f"{class_id}|{name.lower()}"
            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            classes.append({
                'id': class_id or name,
                'name': name,
            })

        classes.sort(key=lambda item: item['name'].lower())
        return classes

    @staticmethod
    def _extract_properties(definition_payload: Dict) -> Dict:
        data = definition_payload.get('data')
        if not isinstance(data, dict):
            raise MFilesClientError('M-Files document definition response is missing data object')

        properties = data.get('properties')
        if not isinstance(properties, dict):
            raise MFilesClientError('M-Files document definition response is missing properties object')
        return properties

    @classmethod
    def _find_property_id(cls, definition_payload: Dict, property_name: str) -> int:
        properties = cls._extract_properties(definition_payload)
        target = property_name.strip().lower()

        for section_name in ('mandatory', 'optional'):
            items = properties.get(section_name)
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue
                item_name = str(item.get('name', '')).strip().lower()
                if item_name != target:
                    continue

                item_id = item.get('id')
                if item_id is None:
                    raise MFilesClientError(f"M-Files property '{property_name}' is missing id")

                try:
                    return int(item_id)
                except (TypeError, ValueError) as exc:
                    raise MFilesClientError(
                        f"M-Files property '{property_name}' has invalid id value: {item_id}"
                    ) from exc

        raise MFilesClientError(
            f"M-Files document definition does not contain property '{property_name}'"
        )

    def get_search_fields(self, doc_class: str = 'Drawing') -> List[Dict[str, Any]]:
        definition_payload = self.get_document_definition(doc_class=doc_class)
        properties = self._extract_properties(definition_payload)

        fields: List[Dict[str, Any]] = []
        seen_names = set()
        for section_name, required in (('mandatory', True), ('optional', False)):
            items = properties.get(section_name)
            if not isinstance(items, list):
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue

                name = str(item.get('name') or '').strip()
                if not name:
                    continue

                name_key = name.lower()
                if name_key in seen_names:
                    continue

                prop_id = item.get('id')
                if prop_id is None:
                    continue

                try:
                    field_id = int(prop_id)
                except (TypeError, ValueError):
                    continue

                seen_names.add(name_key)
                fields.append({
                    'id': field_id,
                    'name': name,
                    'required': required,
                    'data_type': item.get('dataType'),
                    'data_type_word': item.get('dataTypeWord'),
                    'system_auto_fill': bool(item.get('systemAutoFill', False)),
                })

        fields.sort(key=lambda field: str(field.get('name', '')).lower())
        return fields

    def get_projects(self, doc_class: str = 'Drawing', property_name: str = 'Project') -> List[Dict[str, str]]:
        definition_payload = self.get_document_definition(doc_class=doc_class)
        project_property_id = self._find_property_id(definition_payload, property_name)

        values_payload = self._request_get('/property/values', params={'id': project_property_id})
        if values_payload.get('success') is False:
            message = str(values_payload.get('message') or 'M-Files property values request failed')
            raise MFilesClientError(message)
        values = values_payload.get('data')
        if not isinstance(values, list):
            raise MFilesClientError('M-Files property values response is missing data array')

        projects: List[Dict[str, str]] = []
        seen_ids = set()

        for item in values:
            if not isinstance(item, dict):
                continue

            raw_id = item.get('ID')
            raw_name = item.get('Name')
            if raw_id is None or raw_name is None:
                continue

            project_id = str(raw_id).strip()
            project_name = str(raw_name).strip()
            if not project_id or not project_name:
                continue

            if project_id in seen_ids:
                continue

            seen_ids.add(project_id)
            projects.append({
                'id': project_id,
                'name': project_name,
            })

        return projects

    def get_property_values(self, property_id: int) -> List[Dict[str, str]]:
        values_payload = self._request_get('/property/values', params={'id': property_id})
        if values_payload.get('success') is False:
            message = str(values_payload.get('message') or 'M-Files property values request failed')
            raise MFilesClientError(message)

        values = values_payload.get('data')
        if not isinstance(values, list):
            raise MFilesClientError('M-Files property values response is missing data array')

        options: List[Dict[str, str]] = []
        seen_ids = set()

        for item in values:
            if not isinstance(item, dict):
                continue
            if bool(item.get('IsDeleted', False)):
                continue

            raw_id = item.get('ID')
            raw_name = item.get('Name')
            if raw_id is None or raw_name is None:
                continue

            value_id = str(raw_id).strip()
            value_name = str(raw_name).strip()
            if not value_id or not value_name or value_id in seen_ids:
                continue

            seen_ids.add(value_id)
            options.append({
                'id': value_id,
                'name': value_name,
            })

        options.sort(key=lambda option: option['name'].lower())
        return options

    def search_documents(self, criteria: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        payload = self._request_post('/document/search', {'search': criteria})
        data = payload.get('data')
        if not isinstance(data, list):
            raise MFilesClientError('M-Files document search response is missing data array')
        return data

    @staticmethod
    def _extract_filename_from_content_disposition(content_disposition: str) -> Optional[str]:
        if not content_disposition:
            return None

        filename_star_match = re.search(
            r"filename\*\s*=\s*[^']*''([^;]+)",
            content_disposition,
            flags=re.IGNORECASE
        )
        if filename_star_match:
            candidate = unquote(filename_star_match.group(1)).strip().strip('"')
            return candidate or None

        filename_match = re.search(
            r'filename\s*=\s*"?([^\";]+)"?',
            content_disposition,
            flags=re.IGNORECASE
        )
        if filename_match:
            candidate = filename_match.group(1).strip().strip('"')
            return candidate or None

        return None

    def download_document_contents(self, display_id: str) -> Dict[str, Any]:
        response = self._request_content('/document/contents', params={'id': display_id})
        content_type = response.headers.get('Content-Type', 'application/octet-stream')
        content_disposition = response.headers.get('Content-Disposition', '')
        return {
            'content': response.content,
            'content_type': content_type,
            'filename': self._extract_filename_from_content_disposition(content_disposition),
        }
