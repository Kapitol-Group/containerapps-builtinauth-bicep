"""M-Files API helper for project lookup during tender creation."""
import logging
from typing import Dict, List, Optional

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

    def _request_get(self, path: str, params: Optional[Dict] = None) -> Dict:
        self._ensure_configured()

        url = f"{self.base_url}{path}"
        headers = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'Accept': 'application/json',
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise MFilesClientError(f"M-Files request failed: {exc}") from exc

        if not response.ok:
            # Keep logs safe and compact while still exposing enough detail for troubleshooting.
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

    @staticmethod
    def _find_property_id(definition_payload: Dict, property_name: str) -> int:
        data = definition_payload.get('data')
        if not isinstance(data, dict):
            raise MFilesClientError('M-Files document definition response is missing data object')

        properties = data.get('properties')
        if not isinstance(properties, dict):
            raise MFilesClientError('M-Files document definition response is missing properties object')

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

    def get_projects(self, doc_class: str = 'Drawing', property_name: str = 'Project') -> List[Dict[str, str]]:
        definition_payload = self._request_get('/document/definition', params={'docClass': doc_class})
        if definition_payload.get('status') == 'failed':
            raise MFilesClientError('M-Files document definition request failed')
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
