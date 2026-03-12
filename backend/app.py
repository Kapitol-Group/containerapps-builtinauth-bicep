import base64
import hmac
import json
import logging
import mimetypes
import os
import re
import threading
import time
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Set

from azure.core.exceptions import ResourceNotFoundError
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from werkzeug.datastructures import FileStorage
import requests

from services.batch_metrics import (
    build_batch_metrics,
    close_active_submission_attempt,
)
from services.blob_storage import BlobStorageService, sanitize_metadata_value
from services.entity_store_submission_service import EntityStoreSubmissionService
from services.extraction_queue import ExtractionBatchMessage, ExtractionQueueService
from services.extraction_telemetry import ExtractionTelemetry, configure_process_telemetry
from services.mfiles_client import MFilesClient, MFilesClientError, MFilesConfigurationError
from services.metadata_store_factory import build_metadata_store
from utils.auth import extract_group_claims, extract_group_ids, extract_user_info, require_auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
configure_process_telemetry('kapitol-backend-api')

# Suppress verbose Azure SDK logging
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.WARNING
)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)


# Create a flask app
# Serve React build from frontend_build directory, fallback to templates/static for legacy routes
app = Flask(
    __name__,
    template_folder='templates',
    static_folder='frontend_build',
    static_url_path=''
)

# Limit max upload body to 500MB
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# CORS not needed since frontend and backend are on same origin
# CORS(app, origins=[os.getenv('FRONTEND_URL', '*')])

# Initialize services
blob_service = BlobStorageService(
    account_name=os.getenv('AZURE_STORAGE_ACCOUNT_NAME'),
    container_name=os.getenv(
        'AZURE_STORAGE_CONTAINER_NAME', 'tender-documents')
)
metadata_store = build_metadata_store(blob_service)

submission_store = EntityStoreSubmissionService(
    metadata_store=metadata_store,
)
extraction_queue = ExtractionQueueService(
    account_name=os.getenv('AZURE_STORAGE_ACCOUNT_NAME', ''),
    queue_name=os.getenv('EXTRACTION_QUEUE_NAME', 'drawing-extraction'),
)
extraction_telemetry = ExtractionTelemetry('kapitol-backend-api')

mfiles_client = MFilesClient(
    base_url=os.getenv('MFILES_BASE_URL', ''),
    client_id=os.getenv('MFILES_CLIENT_ID', ''),
    client_secret=os.getenv('MFILES_CLIENT_SECRET', ''),
    timeout_seconds=int(os.getenv('MFILES_TIMEOUT_SECONDS', '30'))
)

# SharePoint import job tracking (in-memory)
sharepoint_import_jobs = {}
mfiles_import_jobs = {}
import_jobs_lock = threading.Lock()

# Bulk upload job tracking (in-memory)
bulk_upload_jobs = {}
bulk_upload_jobs_lock = threading.Lock()

# Chunked upload tracking (in-memory)
chunked_uploads = {}
chunked_uploads_lock = threading.Lock()

# Auto-cleanup completed jobs after 1 hour
JOB_CLEANUP_SECONDS = 3600

# Keep stored batch error text compact to avoid blob metadata overflow.
MAX_BATCH_ERROR_CHARS = int(os.getenv('BATCH_METADATA_ERROR_MAX_CHARS', '512'))
BATCH_SUBMISSION_LOCK_SECONDS = int(
    os.getenv('BATCH_SUBMISSION_LOCK_SECONDS', '900'))
BATCH_PENDING_RETRY_MIN_AGE_MINUTES = int(
    os.getenv('BATCH_PENDING_RETRY_MIN_AGE_MINUTES', '5'))
BATCH_MAX_FAILED_ATTEMPTS = int(os.getenv('BATCH_MAX_FAILED_ATTEMPTS', '3'))
WEBHOOK_BATCH_COMPLETE_KEY_HEADER = 'X-Webhook-Key'
WEBHOOK_BATCH_COMPLETE_KEY = os.getenv(
    'WEBHOOK_BATCH_COMPLETE_KEY', '').strip()
MFILES_QUEUE_DEFAULTS_ADMIN_GROUP_IDS = {
    item.strip()
    for item in os.getenv('MFILES_DEFAULTS_ADMIN_GROUP_IDS', '').split(',')
    if item.strip()
}
MFILES_QUEUE_DEFAULT_RULE_TYPES = {'current_user', 'fixed_text', 'fixed_lookup'}

ALLOWED_MFILES_MODIFIERS = {
    '<', 'lt', 'lte',
    '>', 'gt', 'gte',
    'contains', 'startswith',
    'equals', '=',
    'wild', 'quick'
}

DEFAULT_MFILES_AUTOMATION_MANAGED_PROPERTIES_PATH = os.path.join(
    os.path.dirname(__file__),
    'config',
    'mfiles_automation_managed_properties.json'
)
MFILES_AUTOMATION_MANAGED_PROPERTIES_PATH = os.getenv(
    'MFILES_AUTOMATION_MANAGED_PROPERTIES_PATH',
    DEFAULT_MFILES_AUTOMATION_MANAGED_PROPERTIES_PATH
).strip() or DEFAULT_MFILES_AUTOMATION_MANAGED_PROPERTIES_PATH


def _load_mfiles_automation_managed_properties(path: str) -> Dict[str, Set[int]]:
    resolved: Dict[str, Set[int]] = {}
    if not path:
        return resolved

    if not os.path.exists(path):
        logger.info(
            "M-Files automation-managed properties file not found at %s; defaulting to empty mapping",
            path
        )
        return resolved

    try:
        with open(path, 'r', encoding='utf-8') as file_handle:
            payload = json.load(file_handle)
    except Exception as exc:
        logger.error(
            "Failed to parse M-Files automation-managed properties file at %s: %s",
            path,
            exc
        )
        return resolved

    if not isinstance(payload, dict):
        logger.error(
            "M-Files automation-managed properties config at %s must be a JSON object",
            path
        )
        return resolved

    for raw_doc_class, raw_values in payload.items():
        doc_class = str(raw_doc_class or '').strip().lower()
        if not doc_class:
            continue

        if not isinstance(raw_values, list):
            logger.warning(
                "Ignoring automation-managed properties for doc class '%s' because value is not an array",
                raw_doc_class
            )
            continue

        property_ids: Set[int] = set()
        for raw_property_id in raw_values:
            try:
                property_ids.add(int(raw_property_id))
            except (TypeError, ValueError):
                logger.warning(
                    "Ignoring invalid automation-managed property id '%s' for doc class '%s'",
                    raw_property_id,
                    raw_doc_class
                )
        resolved[doc_class] = property_ids

    return resolved


MFILES_AUTOMATION_MANAGED_PROPERTIES = _load_mfiles_automation_managed_properties(
    MFILES_AUTOMATION_MANAGED_PROPERTIES_PATH
)
logger.info(
    "Loaded M-Files automation-managed property mapping from %s (doc classes: %s)",
    MFILES_AUTOMATION_MANAGED_PROPERTIES_PATH,
    len(MFILES_AUTOMATION_MANAGED_PROPERTIES)
)


def _get_mfiles_automation_managed_property_ids(doc_class: str) -> Set[int]:
    normalized_doc_class = str(doc_class or '').strip().lower()
    combined: Set[int] = set(
        MFILES_AUTOMATION_MANAGED_PROPERTIES.get('*', set())
    )
    if normalized_doc_class:
        combined.update(
            MFILES_AUTOMATION_MANAGED_PROPERTIES.get(normalized_doc_class, set())
        )
    return combined


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y', 'on'}


def _build_seed_mfiles_queue_default_rules() -> List[Dict[str, Any]]:
    return [
        {
            'id': 'seed-document-owner-current-user',
            'document_class': '*',
            'property_name': 'Document Owner',
            'rule_type': 'current_user',
            'text_value': '',
            'lookup_value_id': '',
            'lookup_value_name': '',
            'enabled': True,
        }
    ]


def _normalize_mfiles_queue_default_rule(
    raw_rule: Any,
    index: int,
    *,
    strict: bool,
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_rule, dict):
        if strict:
            raise ValueError(f'mfiles_queue_default_rules[{index}] must be an object')
        return None

    rule_id = str(raw_rule.get('id') or '').strip() or str(uuid.uuid4())
    document_class = str(raw_rule.get('document_class') or '').strip() or '*'
    property_name = str(raw_rule.get('property_name') or '').strip()
    rule_type = str(raw_rule.get('rule_type') or '').strip().lower()

    if not property_name:
        if strict:
            raise ValueError(
                f"mfiles_queue_default_rules[{index}].property_name is required"
            )
        return None

    if rule_type not in MFILES_QUEUE_DEFAULT_RULE_TYPES:
        if strict:
            raise ValueError(
                f"mfiles_queue_default_rules[{index}].rule_type must be one of: "
                f"{', '.join(sorted(MFILES_QUEUE_DEFAULT_RULE_TYPES))}"
            )
        return None

    return {
        'id': rule_id,
        'document_class': document_class,
        'property_name': property_name,
        'rule_type': rule_type,
        'text_value': str(raw_rule.get('text_value') or '').strip(),
        'lookup_value_id': str(raw_rule.get('lookup_value_id') or '').strip(),
        'lookup_value_name': str(raw_rule.get('lookup_value_name') or '').strip(),
        'enabled': _coerce_bool(raw_rule.get('enabled', True), default=True),
    }


def _normalize_mfiles_queue_defaults_config(
    raw_config: Any,
    *,
    strict: bool,
) -> Dict[str, Any]:
    payload = raw_config if isinstance(raw_config, dict) else {}
    raw_rules = payload.get('rules', [])
    if raw_rules is None:
        raw_rules = []
    if not isinstance(raw_rules, list):
        if strict:
            raise ValueError('mfiles_queue_default_rules must be an array')
        raw_rules = []

    normalized_rules: List[Dict[str, Any]] = []
    for index, raw_rule in enumerate(raw_rules):
        normalized_rule = _normalize_mfiles_queue_default_rule(
            raw_rule,
            index,
            strict=strict,
        )
        if normalized_rule:
            normalized_rules.append(normalized_rule)

    updated_at = str(payload.get('updated_at') or datetime.utcnow().isoformat())
    return {
        'rules': normalized_rules,
        'updated_at': updated_at,
    }


def _get_seed_mfiles_queue_defaults_config() -> Dict[str, Any]:
    return {
        'rules': _build_seed_mfiles_queue_default_rules(),
        'updated_at': datetime.utcnow().isoformat(),
    }


def _get_mfiles_queue_defaults_config() -> Dict[str, Any]:
    try:
        stored = metadata_store.get_mfiles_queue_defaults()
    except Exception as exc:
        logger.error("Failed to load M-Files queue defaults from metadata store: %s", exc)
        stored = None

    if stored is None:
        seeded = _get_seed_mfiles_queue_defaults_config()
        try:
            return _normalize_mfiles_queue_defaults_config(
                metadata_store.upsert_mfiles_queue_defaults(seeded),
                strict=False,
            )
        except Exception as exc:
            logger.error("Failed to persist seeded M-Files queue defaults: %s", exc)
            return seeded

    return _normalize_mfiles_queue_defaults_config(stored, strict=False)


def _is_lookup_mfiles_field(field: Dict[str, Any]) -> bool:
    try:
        data_type = int(field.get('data_type'))
    except (TypeError, ValueError):
        return False
    return data_type in {9, 10}


def _annotate_mfiles_search_fields(
    doc_class: str,
    fields: List[Dict[str, Any]],
    user_info: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    automation_managed_property_ids = _get_mfiles_automation_managed_property_ids(
        doc_class
    )
    rules = _get_mfiles_queue_defaults_config().get('rules', [])
    current_user_name = str((user_info or {}).get('name') or '').strip()
    normalized_doc_class = str(doc_class or '').strip().lower()

    def resolve_default(field: Dict[str, Any], queue_required: bool) -> Optional[Dict[str, Any]]:
        if not queue_required:
            return None

        field_name = str(field.get('name') or '').strip()
        if not field_name:
            return None

        normalized_field_name = field_name.lower()
        matched_rule: Optional[Dict[str, Any]] = None

        for rule in rules:
            if not rule.get('enabled'):
                continue
            if str(rule.get('property_name') or '').strip().lower() != normalized_field_name:
                continue
            rule_doc_class = str(rule.get('document_class') or '').strip().lower() or '*'
            if rule_doc_class == normalized_doc_class:
                matched_rule = rule
                break
            if rule_doc_class == '*' and matched_rule is None:
                matched_rule = rule

        if not matched_rule:
            return None

        if matched_rule.get('rule_type') == 'current_user':
            return {
                'id': matched_rule.get('id'),
                'document_class': matched_rule.get('document_class'),
                'property_name': matched_rule.get('property_name'),
                'rule_type': 'current_user',
                'text_value': current_user_name,
                'lookup_value_id': '',
                'lookup_value_name': '',
            }

        if matched_rule.get('rule_type') == 'fixed_text':
            return {
                'id': matched_rule.get('id'),
                'document_class': matched_rule.get('document_class'),
                'property_name': matched_rule.get('property_name'),
                'rule_type': 'fixed_text',
                'text_value': str(matched_rule.get('text_value') or '').strip(),
                'lookup_value_id': '',
                'lookup_value_name': '',
            }

        return {
            'id': matched_rule.get('id'),
            'document_class': matched_rule.get('document_class'),
            'property_name': matched_rule.get('property_name'),
            'rule_type': 'fixed_lookup',
            'text_value': str(matched_rule.get('lookup_value_name') or '').strip(),
            'lookup_value_id': str(matched_rule.get('lookup_value_id') or '').strip(),
            'lookup_value_name': str(matched_rule.get('lookup_value_name') or '').strip(),
        }

    for field in fields:
        try:
            field_id = int(field.get('id'))
        except (TypeError, ValueError):
            field_id = None

        is_automation_managed = bool(
            field_id is not None and field_id in automation_managed_property_ids
        )
        queue_required = bool(
            field.get('required')
            and not field.get('system_auto_fill')
            and not is_automation_managed
        )
        field['automation_managed'] = is_automation_managed
        field['queue_required'] = queue_required
        resolved_default = resolve_default(field, queue_required)
        if resolved_default:
            field['queue_default'] = resolved_default

    return fields


def _get_queue_required_field_by_name(
    doc_class: str,
    *,
    cache: Dict[str, Dict[str, Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    normalized_doc_class = str(doc_class or '').strip().lower()
    if normalized_doc_class in cache:
        return cache[normalized_doc_class]

    fields = _annotate_mfiles_search_fields(
        doc_class,
        mfiles_client.get_search_fields(doc_class=doc_class),
    )
    indexed: Dict[str, Dict[str, Any]] = {}
    for field in fields:
        if not field.get('queue_required'):
            continue
        field_name = str(field.get('name') or '').strip().lower()
        if field_name and field_name not in indexed:
            indexed[field_name] = field

    cache[normalized_doc_class] = indexed
    return indexed


def _is_property_lookup_across_any_doc_class(property_name: str) -> bool:
    normalized_property_name = str(property_name or '').strip().lower()
    if not normalized_property_name:
        return False

    for doc_class in mfiles_client.get_document_classes():
        doc_class_name = str(doc_class.get('name') or '').strip()
        if not doc_class_name:
            continue
        fields = _annotate_mfiles_search_fields(
            doc_class_name,
            mfiles_client.get_search_fields(doc_class=doc_class_name),
        )
        for field in fields:
            if not field.get('queue_required'):
                continue
            if str(field.get('name') or '').strip().lower() != normalized_property_name:
                continue
            if _is_lookup_mfiles_field(field):
                return True
    return False


def _validate_mfiles_queue_default_rules(raw_rules: Any) -> List[Dict[str, Any]]:
    normalized = _normalize_mfiles_queue_defaults_config(
        {'rules': raw_rules},
        strict=True,
    )
    rules = normalized['rules']
    seen_keys: Set[str] = set()
    field_cache: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for rule in rules:
        normalized_doc_class = str(rule.get('document_class') or '').strip().lower() or '*'
        normalized_property_name = str(rule.get('property_name') or '').strip().lower()
        duplicate_key = f"{normalized_doc_class}::{normalized_property_name}"
        if duplicate_key in seen_keys:
            raise ValueError(
                f"Duplicate M-Files queue default rule for '{rule['property_name']}' in '{rule['document_class']}'"
            )
        seen_keys.add(duplicate_key)

        rule_type = rule['rule_type']
        if rule_type == 'fixed_lookup' and normalized_doc_class == '*':
            raise ValueError(
                "fixed_lookup rules require a specific document class"
            )
        if rule_type == 'fixed_text' and not str(rule.get('text_value') or '').strip():
            raise ValueError(
                f"fixed_text rule for '{rule['property_name']}' requires text_value"
            )
        if rule_type == 'fixed_lookup':
            if not str(rule.get('lookup_value_id') or '').strip():
                raise ValueError(
                    f"fixed_lookup rule for '{rule['property_name']}' requires lookup_value_id"
                )
            if not str(rule.get('lookup_value_name') or '').strip():
                raise ValueError(
                    f"fixed_lookup rule for '{rule['property_name']}' requires lookup_value_name"
                )

        if normalized_doc_class == '*':
            if rule_type == 'fixed_text' and _is_property_lookup_across_any_doc_class(
                rule['property_name']
            ):
                raise ValueError(
                    f"fixed_text rule for '{rule['property_name']}' targets a lookup field in at least one document class"
                )
            continue

        fields_by_name = _get_queue_required_field_by_name(
            rule['document_class'],
            cache=field_cache,
        )
        field = fields_by_name.get(normalized_property_name)
        if not field:
            raise ValueError(
                f"Property '{rule['property_name']}' is not a queue-visible M-Files field for document class '{rule['document_class']}'"
            )

        if rule_type == 'fixed_text' and _is_lookup_mfiles_field(field):
            raise ValueError(
                f"fixed_text rule for '{rule['property_name']}' cannot target a lookup field"
            )
        if rule_type == 'fixed_lookup' and not _is_lookup_mfiles_field(field):
            raise ValueError(
                f"fixed_lookup rule for '{rule['property_name']}' must target a lookup field"
            )

        if rule_type == 'fixed_lookup':
            try:
                property_id = int(field.get('id'))
            except (TypeError, ValueError):
                raise ValueError(
                    f"Property '{rule['property_name']}' in document class '{rule['document_class']}' has an invalid id"
                )

            property_values = mfiles_client.get_property_values(property_id)
            lookup_id = str(rule.get('lookup_value_id') or '').strip()
            lookup_name = str(rule.get('lookup_value_name') or '').strip()
            matched = next(
                (
                    item for item in property_values
                    if str(item.get('id') or '').strip() == lookup_id
                    or str(item.get('name') or '').strip().lower() == lookup_name.lower()
                ),
                None,
            )
            if not matched:
                raise ValueError(
                    f"Lookup value '{lookup_name or lookup_id}' is not valid for property '{rule['property_name']}' in document class '{rule['document_class']}'"
                )
            rule['lookup_value_id'] = str(matched.get('id') or '').strip()
            rule['lookup_value_name'] = str(matched.get('name') or '').strip()

    return rules


def _request_is_mfiles_queue_defaults_admin() -> bool:
    configured_group_ids = sorted(MFILES_QUEUE_DEFAULTS_ADMIN_GROUP_IDS)
    resolved_group_claims = extract_group_claims(request.headers)
    resolved_group_ids = sorted(extract_group_ids(request.headers))
    matching_group_ids = sorted(
        set(resolved_group_ids) & MFILES_QUEUE_DEFAULTS_ADMIN_GROUP_IDS
    )
    user_info = extract_user_info(request.headers)

    logger.info(
        "M-Files queue defaults admin access check user=%s email=%s configured_group_ids=%s resolved_group_ids=%s matching_group_ids=%s resolved_group_claims=%s",
        user_info.get('name', 'Unknown'),
        user_info.get('email'),
        configured_group_ids,
        resolved_group_ids,
        matching_group_ids,
        resolved_group_claims,
    )

    if not MFILES_QUEUE_DEFAULTS_ADMIN_GROUP_IDS:
        logger.warning(
            "M-Files queue defaults admin access denied because MFILES_DEFAULTS_ADMIN_GROUP_IDS is not configured"
        )
        return False

    is_admin = bool(matching_group_ids)
    if not is_admin:
        logger.warning(
            "M-Files queue defaults admin access denied user=%s email=%s resolved_group_ids=%s configured_group_ids=%s",
            user_info.get('name', 'Unknown'),
            user_info.get('email'),
            resolved_group_ids,
            configured_group_ids,
        )
    return is_admin


def _compact_batch_error(error: object, prefix: Optional[str] = None) -> str:
    error_text = sanitize_metadata_value(str(error))
    if prefix:
        error_text = f"{prefix}{error_text}"
    if len(error_text) <= MAX_BATCH_ERROR_CHARS:
        return error_text
    return error_text[:MAX_BATCH_ERROR_CHARS - 3] + '...'


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _build_submission_owner(source: str) -> str:
    host = os.getenv('HOSTNAME', 'local')
    return f"{source}:{host}:{os.getpid()}:{threading.get_ident()}:{uuid.uuid4().hex[:8]}"


def _normalize_mfiles_modifier(value: Any) -> str:
    modifier = str(value or '').strip().lower()
    if modifier in {'=', '<', '>'}:
        return modifier
    if not modifier:
        raise ValueError('Search modifier is required')
    if modifier not in ALLOWED_MFILES_MODIFIERS:
        raise ValueError(f"Unsupported M-Files modifier: '{modifier}'")
    return modifier


def _normalize_mfiles_criteria(raw_criteria: Any) -> List[Dict[str, str]]:
    if raw_criteria is None:
        return []
    if not isinstance(raw_criteria, list):
        raise ValueError('criteria must be an array')

    normalized: List[Dict[str, str]] = []
    reserved_names = {'project', 'class', 'keyword'}

    for index, item in enumerate(raw_criteria):
        if not isinstance(item, dict):
            raise ValueError(f'criteria[{index}] must be an object')

        name = str(item.get('name') or '').strip()
        value = str(item.get('value') or '').strip()
        modifier = _normalize_mfiles_modifier(item.get('modifier'))

        if not name and not value:
            continue
        if not name or not value:
            raise ValueError(f'criteria[{index}] must include name and value')

        if name.lower() in reserved_names:
            continue

        normalized.append({
            'name': name,
            'value': value,
            'modifier': modifier,
        })

    return normalized


def _require_mfiles_tender(tender_id: str):
    tender = metadata_store.get_tender(tender_id)
    if not tender:
        return None, (jsonify({
            'success': False,
            'error': 'Tender not found'
        }), 404)

    tender_type = str(tender.get('tender_type')
                      or 'sharepoint').strip().lower()
    if tender_type != 'mfiles':
        return None, (jsonify({
            'success': False,
            'error': 'M-Files operations are only supported for mfiles tenders'
        }), 400)

    return tender, None


def _safe_import_filename(name: str) -> str:
    candidate = str(name or '').strip()
    if not candidate:
        return ''
    candidate = candidate.replace('\\', '/').split('/')[-1]
    candidate = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', '_',
                       candidate).strip().strip('.')
    return candidate[:240]


def _normalize_mfiles_property_payload(raw_properties: Any) -> List[Dict[str, Any]]:
    if raw_properties is None:
        return []
    if not isinstance(raw_properties, list):
        raise ValueError('mfiles_properties must be an array')

    normalized: List[Dict[str, Any]] = []
    for index, item in enumerate(raw_properties):
        if not isinstance(item, dict):
            raise ValueError(f'mfiles_properties[{index}] must be an object')

        raw_property_id = item.get('property_id')
        if raw_property_id is None:
            raw_property_id = item.get('id')
        if raw_property_id is None:
            raise ValueError(
                f"mfiles_properties[{index}] is missing 'property_id'")

        try:
            property_id = int(raw_property_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"mfiles_properties[{index}].property_id must be an integer"
            ) from exc

        property_name = str(
            item.get('property_name') or item.get('name') or ''
        ).strip()
        if not property_name:
            raise ValueError(
                f"mfiles_properties[{index}] is missing 'property_name'"
            )

        normalized_item: Dict[str, Any] = {
            'property_id': property_id,
            'property_name': property_name,
        }

        raw_data_type = item.get('data_type')
        if raw_data_type is not None and raw_data_type != '':
            try:
                normalized_item['data_type'] = int(raw_data_type)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"mfiles_properties[{index}].data_type must be an integer"
                ) from exc

        raw_data_type_word = item.get('data_type_word')
        if raw_data_type_word is not None and str(raw_data_type_word).strip():
            normalized_item['data_type_word'] = str(raw_data_type_word).strip()

        value = item.get('value')
        if value is not None:
            normalized_item['value'] = str(value).strip()

        value_id = item.get('value_id')
        if value_id is not None:
            normalized_item['value_id'] = str(value_id).strip()

        value_ids_raw = item.get('value_ids')
        if value_ids_raw is not None:
            if not isinstance(value_ids_raw, list):
                raise ValueError(
                    f"mfiles_properties[{index}].value_ids must be an array"
                )
            normalized_item['value_ids'] = [
                str(entry).strip() for entry in value_ids_raw if str(entry).strip()
            ]

        values_raw = item.get('values')
        if values_raw is not None:
            if not isinstance(values_raw, list):
                raise ValueError(
                    f"mfiles_properties[{index}].values must be an array"
                )
            normalized_item['values'] = [
                str(entry).strip() for entry in values_raw if str(entry).strip()
            ]

        normalized.append(normalized_item)

    return normalized


def _validate_mfiles_extraction_properties(
    tender: Dict[str, Any],
    mfiles_document_class: str,
    raw_properties: Any,
) -> List[Dict[str, Any]]:
    submitted_properties = _normalize_mfiles_property_payload(raw_properties)
    automation_managed_property_ids = _get_mfiles_automation_managed_property_ids(
        mfiles_document_class
    )
    required_fields: List[Dict[str, Any]] = []
    for field in mfiles_client.get_search_fields(doc_class=mfiles_document_class):
        if not field.get('required') or field.get('system_auto_fill'):
            continue
        try:
            field_id = int(field.get('id'))
        except (TypeError, ValueError):
            continue
        if field_id in automation_managed_property_ids:
            continue
        required_fields.append(field)

    by_id: Dict[int, Dict[str, Any]] = {}
    by_name: Dict[str, Dict[str, Any]] = {}
    for item in submitted_properties:
        by_id[item['property_id']] = item
        by_name[item['property_name'].strip().lower()] = item

    locked_project = str(tender.get('mfiles_project_name') or '').strip()
    validated_properties: List[Dict[str, Any]] = []

    for field in required_fields:
        field_name = str(field.get('name') or '').strip()
        if not field_name:
            continue

        try:
            field_id = int(field.get('id'))
        except (TypeError, ValueError):
            raise ValueError(
                f"M-Files required field '{field_name}' has invalid id")

        submitted = by_id.get(field_id) or by_name.get(field_name.lower())
        if not submitted:
            raise ValueError(
                f"Missing mandatory M-Files property: '{field_name}'")

        data_type = field.get('data_type')
        try:
            data_type_value = int(data_type) if data_type is not None else None
        except (TypeError, ValueError):
            data_type_value = None

        normalized_property: Dict[str, Any] = {
            'property_id': field_id,
            'property_name': field_name,
            'data_type': data_type_value if data_type_value is not None else submitted.get('data_type'),
            'data_type_word': field.get('data_type_word') or submitted.get('data_type_word') or '',
        }

        if data_type_value == 10:
            value_ids = submitted.get('value_ids')
            values = submitted.get('values')
            if not isinstance(value_ids, list) or not value_ids:
                raise ValueError(
                    f"Mandatory property '{field_name}' requires value_ids")
            if not isinstance(values, list) or not values:
                raise ValueError(
                    f"Mandatory property '{field_name}' requires values")
            normalized_property['value_ids'] = value_ids
            normalized_property['values'] = values

            if field_name.lower() == 'project':
                if not locked_project:
                    raise ValueError(
                        "Tender is missing mfiles_project_name for mandatory Project property"
                    )
                if locked_project.lower() not in {str(v).strip().lower() for v in values}:
                    raise ValueError(
                        "Mandatory Project property must match tender mfiles_project_name"
                    )
        elif data_type_value == 9:
            value_id = str(submitted.get('value_id') or '').strip()
            value = str(submitted.get('value') or '').strip()
            if not value_id or not value:
                raise ValueError(
                    f"Mandatory lookup property '{field_name}' requires value_id and value"
                )
            normalized_property['value_id'] = value_id
            normalized_property['value'] = value

            if field_name.lower() == 'project':
                if not locked_project:
                    raise ValueError(
                        "Tender is missing mfiles_project_name for mandatory Project property"
                    )
                if value.lower() != locked_project.lower():
                    raise ValueError(
                        "Mandatory Project property must match tender mfiles_project_name"
                    )
        else:
            value = str(submitted.get('value') or '').strip()
            if not value:
                raise ValueError(
                    f"Mandatory property '{field_name}' requires value")
            normalized_property['value'] = value

            if field_name.lower() == 'project':
                if not locked_project:
                    raise ValueError(
                        "Tender is missing mfiles_project_name for mandatory Project property"
                    )
                if value.lower() != locked_project.lower():
                    raise ValueError(
                        "Mandatory Project property must match tender mfiles_project_name"
                    )

        validated_properties.append(normalized_property)

    return validated_properties


def _mark_batch_submission_failed(tender_id: str, batch_id: str, error: object,
                                  prefix: Optional[str] = None):
    compact_error = _compact_batch_error(error, prefix=prefix)
    try:
        batch = metadata_store.get_batch(tender_id, batch_id)
        attempts = close_active_submission_attempt(
            batch.get('submission_attempts', []) if batch else [],
            completed_at=datetime.utcnow(),
            status='failed',
            error=compact_error,
        )

        updated = metadata_store.update_batch(tender_id, batch_id, {
            'status': 'failed',
            'submission_attempts': attempts,
            'last_error': compact_error,
            'completed_at': '',
            'submission_owner': '',
            'submission_locked_until': ''
        })
        if not updated:
            logger.error(
                "[Submission] Failed to mark batch %s as failed because metadata update returned no result",
                batch_id
            )
    except Exception as update_error:
        logger.error(
            "[Submission] Failed to update batch %s to failed state: %s",
            batch_id, update_error
        )


def _validate_pdf_file_paths(tender_id: str, file_paths: List[str]) -> None:
    for file_path in file_paths:
        file_record = metadata_store.get_file(tender_id, file_path)
        if not file_record:
            raise ValueError(f"File not found: {file_path}")

        content_type = str(file_record.get('content_type') or '').lower()
        if not file_path.lower().endswith('.pdf') and 'pdf' not in content_type:
            raise ValueError(
                f"Only PDF drawings are supported for internal extraction: {file_path}"
            )


# Log startup info
logger.info("=" * 60)
logger.info("Construction Tender Automation Backend Starting")
logger.info(
    f"Storage Account: {os.getenv('AZURE_STORAGE_ACCOUNT_NAME', 'NOT SET')}")
logger.info(
    f"Container Name: {os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'tender-documents')}")
logger.info(f"Metadata Store Mode: {os.getenv('METADATA_STORE_MODE', 'blob')}")
logger.info(
    f"Extraction Queue Name: {os.getenv('EXTRACTION_QUEUE_NAME', 'drawing-extraction')}"
)
logger.info("=" * 60)

# ========== Web Routes (existing functionality) ==========


@app.get('/')
def index():
    # Serve React app index.html
    return app.send_static_file('index.html')

# Extract the username for display from the base64 encoded header
# X-MS-CLIENT-PRINCIPAL from the 'name' claim.
#
# Fallback to `default_username` if the header is not present.


def extract_username(headers, default_username="You"):
    if "X-MS-CLIENT-PRINCIPAL" not in headers:
        return default_username

    token = json.loads(base64.b64decode(headers.get("X-MS-CLIENT-PRINCIPAL")))
    claims = {claim["typ"]: claim["val"] for claim in token["claims"]}
    return claims.get("name", default_username)


@app.get('/hello')
def hello():
    return render_template('hello.html', name=extract_username(request.headers))

# ========== API Routes ==========

# Tenders API


@app.get('/api/tenders')
@require_auth
def list_tenders():
    """List all tenders"""
    try:
        logger.debug("Listing all tenders")
        tenders = metadata_store.list_tenders()
        logger.debug(f"Found {len(tenders)} tenders")
        return jsonify({
            'success': True,
            'data': tenders
        })
    except Exception as e:
        logger.error(f"Failed to list tenders: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/tenders')
@require_auth
def create_tender():
    """Create a new tender"""
    try:
        data = request.get_json(silent=True) or {}
        tender_name = data.get('name')
        tender_type = str(data.get('tender_type')
                          or 'sharepoint').strip().lower()

        # Legacy fields (kept for backward compatibility)
        sharepoint_path = data.get('sharepoint_path')
        output_location = data.get('output_location')

        # New SharePoint identifier fields
        sharepoint_site_id = data.get('sharepoint_site_id')
        sharepoint_library_id = data.get('sharepoint_library_id')
        sharepoint_folder_path = data.get('sharepoint_folder_path')

        # Output location identifier fields
        output_site_id = data.get('output_site_id')
        output_library_id = data.get('output_library_id')
        output_folder_path = data.get('output_folder_path')

        # M-Files fields
        mfiles_project_id = str(data.get('mfiles_project_id') or '').strip()
        mfiles_project_name = str(
            data.get('mfiles_project_name') or '').strip()

        if not tender_name:
            return jsonify({
                'success': False,
                'error': 'Tender name is required'
            }), 400

        if tender_type not in {'sharepoint', 'mfiles'}:
            return jsonify({
                'success': False,
                'error': "tender_type must be one of: 'sharepoint', 'mfiles'"
            }), 400

        if tender_type == 'mfiles' and (not mfiles_project_id or not mfiles_project_name):
            return jsonify({
                'success': False,
                'error': 'M-Files Project is required for mfiles tender type'
            }), 400

        user_info = extract_user_info(request.headers)
        logger.info(
            f"Creating tender: {tender_name} by {user_info.get('name', 'Unknown')}")

        # Build metadata with all SharePoint identifiers
        metadata = {
            'created_at': datetime.utcnow().isoformat(),
            'tender_type': tender_type,
        }

        # Add legacy fields if provided
        if sharepoint_path:
            metadata['sharepoint_path'] = sharepoint_path
        if output_location:
            metadata['output_location'] = output_location

        # Add new SharePoint identifier fields if provided
        if sharepoint_site_id:
            metadata['sharepoint_site_id'] = sharepoint_site_id
        if sharepoint_library_id:
            metadata['sharepoint_library_id'] = sharepoint_library_id
        if sharepoint_folder_path:
            metadata['sharepoint_folder_path'] = sharepoint_folder_path

        # Add output location identifier fields if provided
        if output_site_id:
            metadata['output_site_id'] = output_site_id
        if output_library_id:
            metadata['output_library_id'] = output_library_id
        if output_folder_path:
            metadata['output_folder_path'] = output_folder_path

        if tender_type == 'mfiles':
            metadata['mfiles_project_id'] = mfiles_project_id
            metadata['mfiles_project_name'] = mfiles_project_name

        tender = metadata_store.create_tender(
            tender_name=tender_name,
            created_by=user_info.get('name', 'Unknown'),
            metadata=metadata
        )

        logger.info(f"Successfully created tender: {tender['id']}")
        return jsonify({
            'success': True,
            'data': tender
        }), 201
    except Exception as e:
        logger.error(f"Failed to create tender: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/mfiles/projects')
@require_auth
def list_mfiles_projects():
    """List available M-Files projects for Drawing document class."""
    try:
        projects = mfiles_client.get_projects(
            doc_class='Drawing', property_name='Project')
        return jsonify({
            'success': True,
            'data': projects
        })
    except MFilesConfigurationError as e:
        logger.error("M-Files configuration error: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 503
    except MFilesClientError as e:
        logger.error("Failed to fetch M-Files projects: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 502
    except Exception as e:
        logger.error(
            "Unexpected M-Files project lookup failure: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch projects from M-Files'
        }), 500


@app.get('/api/mfiles/document-classes')
@require_auth
def list_mfiles_document_classes():
    """List available M-Files document classes."""
    try:
        document_classes = mfiles_client.get_document_classes()
        return jsonify({
            'success': True,
            'data': document_classes
        })
    except MFilesConfigurationError as e:
        logger.error("M-Files configuration error: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 503
    except MFilesClientError as e:
        logger.error("Failed to fetch M-Files document classes: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 502
    except Exception as e:
        logger.error("Unexpected M-Files class lookup failure: %s",
                     e, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch document classes from M-Files'
        }), 500


@app.get('/api/mfiles/search-fields')
@require_auth
def list_mfiles_search_fields():
    """List searchable field definitions for a given M-Files document class."""
    try:
        doc_class = str(request.args.get('docClass')
                        or 'Drawing').strip() or 'Drawing'
        user_info = extract_user_info(request.headers)
        fields = _annotate_mfiles_search_fields(
            doc_class,
            mfiles_client.get_search_fields(doc_class=doc_class),
            user_info=user_info,
        )

        return jsonify({
            'success': True,
            'data': fields
        })
    except MFilesConfigurationError as e:
        logger.error("M-Files configuration error: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 503
    except MFilesClientError as e:
        logger.error("Failed to fetch M-Files search fields: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 502
    except Exception as e:
        logger.error(
            "Unexpected M-Files search field lookup failure: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch search fields from M-Files'
        }), 500


@app.get('/api/mfiles/property-values')
@require_auth
def list_mfiles_property_values():
    """List allowed values for an M-Files property definition."""
    try:
        raw_property_id = request.args.get('id')
        if raw_property_id is None:
            return jsonify({
                'success': False,
                'error': 'Property id is required'
            }), 400

        try:
            property_id = int(raw_property_id)
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'error': 'Property id must be an integer'
            }), 400

        values = mfiles_client.get_property_values(property_id)
        return jsonify({
            'success': True,
            'data': values
        })
    except MFilesConfigurationError as e:
        logger.error("M-Files configuration error: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 503
    except MFilesClientError as e:
        logger.error("Failed to fetch M-Files property values: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 502
    except Exception as e:
        logger.error(
            "Unexpected M-Files property values failure: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch property values from M-Files'
        }), 500


@app.get('/api/admin/mfiles-queue-defaults')
@require_auth
def get_mfiles_queue_defaults():
    """Return persisted M-Files queue extraction default rules for admin management."""
    if not _request_is_mfiles_queue_defaults_admin():
        return jsonify({
            'success': False,
            'error': 'Admin access is required'
        }), 403

    try:
        return jsonify({
            'success': True,
            'data': _get_mfiles_queue_defaults_config()
        })
    except Exception as exc:
        logger.error("Failed to load M-Files queue defaults: %s", exc, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to load M-Files queue defaults'
        }), 500


@app.put('/api/admin/mfiles-queue-defaults')
@require_auth
def update_mfiles_queue_defaults():
    """Persist M-Files queue extraction default rules after validation."""
    if not _request_is_mfiles_queue_defaults_admin():
        return jsonify({
            'success': False,
            'error': 'Admin access is required'
        }), 403

    try:
        data = request.get_json(silent=True) or {}
        raw_rules = data.get('rules')
        if raw_rules is None:
            return jsonify({
                'success': False,
                'error': 'rules is required'
            }), 400

        validated_rules = _validate_mfiles_queue_default_rules(raw_rules)
        config = {
            'rules': validated_rules,
            'updated_at': datetime.utcnow().isoformat(),
        }
        saved = metadata_store.upsert_mfiles_queue_defaults(config)
        return jsonify({
            'success': True,
            'data': _normalize_mfiles_queue_defaults_config(saved, strict=False)
        })
    except ValueError as exc:
        return jsonify({
            'success': False,
            'error': str(exc)
        }), 400
    except MFilesConfigurationError as exc:
        logger.error("M-Files configuration error while saving queue defaults: %s", exc)
        return jsonify({
            'success': False,
            'error': str(exc)
        }), 503
    except MFilesClientError as exc:
        logger.error("M-Files request failed while saving queue defaults: %s", exc)
        return jsonify({
            'success': False,
            'error': str(exc)
        }), 502
    except Exception as exc:
        logger.error("Failed to update M-Files queue defaults: %s", exc, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to update M-Files queue defaults'
        }), 500


@app.post('/api/mfiles/search')
@require_auth
def search_mfiles_documents():
    """Search M-Files documents for a tender using metadata criteria."""
    try:
        data = request.get_json(silent=True) or {}
        tender_id = str(data.get('tender_id') or '').strip()
        if not tender_id:
            return jsonify({
                'success': False,
                'error': 'tender_id is required'
            }), 400

        tender, error_response = _require_mfiles_tender(tender_id)
        if error_response:
            return error_response

        locked_project = str(tender.get('mfiles_project_name') or '').strip()
        if not locked_project:
            return jsonify({
                'success': False,
                'error': 'Tender is missing mfiles_project_name'
            }), 400

        doc_class = str(data.get('doc_class') or data.get(
            'class') or 'Drawing').strip()
        keyword = str(data.get('keyword') or '').strip()
        user_criteria = _normalize_mfiles_criteria(data.get('criteria'))

        criteria: List[Dict[str, str]] = [{
            'name': 'Project',
            'value': locked_project,
            'modifier': '=',
        }]

        if doc_class:
            criteria.append({
                'name': 'Class',
                'value': doc_class,
                'modifier': '=',
            })

        if keyword:
            criteria.append({
                'name': 'keyword',
                'value': keyword,
                'modifier': 'quick',
            })

        criteria.extend(user_criteria)

        raw_results = mfiles_client.search_documents(criteria)
        normalized_results = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue

            display_id = str(item.get('DisplayID') or '').strip()
            if not display_id:
                continue

            files = item.get('Files')
            file_names: List[str] = []
            file_type = ''
            if isinstance(files, list):
                for file_item in files:
                    if not isinstance(file_item, dict):
                        continue
                    file_name = str(file_item.get('Name') or '').strip()
                    if file_name:
                        file_names.append(file_name)
                        if not file_type and '.' in file_name:
                            file_type = file_name.rsplit(
                                '.', 1)[-1].strip().lower()

                    if not file_type:
                        extension = str(file_item.get('Extension')
                                        or '').strip().lower().lstrip('.')
                        if extension:
                            file_type = extension

            raw_score = item.get('Score')
            try:
                score = float(raw_score) if raw_score is not None else None
            except (TypeError, ValueError):
                score = None

            normalized_results.append({
                'title': str(item.get('Title') or '').strip() or display_id,
                'display_id': display_id,
                'score': score,
                'single_file': bool(item.get('SingleFile', False)),
                'last_modified': item.get('LastModified') or item.get('LastModifiedDisplayValue'),
                'file_count': len(file_names),
                'file_names': file_names,
                'primary_filename': file_names[0] if file_names else '',
                'file_type': file_type,
            })

        return jsonify({
            'success': True,
            'data': {
                'criteria': criteria,
                'results': normalized_results
            }
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except MFilesConfigurationError as e:
        logger.error("M-Files configuration error: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 503
    except MFilesClientError as e:
        logger.error("M-Files document search failed: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 502
    except Exception as e:
        logger.error("Unexpected M-Files search failure: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to search M-Files documents'
        }), 500


@app.post('/api/mfiles/import-files')
@require_auth
def import_mfiles_files():
    """Start background import job for selected M-Files documents."""
    try:
        data = request.get_json(silent=True) or {}
        tender_id = str(data.get('tender_id') or '').strip()
        documents = data.get('documents') or []
        category = str(data.get('category')
                       or 'mfiles-import').strip() or 'mfiles-import'

        if not tender_id:
            return jsonify({
                'success': False,
                'error': 'tender_id is required'
            }), 400

        if not isinstance(documents, list) or not documents:
            return jsonify({
                'success': False,
                'error': 'documents must be a non-empty array'
            }), 400

        tender, error_response = _require_mfiles_tender(tender_id)
        if error_response:
            return error_response

        selected_documents = []
        for index, item in enumerate(documents):
            if not isinstance(item, dict):
                return jsonify({
                    'success': False,
                    'error': f'documents[{index}] must be an object'
                }), 400

            display_id = str(
                item.get('display_id')
                or item.get('displayId')
                or item.get('id')
                or ''
            ).strip()
            if not display_id:
                return jsonify({
                    'success': False,
                    'error': f'documents[{index}] is missing display_id'
                }), 400

            selected_documents.append({
                'display_id': display_id,
                'title': str(item.get('title') or '').strip(),
                'filename': str(item.get('filename') or item.get('name') or '').strip(),
            })

        user_info = extract_user_info(request.headers)
        imported_by = user_info.get('name', 'M-Files Import')

        job_id = str(uuid.uuid4())
        with import_jobs_lock:
            mfiles_import_jobs[job_id] = {
                'job_id': job_id,
                'tender_id': tender_id,
                'tender_name': tender.get('name', tender_id),
                'status': 'running',
                'progress': 0,
                'total': len(selected_documents),
                'current_file': '',
                'success_count': 0,
                'error_count': 0,
                'errors': [],
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

        import_thread = threading.Thread(
            target=_process_mfiles_import,
            args=(job_id, tender_id, selected_documents, category, imported_by),
            daemon=True
        )
        import_thread.start()

        logger.info(
            "Started M-Files import job %s for tender %s with %s documents",
            job_id,
            tender_id,
            len(selected_documents),
        )

        return jsonify({
            'success': True,
            'data': {
                'job_id': job_id,
                'status': 'running',
                'total': len(selected_documents),
            }
        })
    except Exception as e:
        logger.error("Failed to start M-Files import: %s", e, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/mfiles/import-jobs/<job_id>')
@require_auth
def get_mfiles_import_job_status(job_id: str):
    """Get status of an M-Files import job."""
    try:
        with import_jobs_lock:
            job = mfiles_import_jobs.get(job_id)

        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404

        return jsonify({
            'success': True,
            'data': job
        })
    except Exception as e:
        logger.error("Failed to get M-Files import job status: %s",
                     e, exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Extraction queue helpers


def _process_uipath_submission_async(
    tender_id: str,
    tender_name: str,
    batch_id: str,
    file_paths: list,
    category: str,
    title_block_coords: dict,
    user_email: str,
    sharepoint_folder_path: str,
    output_folder_path: str,
    folder_list: list = None,
    mfiles_document_class: str = '',
    mfiles_properties: Optional[List[Dict[str, Any]]] = None,
    claim_before_submit: bool = True,
    claim_allowed_statuses: Optional[list] = None,
    attempt_source: str = 'submission',
    claim_owner: Optional[str] = None,
    raise_on_error: bool = False,
    reset_failed_files: bool = False,
):
    """
    Submit a batch to the internal extraction queue after ensuring Entity Store records exist.
    This function remains idempotent so manual retries and automatic stuck-batch retries can reuse it.
    """
    try:
        logger.info(
            "[Submission] Starting internal extraction submission for batch %s",
            batch_id
        )

        batch = None
        if claim_before_submit:
            owner = claim_owner or _build_submission_owner(attempt_source)
            allowed = claim_allowed_statuses or [
                'pending', 'failed', 'submitting']
            batch = metadata_store.claim_batch_for_submission(
                tender_id=tender_id,
                batch_id=batch_id,
                owner=owner,
                allowed_statuses=allowed,
                lock_seconds=BATCH_SUBMISSION_LOCK_SECONDS,
                attempt_source=attempt_source,
                submitted_by=user_email,
            )
            if not batch:
                logger.info(
                    "[Background] Skipping submission for batch %s: claim rejected",
                    batch_id
                )
                return
        else:
            batch = metadata_store.get_batch(tender_id, batch_id)
            if not batch:
                logger.warning(
                    "[Submission] Batch %s not found during submission", batch_id)
                return

        attempts = batch.get('submission_attempts', []) if batch else []
        existing_reference = batch.get('uipath_reference', '') if batch else ''
        reference = existing_reference or f"batch-{batch_id}"

        context = submission_store.ensure_submission_records(
            tender_id=tender_id,
            file_paths=file_paths,
            submitted_by=user_email,
            reference=reference,
            sharepoint_folder_path=sharepoint_folder_path,
            output_folder_path=output_folder_path,
            folder_list=folder_list,
            reset_failed_files=reset_failed_files or bool(
                batch and batch.get('status') == 'failed'
            ),
        )
        extraction_queue.enqueue_batch(
            ExtractionBatchMessage(
                tender_id=tender_id,
                batch_id=batch_id,
                reference=context.reference,
            )
        )
        extraction_telemetry.record_enqueue(
            tender_id=tender_id,
            batch_id=batch_id,
            file_count=len(file_paths),
        )

        logger.info(
            "[Submission] Successfully queued batch %s with reference %s",
            batch_id,
            context.reference,
        )

        attempts = close_active_submission_attempt(
            attempts,
            completed_at=datetime.utcnow(),
            status='success',
            reference=context.reference,
        )

        updated = metadata_store.update_batch(tender_id, batch_id, {
            'status': 'running',
            'uipath_reference': context.reference,
            'uipath_submission_id': context.submission_id,
            'uipath_project_id': context.project_id,
            'submission_attempts': attempts,
            'last_error': '',
            'completed_at': '',
            'submission_owner': '',
            'submission_locked_until': ''
        })
        if not updated:
            raise RuntimeError(
                "Batch metadata update returned no result after queue submission")

    except ValueError as user_error:
        logger.error(
            "[Submission] User validation failed for batch %s: %s",
            batch_id, user_error
        )
        _mark_batch_submission_failed(
            tender_id=tender_id,
            batch_id=batch_id,
            error=user_error,
            prefix='User validation failed: '
        )
        if raise_on_error:
            raise

    except Exception as e:
        logger.error(
            "[Submission] Internal extraction submission failed for batch %s: %s",
            batch_id, e, exc_info=True
        )
        _mark_batch_submission_failed(
            tender_id=tender_id,
            batch_id=batch_id,
            error=e
        )
        if raise_on_error:
            raise


def retry_stuck_batches():
    """
    Background worker that periodically retries batches stuck in 'pending' status.
    Runs every 5 minutes to find and retry batches that failed before they were enqueued.
    """
    logger.info("[Retry Worker] Starting stuck batch retry worker")

    while True:
        try:
            time.sleep(300)  # 5 minutes
            logger.info("[Retry Worker] Checking for stuck batches...")

            tenders = metadata_store.list_tenders()
            stuck_count = 0
            retry_count = 0

            for tender in tenders:
                tender_id = tender['id']
                tender_name = tender.get('name', tender_id)

                try:
                    batches = metadata_store.list_batches(tender_id)
                except Exception as tender_error:
                    logger.error(
                        "[Retry Worker] Error listing batches for tender %s: %s",
                        tender_id, tender_error
                    )
                    continue

                for batch in batches:
                    batch_id = batch.get('batch_id')
                    if not batch_id:
                        continue

                    try:
                        status = batch.get('status', 'pending')
                        attempts = batch.get('submission_attempts', [])
                        failed_attempts = [
                            a for a in attempts if a.get('status') == 'failed'
                        ]

                        if len(failed_attempts) >= BATCH_MAX_FAILED_ATTEMPTS:
                            if status != 'failed':
                                metadata_store.update_batch(tender_id, batch_id, {
                                    'status': 'failed',
                                    'last_error': f'Maximum retry limit reached after {len(failed_attempts)} failed attempts',
                                    'completed_at': '',
                                    'submission_owner': '',
                                    'submission_locked_until': ''
                                })
                            continue

                        allow_statuses = None
                        if status == 'pending':
                            submitted_at = _parse_iso_datetime(
                                batch.get('submitted_at'))
                            if not submitted_at:
                                continue
                            age = datetime.utcnow() - submitted_at
                            if age <= timedelta(minutes=BATCH_PENDING_RETRY_MIN_AGE_MINUTES):
                                continue
                            allow_statuses = ['pending']
                            stuck_count += 1
                        elif status == 'submitting':
                            lock_until = _parse_iso_datetime(
                                batch.get('submission_locked_until'))
                            if lock_until and lock_until > datetime.utcnow():
                                continue
                            allow_statuses = ['submitting']
                            stuck_count += 1
                        else:
                            continue

                        submitted_by = batch.get('submitted_by', 'system')
                        owner = _build_submission_owner('auto-retry')
                        claimed = metadata_store.claim_batch_for_submission(
                            tender_id=tender_id,
                            batch_id=batch_id,
                            owner=owner,
                            allowed_statuses=allow_statuses,
                            lock_seconds=BATCH_SUBMISSION_LOCK_SECONDS,
                            attempt_source='auto-retry',
                            submitted_by=submitted_by
                        )
                        if not claimed:
                            continue

                        _process_uipath_submission_async(
                            tender_id=tender_id,
                            tender_name=tender_name,
                            batch_id=batch_id,
                            file_paths=claimed.get('file_paths', []),
                            category=claimed.get('discipline') or 'Unknown',
                            title_block_coords=claimed.get(
                                'title_block_coords', {}),
                            user_email=submitted_by,
                            sharepoint_folder_path=claimed.get(
                                'sharepoint_folder_path', ''),
                            output_folder_path=claimed.get(
                                'output_folder_path', ''),
                            folder_list=claimed.get('folder_list', []),
                            mfiles_document_class=claimed.get(
                                'mfiles_document_class', ''),
                            mfiles_properties=claimed.get(
                                'mfiles_properties', []),
                            claim_before_submit=False,
                            attempt_source='auto-retry',
                            claim_owner=owner,
                        )
                        retry_count += 1

                    except Exception as retry_error:
                        logger.error(
                            "[Retry Worker] Retry failed for batch %s in tender %s: %s",
                            batch_id, tender_id, retry_error
                        )

            if stuck_count > 0:
                logger.info(
                    "[Retry Worker] Retry cycle complete: found %s stuck batches, successfully retried %s",
                    stuck_count, retry_count
                )
            else:
                logger.debug("[Retry Worker] No stuck batches found")

        except Exception as e:
            logger.error(
                "[Retry Worker] Error in retry loop: %s", e, exc_info=True)


# Start retry worker thread
retry_thread = threading.Thread(target=retry_stuck_batches, daemon=True)
retry_thread.start()
logger.info("Started retry worker thread")


@app.get('/api/tenders/<tender_id>')
@require_auth
def get_tender(tender_id: str):
    """Get tender details"""
    try:
        tender = metadata_store.get_tender(tender_id)
        if not tender:
            return jsonify({
                'success': False,
                'error': 'Tender not found'
            }), 404

        return jsonify({
            'success': True,
            'data': tender
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.delete('/api/tenders/<tender_id>')
@require_auth
def delete_tender(tender_id: str):
    """Delete a tender"""
    try:
        logger.info(f"Attempting to delete tender: {tender_id}")
        # Delete blob content first, then metadata records.
        blob_service.delete_tender(tender_id)
        metadata_store.delete_tender(tender_id)
        logger.info(f"Successfully deleted tender: {tender_id}")
        return jsonify({
            'success': True,
            'message': 'Tender deleted successfully'
        })
    except Exception as e:
        logger.error(
            f"Failed to delete tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Files API


@app.get('/api/tenders/<tender_id>/files')
@require_auth
def list_files(tender_id: str):
    """List files in a tender"""
    try:
        # Get exclude_batched query parameter (default: False)
        exclude_batched = request.args.get(
            'exclude_batched', 'false').lower() == 'true'

        files = metadata_store.list_files(
            tender_id, exclude_batched=exclude_batched)
        return jsonify({
            'success': True,
            'data': files
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/tenders/<tender_id>/files')
@require_auth
def upload_file(tender_id: str):
    """Upload a file to a tender"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400

        file = request.files['file']
        category = request.form.get('category', 'uncategorized')
        source = request.form.get('source', 'local')  # 'local' or 'sharepoint'

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400

        user_info = extract_user_info(request.headers)
        logger.info(
            f"Uploading file {file.filename} to tender {tender_id}, category: {category}, source: {source}")

        file_info = blob_service.upload_file(
            tender_id=tender_id,
            file=file,
            category=category,
            uploaded_by=user_info.get('name', 'Unknown'),
            source=source
        )

        try:
            metadata_store.upsert_file_record(tender_id, file_info)
        except Exception as metadata_error:
            logger.error(
                "Metadata write failed after blob upload for %s. Deleting blob for compensation.",
                file_info.get('path'),
                exc_info=True
            )
            try:
                blob_service.delete_file(tender_id, file_info.get('path'))
                logger.warning(
                    "Compensation succeeded for file %s", file_info.get('path'))
            except Exception as rollback_error:
                logger.error(
                    "Compensation failed for uploaded file %s: %s",
                    file_info.get('path'),
                    rollback_error,
                    exc_info=True
                )
            raise metadata_error

        logger.info(
            f"Successfully uploaded file {file.filename} to tender {tender_id}")
        return jsonify({
            'success': True,
            'data': file_info
        }), 201
    except Exception as e:
        logger.error(
            f"Failed to upload file to tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ---- Bulk Upload Endpoints ----


@app.post('/api/tenders/<tender_id>/files/bulk')
@require_auth
def bulk_upload_files(tender_id: str):
    """Accept multiple files in one request and process them in a background thread"""
    try:
        files = request.files.getlist('files')
        category = request.form.get('category', 'uncategorized')

        if not files:
            return jsonify({
                'success': False,
                'error': 'No files provided'
            }), 400

        # Verify tender exists
        tender = metadata_store.get_tender(tender_id)
        if not tender:
            return jsonify({
                'success': False,
                'error': 'Tender not found'
            }), 404

        user_info = extract_user_info(request.headers)

        # Buffer all file data into memory (request.files won't survive past the request)
        file_items = []
        for f in files:
            data = BytesIO(f.read())
            file_items.append({
                'data': data,
                'filename': f.filename,
                'content_type': f.content_type or 'application/octet-stream',
            })

        job_id = str(uuid.uuid4())

        with bulk_upload_jobs_lock:
            bulk_upload_jobs[job_id] = {
                'job_id': job_id,
                'tender_id': tender_id,
                'status': 'running',
                'progress': 0,
                'total': len(file_items),
                'current_file': '',
                'success_count': 0,
                'error_count': 0,
                'errors': [],
                'cancelled': False,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
            }

        t = threading.Thread(
            target=_process_bulk_upload,
            args=(job_id, tender_id, file_items, category, user_info),
            daemon=True,
        )
        t.start()

        logger.info(
            f"Started bulk upload job {job_id} for tender {tender_id} with {len(file_items)} files")

        return jsonify({
            'success': True,
            'data': {
                'job_id': job_id,
                'total_files': len(file_items),
            }
        }), 202

    except Exception as e:
        logger.error(
            f"Failed to start bulk upload: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/tenders/<tender_id>/files/bulk-jobs/<job_id>')
@require_auth
def get_bulk_upload_job_status(tender_id: str, job_id: str):
    """Get status of a bulk upload job"""
    try:
        with bulk_upload_jobs_lock:
            job = bulk_upload_jobs.get(job_id)

        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404

        # Don't expose internal fields
        safe_job = {k: v for k, v in job.items() if k != 'cancelled'}
        return jsonify({'success': True, 'data': safe_job})
    except Exception as e:
        logger.error(
            f"Failed to get bulk job status: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.post('/api/tenders/<tender_id>/files/bulk-jobs/<job_id>/cancel')
@require_auth
def cancel_bulk_upload_job(tender_id: str, job_id: str):
    """Cancel a running bulk upload job"""
    try:
        with bulk_upload_jobs_lock:
            job = bulk_upload_jobs.get(job_id)
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
            job['cancelled'] = True
            job['updated_at'] = datetime.utcnow().isoformat()

        return jsonify({'success': True, 'data': {'message': 'Cancellation requested'}})
    except Exception as e:
        logger.error(
            f"Failed to cancel bulk job: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


def _process_bulk_upload(job_id: str, tender_id: str, file_items: list,
                         category: str, user_info: dict):
    """Background thread to process bulk file uploads"""
    try:
        for i, item in enumerate(file_items):
            # Check for cancellation
            with bulk_upload_jobs_lock:
                job = bulk_upload_jobs.get(job_id, {})
                if job.get('cancelled'):
                    job['status'] = 'cancelled'
                    job['updated_at'] = datetime.utcnow().isoformat()
                    logger.info(
                        f"Bulk upload job {job_id} cancelled at file {i}/{len(file_items)}")
                    _schedule_job_cleanup(job_id, 'bulk')
                    return

            file_name = item['filename']
            with bulk_upload_jobs_lock:
                if job_id in bulk_upload_jobs:
                    bulk_upload_jobs[job_id]['current_file'] = file_name
                    bulk_upload_jobs[job_id]['progress'] = i
                    bulk_upload_jobs[job_id]['updated_at'] = datetime.utcnow(
                    ).isoformat()

            try:
                file_storage = FileStorage(
                    stream=item['data'],
                    filename=file_name,
                    content_type=item['content_type'],
                )
                uploaded_info = blob_service.upload_file(
                    tender_id=tender_id,
                    file=file_storage,
                    category=category,
                    uploaded_by=user_info.get('name', 'Unknown'),
                    source='local',
                )
                try:
                    metadata_store.upsert_file_record(tender_id, uploaded_info)
                except Exception:
                    logger.error(
                        "Bulk upload metadata write failed for %s. Deleting blob for compensation.",
                        uploaded_info.get('path'),
                        exc_info=True
                    )
                    try:
                        blob_service.delete_file(
                            tender_id, uploaded_info.get('path'))
                    except Exception:
                        logger.error(
                            "Bulk upload compensation failed for %s",
                            uploaded_info.get('path'),
                            exc_info=True
                        )
                    raise
                with bulk_upload_jobs_lock:
                    if job_id in bulk_upload_jobs:
                        bulk_upload_jobs[job_id]['success_count'] += 1
                logger.info(
                    f"Bulk upload: uploaded {file_name} ({i+1}/{len(file_items)}) job {job_id}")
            except Exception as item_err:
                error_msg = f"{file_name}: {str(item_err)}"
                logger.error(
                    f"Bulk upload failed for {file_name} in job {job_id}: {str(item_err)}")
                with bulk_upload_jobs_lock:
                    if job_id in bulk_upload_jobs:
                        bulk_upload_jobs[job_id]['error_count'] += 1
                        bulk_upload_jobs[job_id]['errors'].append(error_msg)

        # Complete
        with bulk_upload_jobs_lock:
            if job_id in bulk_upload_jobs:
                job = bulk_upload_jobs[job_id]
                job['status'] = 'completed' if job[
                    'error_count'] == 0 else 'completed_with_errors'
                job['progress'] = len(file_items)
                job['current_file'] = ''
                job['updated_at'] = datetime.utcnow().isoformat()
                job['completed_at'] = datetime.utcnow().isoformat()

        logger.info(
            f"Bulk upload job {job_id} completed: "
            f"{bulk_upload_jobs[job_id]['success_count']} ok, "
            f"{bulk_upload_jobs[job_id]['error_count']} failed")
        _schedule_job_cleanup(job_id, 'bulk')

    except Exception as e:
        logger.error(
            f"Fatal error in bulk upload job {job_id}: {str(e)}", exc_info=True)
        with bulk_upload_jobs_lock:
            if job_id in bulk_upload_jobs:
                bulk_upload_jobs[job_id]['status'] = 'failed'
                bulk_upload_jobs[job_id]['errors'].append(f"Fatal: {str(e)}")
                bulk_upload_jobs[job_id]['updated_at'] = datetime.utcnow(
                ).isoformat()
        _schedule_job_cleanup(job_id, 'bulk')


# ---- Chunked Upload Endpoints ----

CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB


@app.post('/api/tenders/<tender_id>/uploads/init')
@require_auth
def init_chunked_upload(tender_id: str):
    """Initialize a chunked upload for a large file"""
    try:
        data = request.json
        filename = data.get('filename')
        size = data.get('size', 0)
        category = data.get('category', 'uncategorized')
        content_type = data.get('content_type', 'application/octet-stream')

        if not filename or size <= 0:
            return jsonify({
                'success': False,
                'error': 'filename and size are required'
            }), 400

        # Verify tender exists
        tender = metadata_store.get_tender(tender_id)
        if not tender:
            return jsonify({'success': False, 'error': 'Tender not found'}), 404

        upload_id = str(uuid.uuid4())
        total_chunks = -(-size // CHUNK_SIZE)  # ceil division

        user_info = extract_user_info(request.headers)

        with chunked_uploads_lock:
            chunked_uploads[upload_id] = {
                'upload_id': upload_id,
                'tender_id': tender_id,
                'filename': filename,
                'size': size,
                'category': category,
                'content_type': content_type,
                'total_chunks': total_chunks,
                'completed_chunks': set(),
                'block_ids': [None] * total_chunks,
                'uploaded_by': user_info.get('name', 'Unknown'),
                'created_at': datetime.utcnow().isoformat(),
            }

        logger.info(
            f"Initialized chunked upload {upload_id}: "
            f"{filename} ({size} bytes, {total_chunks} chunks)")

        return jsonify({
            'success': True,
            'data': {
                'upload_id': upload_id,
                'chunk_size': CHUNK_SIZE,
                'total_chunks': total_chunks,
            }
        })
    except Exception as e:
        logger.error(
            f"Failed to init chunked upload: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.put('/api/tenders/<tender_id>/uploads/<upload_id>/chunks/<int:chunk_index>')
@require_auth
def upload_chunk(tender_id: str, upload_id: str, chunk_index: int):
    """Upload a single chunk of a file"""
    try:
        with chunked_uploads_lock:
            upload = chunked_uploads.get(upload_id)
            if not upload:
                return jsonify({
                    'success': False,
                    'error': 'Upload not found'
                }), 404

        if chunk_index < 0 or chunk_index >= upload['total_chunks']:
            return jsonify({
                'success': False,
                'error': 'Invalid chunk index'
            }), 400

        chunk_data = request.get_data()
        if not chunk_data:
            return jsonify({'success': False, 'error': 'No chunk data'}), 400

        # Stage block in Azure Blob Storage
        blob_name = f"{tender_id}/{upload['category']}/{upload['filename']}"
        block_id = blob_service.stage_chunk(
            blob_name=blob_name,
            chunk_index=chunk_index,
            data=chunk_data,
        )

        with chunked_uploads_lock:
            if upload_id in chunked_uploads:
                chunked_uploads[upload_id]['completed_chunks'].add(chunk_index)
                chunked_uploads[upload_id]['block_ids'][chunk_index] = block_id

        return jsonify({'success': True, 'data': {'chunk_index': chunk_index}})
    except Exception as e:
        logger.error(
            f"Failed to upload chunk {chunk_index} for {upload_id}: {str(e)}",
            exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.post('/api/tenders/<tender_id>/uploads/<upload_id>/complete')
@require_auth
def complete_chunked_upload(tender_id: str, upload_id: str):
    """Finalize a chunked upload by committing all blocks"""
    try:
        with chunked_uploads_lock:
            upload = chunked_uploads.get(upload_id)
            if not upload:
                return jsonify({
                    'success': False,
                    'error': 'Upload not found'
                }), 404

        # Verify all chunks are present
        if len(upload['completed_chunks']) < upload['total_chunks']:
            missing = set(range(upload['total_chunks'])
                          ) - upload['completed_chunks']
            return jsonify({
                'success': False,
                'error': f"Missing chunks: {sorted(missing)}"
            }), 400

        # Commit block list
        blob_name = f"{tender_id}/{upload['category']}/{upload['filename']}"
        block_ids = upload['block_ids']

        metadata = {
            'category': sanitize_metadata_value(upload['category']),
            'uploaded_by': sanitize_metadata_value(upload['uploaded_by']),
            'uploaded_at': datetime.utcnow().isoformat(),
            'original_filename': sanitize_metadata_value(upload['filename']),
            'source': 'local',
        }

        committed = blob_service.commit_chunks(
            blob_name=blob_name,
            block_ids=block_ids,
            content_type=upload['content_type'],
            metadata=metadata,
        )

        file_record = {
            'name': upload['filename'],
            'path': blob_name,
            'size': committed.get('size', upload.get('size', 0)),
            'content_type': committed.get('content_type', upload['content_type']),
            'category': upload['category'],
            'uploaded_by': upload['uploaded_by'],
            'uploaded_at': metadata['uploaded_at'],
            'last_modified': committed.get('last_modified'),
            'source': 'local',
        }

        try:
            metadata_store.upsert_file_record(tender_id, file_record)
        except Exception as metadata_error:
            logger.error(
                "Metadata write failed after chunked commit for %s. Deleting blob for compensation.",
                blob_name,
                exc_info=True
            )
            try:
                blob_service.delete_file(tender_id, blob_name)
                logger.warning(
                    "Compensation succeeded for chunked file %s", blob_name)
            except Exception as rollback_error:
                logger.error(
                    "Compensation failed for chunked file %s: %s",
                    blob_name,
                    rollback_error,
                    exc_info=True
                )
            raise metadata_error

        # Cleanup
        with chunked_uploads_lock:
            chunked_uploads.pop(upload_id, None)

        result = file_record

        logger.info(
            f"Completed chunked upload {upload_id}: {upload['filename']}")
        return jsonify({'success': True, 'data': result}), 201

    except Exception as e:
        logger.error(
            f"Failed to complete chunked upload {upload_id}: {str(e)}",
            exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.get('/api/tenders/<tender_id>/uploads/<upload_id>/status')
@require_auth
def get_chunked_upload_status(tender_id: str, upload_id: str):
    """Get the status of a chunked upload (which chunks uploaded)"""
    try:
        with chunked_uploads_lock:
            upload = chunked_uploads.get(upload_id)
            if not upload:
                return jsonify({
                    'success': False,
                    'error': 'Upload not found'
                }), 404

        return jsonify({
            'success': True,
            'data': {
                'completed_chunks': sorted(upload['completed_chunks']),
                'total_chunks': upload['total_chunks'],
            }
        })
    except Exception as e:
        logger.error(
            f"Failed to get chunked upload status: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.delete('/api/tenders/<tender_id>/uploads/<upload_id>')
@require_auth
def abort_chunked_upload(tender_id: str, upload_id: str):
    """Abort and cleanup a chunked upload"""
    try:
        with chunked_uploads_lock:
            upload = chunked_uploads.pop(upload_id, None)

        if not upload:
            return jsonify({
                'success': False,
                'error': 'Upload not found'
            }), 404

        logger.info(
            f"Aborted chunked upload {upload_id}: {upload['filename']}")
        return jsonify({
            'success': True,
            'data': {'message': 'Upload aborted'}
        })
    except Exception as e:
        logger.error(
            f"Failed to abort chunked upload: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


def _schedule_job_cleanup(job_id: str, job_type: str = 'bulk'):
    """Schedule removal of a completed/failed job from memory"""
    def _cleanup():
        time.sleep(JOB_CLEANUP_SECONDS)
        if job_type == 'bulk':
            with bulk_upload_jobs_lock:
                bulk_upload_jobs.pop(job_id, None)
                logger.info(f"Cleaned up bulk upload job {job_id}")

    t = threading.Thread(target=_cleanup, daemon=True)
    t.start()


@app.get('/api/tenders/<tender_id>/files/<path:file_path>')
@require_auth
def download_file(tender_id: str, file_path: str):
    """Download a file from a tender"""
    try:
        file_data = blob_service.download_file(tender_id, file_path)

        return app.response_class(
            file_data['content'],
            mimetype=file_data['content_type'],
            headers={
                'Content-Disposition': f'attachment; filename="{file_data["filename"]}"'
            }
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.put('/api/tenders/<tender_id>/files/<path:file_path>/category')
@require_auth
def update_file_category(tender_id: str, file_path: str):
    """Update file category"""
    try:
        data = request.json
        category = data.get('category')

        if not category:
            return jsonify({
                'success': False,
                'error': 'Category is required'
            }), 400

        metadata_store.update_file_metadata(
            tender_id=tender_id,
            file_path=file_path,
            metadata={'category': category}
        )

        return jsonify({
            'success': True,
            'message': 'File category updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.delete('/api/tenders/<tender_id>/files/<path:file_path>')
@require_auth
def delete_file(tender_id: str, file_path: str):
    """Delete a file from a tender"""
    try:
        logger.info(f"Deleting file {file_path} from tender {tender_id}")
        existing_metadata = metadata_store.get_file(tender_id, file_path)
        metadata_deleted = metadata_store.delete_file_metadata(
            tender_id, file_path)
        try:
            blob_service.delete_file(tender_id, file_path)
        except ResourceNotFoundError:
            logger.info(
                "Blob already absent for tender_id=%s file_path=%s during delete",
                tender_id,
                file_path,
            )
        except Exception:
            if metadata_deleted and existing_metadata:
                try:
                    metadata_store.restore_file_record(
                        tender_id, existing_metadata)
                    logger.warning(
                        "Blob delete failed, restored metadata for %s", file_path)
                except Exception:
                    logger.error(
                        "Failed to restore metadata after blob delete failure for %s",
                        file_path,
                        exc_info=True
                    )
            raise
        logger.info(
            f"Successfully deleted file {file_path} from tender {tender_id}")
        return jsonify({
            'success': True,
            'message': 'File deleted successfully'
        })
    except Exception as e:
        logger.error(
            f"Failed to delete file {file_path} from tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Batches API


@app.post('/api/tenders/<tender_id>/batches')
@require_auth
def create_batch(tender_id: str):
    """Create a new extraction batch"""
    try:
        data = request.json
        batch_name = data.get('batch_name')
        discipline = data.get('discipline')
        file_paths = data.get('file_paths', [])
        title_block_coords = data.get('title_block_coords')

        if not all([batch_name, discipline, file_paths, title_block_coords]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: batch_name, discipline, file_paths, title_block_coords'
            }), 400

        # Validate files exist
        all_files = metadata_store.list_files(tender_id)
        existing_paths = {f['path'] for f in all_files}
        for file_path in file_paths:
            if file_path not in existing_paths:
                return jsonify({
                    'success': False,
                    'error': f'File not found: {file_path}'
                }), 400

        user_info = extract_user_info(request.headers)
        logger.info(
            f"Creating batch '{batch_name}' for tender {tender_id} with {len(file_paths)} files")

        # Create batch (use email for UiPath user lookup, fallback to name if no email)
        batch = metadata_store.create_batch(
            tender_id=tender_id,
            batch_name=batch_name,
            discipline=discipline,
            file_paths=file_paths,
            title_block_coords=title_block_coords,
            submitted_by=user_info.get(
                'email') or user_info.get('name', 'Unknown'),
            job_id=None  # Will be set when UiPath job is submitted
        )

        # Update file categories and batch references
        updated_count = metadata_store.update_files_category(
            tender_id=tender_id,
            file_paths=file_paths,
            category=discipline,
            batch_id=batch['batch_id']
        )

        logger.info(
            f"Created batch {batch['batch_id']}, updated {updated_count} files")

        return jsonify({
            'success': True,
            'data': batch
        }), 201
    except Exception as e:
        logger.error(
            f"Failed to create batch for tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/tenders/<tender_id>/batches')
@require_auth
def list_batches(tender_id: str):
    """List all batches for a tender"""
    try:
        batches = metadata_store.list_batches(tender_id)
        return jsonify({
            'success': True,
            'data': batches
        })
    except Exception as e:
        logger.error(
            f"Failed to list batches for tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/tenders/<tender_id>/batches/progress-summary')
@require_auth
def get_batch_progress_summary(tender_id: str):
    """
    Get progress summary for multiple batches in one request.

    Query params:
    - batch_ids: comma-separated batch IDs

    Returns:
    {
        "success": true,
        "data": {
            "progress_by_batch": {
                "<batch_id>": {
                    "batch_id": "<batch_id>",
                    "total_files": 10,
                    "status_counts": {
                        "queued": 2,
                        "extracted": 1,
                        "failed": 0,
                        "exported": 7
                    }
                }
            },
            "errors_by_batch": {
                "<batch_id>": "Batch not found"
            }
        }
    }
    """
    started_at = time.perf_counter()
    try:
        batch_ids_param = request.args.get('batch_ids', '').strip()
        if not batch_ids_param:
            return jsonify({
                'success': False,
                'error': 'batch_ids query parameter is required'
            }), 400

        seen = set()
        batch_ids = []
        for raw_batch_id in batch_ids_param.split(','):
            batch_id = raw_batch_id.strip()
            if batch_id and batch_id not in seen:
                seen.add(batch_id)
                batch_ids.append(batch_id)

        if not batch_ids:
            return jsonify({
                'success': False,
                'error': 'batch_ids must contain at least one batch id'
            }), 400

        logger.info(
            f"Batch progress summary requested for tender {tender_id}: {len(batch_ids)} batches")

        progress_by_batch = {}
        errors_by_batch = {}

        for batch_id in batch_ids:
            try:
                batch = metadata_store.get_batch(tender_id, batch_id)
                if not batch:
                    errors_by_batch[batch_id] = 'Batch not found'
                    continue

                reference = batch.get('uipath_reference')
                if not reference:
                    file_count = int(batch.get('file_count', 0))
                    progress_by_batch[batch_id] = {
                        'batch_id': batch_id,
                        'total_files': file_count,
                        'status_counts': {
                            'queued': file_count,
                            'extracted': 0,
                            'failed': 0,
                            'exported': 0
                        }
                    }
                    continue

                progress = submission_store.get_batch_progress(reference)
                status_counts = progress.get('status_counts') or {}
                progress_by_batch[batch_id] = {
                    'batch_id': batch_id,
                    'total_files': int(progress.get('total_files', 0)),
                    'status_counts': {
                        'queued': int(status_counts.get('queued', 0)),
                        'extracted': int(status_counts.get('extracted', 0)),
                        'failed': int(status_counts.get('failed', 0)),
                        'exported': int(status_counts.get('exported', 0))
                    }
                }
            except Exception as batch_error:
                logger.error(
                    f"Failed to get progress summary for batch {batch_id} in tender {tender_id}: {str(batch_error)}",
                    exc_info=True
                )
                errors_by_batch[batch_id] = str(batch_error)

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            f"Batch progress summary complete for tender {tender_id}: "
            f"requested={len(batch_ids)} succeeded={len(progress_by_batch)} "
            f"failed={len(errors_by_batch)} elapsed_ms={elapsed_ms}"
        )

        data = {
            'progress_by_batch': progress_by_batch
        }
        if errors_by_batch:
            data['errors_by_batch'] = errors_by_batch

        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.error(
            f"Failed to get batch progress summary for tender {tender_id} after {elapsed_ms}ms: {str(e)}",
            exc_info=True
        )
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/tenders/<tender_id>/batches/<batch_id>')
@require_auth
def get_batch(tender_id: str, batch_id: str):
    """Get batch details and files"""
    try:
        batch = metadata_store.get_batch(tender_id, batch_id)
        if not batch:
            return jsonify({
                'success': False,
                'error': 'Batch not found'
            }), 404

        # Get files in batch
        files = metadata_store.get_batch_files(tender_id, batch_id)

        return jsonify({
            'success': True,
            'data': {
                'batch': batch,
                'files': files
            }
        })
    except Exception as e:
        logger.error(
            f"Failed to get batch {batch_id} for tender {tender_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.patch('/api/tenders/<tender_id>/batches/<batch_id>')
@require_auth
def update_batch_status(tender_id: str, batch_id: str):
    """Update batch status"""
    try:
        data = request.json
        status = data.get('status')

        if not status:
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400

        batch = metadata_store.update_batch_status(tender_id, batch_id, status)

        if not batch:
            return jsonify({
                'success': False,
                'error': 'Batch not found'
            }), 404

        return jsonify({
            'success': True,
            'data': batch
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(
            f"Failed to update batch {batch_id} status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/tenders/<tender_id>/batches/<batch_id>/retry')
@require_auth
def retry_batch(tender_id: str, batch_id: str):
    """Manually retry a failed or stuck batch submission"""
    try:
        # Verify batch exists
        batch = metadata_store.get_batch(tender_id, batch_id)
        if not batch:
            return jsonify({
                'success': False,
                'error': 'Batch not found'
            }), 404

        # Check if batch is in a retriable state
        status = batch.get('status', '')
        if status in ['running', 'completed']:
            return jsonify({
                'success': False,
                'error': f'Batch cannot be retried. Current status: {status}.'
            }), 400

        if status == 'submitting':
            lock_until = _parse_iso_datetime(
                batch.get('submission_locked_until'))
            if lock_until and lock_until > datetime.utcnow():
                return jsonify({
                    'success': False,
                    'error': 'Batch is currently being submitted. Please wait and refresh.'
                }), 409

        if status == 'pending':
            submitted_at = _parse_iso_datetime(batch.get('submitted_at'))
            if submitted_at:
                age = datetime.utcnow() - submitted_at
                if age <= timedelta(minutes=BATCH_PENDING_RETRY_MIN_AGE_MINUTES):
                    return jsonify({
                        'success': False,
                        'error': f'Batch is still within the initial submission window ({BATCH_PENDING_RETRY_MIN_AGE_MINUTES} minutes). Please wait before retrying.'
                    }), 409

        # Get tender info for submission
        tender = metadata_store.get_tender(tender_id)
        if not tender:
            return jsonify({
                'success': False,
                'error': 'Tender not found'
            }), 404

        tender_name = tender.get('name', tender_id)

        # Get batch details
        file_paths = batch.get('file_paths', [])
        category = batch.get('discipline') or batch.get('category', '')
        title_block_coords = batch.get('title_block_coords', {})
        sharepoint_folder_path = batch.get('sharepoint_folder_path', '')
        output_folder_path = batch.get('output_folder_path', '')
        folder_list = batch.get('folder_list', [])
        mfiles_document_class = batch.get('mfiles_document_class', '')
        mfiles_properties = batch.get('mfiles_properties', [])

        # Get email from current user making the retry request (not from old batch metadata)
        # This ensures we use a valid email even for legacy batches with display names
        user_info = extract_user_info(request.headers)
        user_email = user_info.get('email') or user_info.get('name', 'system')

        if not file_paths:
            return jsonify({
                'success': False,
                'error': 'Batch has no files to process'
            }), 400

        _validate_pdf_file_paths(tender_id, file_paths)

        owner = _build_submission_owner('manual-retry')
        claimed = metadata_store.claim_batch_for_submission(
            tender_id=tender_id,
            batch_id=batch_id,
            owner=owner,
            allowed_statuses=['failed', 'pending', 'submitting'],
            lock_seconds=BATCH_SUBMISSION_LOCK_SECONDS,
            attempt_source='manual-retry',
            submitted_by=user_email
        )
        if not claimed:
            return jsonify({
                'success': False,
                'error': 'Batch retry was not started because another submission process already claimed this batch.'
            }), 409

        logger.info(
            f"Manual retry initiated for batch {batch_id} in tender {tender_id} by {user_email}")

        _process_uipath_submission_async(
            tender_id,
            tender_name,
            batch_id,
            file_paths,
            category,
            title_block_coords,
            user_email,
            sharepoint_folder_path,
            output_folder_path,
            folder_list,
            mfiles_document_class,
            mfiles_properties,
            claim_before_submit=False,
            attempt_source='manual-retry',
            claim_owner=owner,
            raise_on_error=True,
            reset_failed_files=(status == 'failed'),
        )

        return jsonify({
            'success': True,
            'message': 'Batch retry initiated and queued for extraction.'
        }), 202

    except Exception as e:
        logger.error(
            f"Failed to retry batch {batch_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.delete('/api/tenders/<tender_id>/batches/<batch_id>')
@require_auth
def delete_batch(tender_id: str, batch_id: str):
    """Delete a batch (admin only - files remain categorized)"""
    try:
        success = metadata_store.delete_batch(tender_id, batch_id)

        if not success:
            return jsonify({
                'success': False,
                'error': 'Batch not found or could not be deleted'
            }), 404

        return jsonify({
            'success': True,
            'message': 'Batch deleted successfully. Files have been uncategorized.'
        })
    except Exception as e:
        logger.error(
            f"Failed to delete batch {batch_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/tenders/<tender_id>/batches/<batch_id>/progress')
@require_auth
def get_batch_progress(tender_id: str, batch_id: str):
    """
    Get file-level progress for a batch by querying internal extraction state

    Returns aggregated status counts and per-file details including:
    - Total file count
    - Status breakdown (queued, extracted, failed, exported)
    - Per-file metadata (status, drawing_number, etc.)
    """
    try:
        batch = metadata_store.get_batch(tender_id, batch_id)
        if not batch:
            return jsonify({
                'success': False,
                'error': 'Batch not found'
            }), 404

        reference = batch.get('uipath_reference')

        if not reference:
            file_count = int(batch.get('file_count', 0))
            progress = {
                'total_files': file_count,
                'status_counts': {
                    'queued': file_count,
                    'extracted': 0,
                    'failed': 0,
                    'exported': 0
                },
                'files': []
            }
            progress['metrics'] = build_batch_metrics(batch, progress)
            logger.info(
                f"Batch {batch_id} not yet queued for extraction. Returning default progress.")
            return jsonify({
                'success': True,
                'data': {
                    'batch_id': batch_id,
                    **progress,
                }
            })

        logger.info(
            f"Querying internal extraction progress for batch {batch_id} with reference {reference}")
        progress = submission_store.get_batch_progress(reference)

        # Add batch_id to response
        progress['batch_id'] = batch_id

        return jsonify({
            'success': True,
            'data': progress
        })

    except Exception as e:
        logger.error(
            f"Failed to get batch progress for {batch_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/webhooks/batch-complete')
def batch_complete_webhook():
    """
    Webhook endpoint to notify when a batch is complete

    Expected payload:
    {
        "reference": "batch-reference-string",
        "status": "completed" | "failed",
        "completed_at": "ISO-8601 datetime"
    }
    """
    try:
        if not WEBHOOK_BATCH_COMPLETE_KEY:
            logger.error(
                "Webhook %s is not configured; set WEBHOOK_BATCH_COMPLETE_KEY to enable this endpoint safely",
                WEBHOOK_BATCH_COMPLETE_KEY_HEADER
            )
            return jsonify({
                'success': False,
                'error': 'Webhook authentication not configured'
            }), 503

        provided_key = request.headers.get(
            WEBHOOK_BATCH_COMPLETE_KEY_HEADER, '')
        if not provided_key or not hmac.compare_digest(provided_key, WEBHOOK_BATCH_COMPLETE_KEY):
            logger.warning(
                "Rejected batch-complete webhook due to invalid key header")
            return jsonify({
                'success': False,
                'error': 'Invalid webhook key'
            }), 401

        data = request.json

        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400

        reference = data.get('reference')
        webhook_status = data.get('status')
        completed_at = data.get('completed_at')

        if not reference:
            return jsonify({
                'success': False,
                'error': 'reference is required'
            }), 400

        if not webhook_status or webhook_status not in ['completed', 'failed']:
            return jsonify({
                'success': False,
                'error': 'status must be "completed" or "failed"'
            }), 400

        logger.info(
            f"Webhook received: Batch {reference} status={webhook_status}")

        lookup = metadata_store.get_batch_by_reference(reference)
        if not lookup:
            logger.warning(
                f"Webhook received for unknown reference: {reference}")
            return jsonify({
                'success': False,
                'error': 'Batch not found for reference'
            }), 404

        tender_id = lookup.get('tender_id')
        batch = lookup.get('batch', {})
        batch_id = batch.get('batch_id')

        logger.info(
            f"Found batch {batch_id} in tender {tender_id} for reference {reference}")
        if completed_at and not _parse_iso_datetime(completed_at):
            return jsonify({
                'success': False,
                'error': 'completed_at must be an ISO-8601 datetime'
            }), 400

        updates = {
            'status': webhook_status,
            'submission_owner': '',
            'submission_locked_until': '',
        }
        if completed_at:
            updates['completed_at'] = completed_at

        metadata_store.update_batch(tender_id, batch_id, updates)
        logger.info(
            f"Updated batch {batch_id} status to {webhook_status}")

        return jsonify({
            'success': True,
            'message': 'Batch status updated'
        }), 200

    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/admin/purge-old-batches')
@require_auth
def purge_old_batches():
    """
    Admin endpoint to mark old stuck batches as failed.
    Useful for cleaning up legacy batches that don't have submission tracking.
    """
    try:
        # Optional query parameter for age threshold (default 24 hours)
        age_hours = request.args.get('age_hours', 24, type=int)

        logger.info(
            f"[Admin] Starting manual purge of batches older than {age_hours} hours")

        tenders = metadata_store.list_tenders()
        purged_count = 0
        checked_count = 0
        errors = []

        for tender in tenders:
            tender_id = tender['id']

            try:
                batches = metadata_store.list_batches(tender_id)

                for batch in batches:
                    # Only process pending batches
                    if batch.get('status') == 'pending':
                        checked_count += 1

                        try:
                            submitted_at = datetime.fromisoformat(
                                batch['submitted_at'])
                            age = datetime.utcnow() - submitted_at
                            submission_attempts = batch.get(
                                'submission_attempts', [])

                            # Mark as failed if old and no tracking
                            if age > timedelta(hours=age_hours) and len(submission_attempts) == 0:
                                batch_id = batch['batch_id']
                                logger.info(
                                    f"[Admin] Purging batch {batch_id} in tender {tender_id} "
                                    f"(age: {int(age.total_seconds()//3600)} hours)"
                                )

                                metadata_store.update_batch(tender_id, batch_id, {
                                    'status': 'failed',
                                    'last_error': f'Manually purged: Legacy batch older than {age_hours} hours with no submission tracking',
                                    'completed_at': '',
                                })

                                purged_count += 1

                        except (ValueError, KeyError) as parse_error:
                            error_msg = f"Error parsing batch {batch.get('batch_id')} in tender {tender_id}: {parse_error}"
                            logger.error(f"[Admin] {error_msg}")
                            errors.append(error_msg)

            except Exception as tender_error:
                error_msg = f"Error processing tender {tender_id}: {tender_error}"
                logger.error(f"[Admin] {error_msg}")
                errors.append(error_msg)

        logger.info(
            f"[Admin] Purge complete: Checked {checked_count} pending batches, purged {purged_count}")

        return jsonify({
            'success': True,
            'message': f'Purge complete',
            'data': {
                'checked': checked_count,
                'purged': purged_count,
                'age_threshold_hours': age_hours,
                'errors': errors if errors else None
            }
        })

    except Exception as e:
        logger.error(
            f"[Admin] Purge operation failed: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Extraction API


@app.post('/api/uipath/extract')
@require_auth
def queue_extraction():
    """Queue drawing metadata extraction via the internal worker pipeline."""
    try:
        data = request.get_json(silent=True) or {}
        tender_id = str(data.get('tender_id') or '').strip()
        tender_name = data.get('tender_name')
        file_paths = data.get('file_paths', [])

        # Support both 'discipline' (legacy) and 'destination' (new)
        destination = str(data.get('destination') or '').strip()
        # Fallback for backward compatibility
        discipline = str(data.get('discipline') or '').strip()
        mfiles_document_class = str(
            data.get('mfiles_document_class') or '').strip()
        raw_mfiles_properties = data.get('mfiles_properties')

        # {x, y, width, height} in pixels
        title_block_coords = data.get('title_block_coords')

        # Get SharePoint paths from request
        sharepoint_folder_path = data.get('sharepoint_folder_path')
        output_folder_path = data.get('output_folder_path')

        # Get folder list from request (list of folder names)
        folder_list = data.get('folder_list', [])

        if not tender_id or not isinstance(file_paths, list) or not file_paths or not title_block_coords:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: tender_id, file_paths, title_block_coords'
            }), 400

        tender = metadata_store.get_tender(tender_id)
        if not tender:
            return jsonify({
                'success': False,
                'error': 'Tender not found'
            }), 404

        tender_type = str(tender.get('tender_type')
                          or 'sharepoint').strip().lower()
        is_mfiles_tender = tender_type == 'mfiles'
        category = destination or discipline
        validated_mfiles_properties: List[Dict[str, Any]] = []

        if is_mfiles_tender:
            if not mfiles_document_class:
                return jsonify({
                    'success': False,
                    'error': 'mfiles_document_class is required for mfiles tenders'
                }), 400

            if raw_mfiles_properties is None:
                return jsonify({
                    'success': False,
                    'error': 'mfiles_properties is required for mfiles tenders'
                }), 400

            validated_mfiles_properties = _validate_mfiles_extraction_properties(
                tender=tender,
                mfiles_document_class=mfiles_document_class,
                raw_properties=raw_mfiles_properties,
            )
            category = mfiles_document_class
        elif not category:
            return jsonify({
                'success': False,
                'error': 'Missing required field for sharepoint tender: destination (or discipline)'
            }), 400

        _validate_pdf_file_paths(tender_id, file_paths)

        batch_name = data.get(
            'batch_name', f"{category} Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")

        user_info = extract_user_info(request.headers)
        user_email = user_info.get('email') or user_info.get('name', 'Unknown')

        logger.info(
            f"Creating batch and queuing extraction for tender {tender_id}")

        # Create batch first (with both discipline and destination for compatibility)
        # Use email for UiPath user lookup, fallback to name if no email
        batch = metadata_store.create_batch(
            tender_id=tender_id,
            batch_name=batch_name,
            discipline=category,  # Store in discipline field for backward compatibility
            file_paths=file_paths,
            title_block_coords=title_block_coords,
            submitted_by=user_email,
            job_id=None,  # Will be updated after UiPath submission
            sharepoint_folder_path=sharepoint_folder_path,
            output_folder_path=output_folder_path,
            folder_list=folder_list
        )

        if is_mfiles_tender:
            updated_batch = metadata_store.update_batch(
                tender_id=tender_id,
                batch_id=batch['batch_id'],
                updates={
                    'mfiles_document_class': mfiles_document_class,
                    'mfiles_properties': validated_mfiles_properties,
                },
            )
            if updated_batch:
                batch = updated_batch
            else:
                logger.warning(
                    "Failed to persist M-Files extraction metadata on batch %s",
                    batch.get('batch_id')
                )

        # Update file categories and batch references
        metadata_store.update_files_category(
            tender_id=tender_id,
            file_paths=file_paths,
            category=category,
            batch_id=batch['batch_id']
        )

        owner = _build_submission_owner('initial-submit')
        claimed = metadata_store.claim_batch_for_submission(
            tender_id=tender_id,
            batch_id=batch['batch_id'],
            owner=owner,
            allowed_statuses=['pending'],
            lock_seconds=BATCH_SUBMISSION_LOCK_SECONDS,
            attempt_source='initial-submit',
            submitted_by=user_email
        )
        if not claimed:
            return jsonify({
                'success': False,
                'error': 'Batch was created but could not be claimed for submission. Please retry.'
            }), 409

        _process_uipath_submission_async(
            tender_id,
            tender_name,
            batch['batch_id'],
            file_paths,
            category,
            title_block_coords,
            user_email,
            sharepoint_folder_path,
            output_folder_path,
            folder_list,
            mfiles_document_class if is_mfiles_tender else '',
            validated_mfiles_properties if is_mfiles_tender else [],
            claim_before_submit=False,
            attempt_source='initial-submit',
            claim_owner=owner,
            raise_on_error=True,
        )
        updated_batch = metadata_store.get_batch(tender_id, batch['batch_id']) or claimed

        logger.info(
            "Successfully created batch %s and queued it for internal extraction",
            batch['batch_id']
        )

        return jsonify({
            'success': True,
            'data': {
                'batch_id': batch['batch_id'],
                'status': updated_batch.get('status', 'running'),
                'message': f'Batch created successfully. Queued {len(file_paths)} files for extraction.',
                'batch': updated_batch
            }
        }), 202

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except MFilesConfigurationError as e:
        logger.error(
            "M-Files configuration error during queue extraction: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 503
    except MFilesClientError as e:
        logger.error("M-Files request failed during queue extraction: %s", e)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 502
    except Exception as e:
        logger.error(f"Failed to queue extraction: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/uipath/jobs/<job_id>')
@require_auth
def get_job_status(job_id: str):
    """Legacy route retained for compatibility; internal extraction is batch-scoped."""
    return jsonify({
        'success': False,
        'error': 'Per-job status is not available for internal extraction. Use batch progress endpoints instead.'
    }), 410

# SharePoint API (placeholder for future integration)


@app.post('/api/sharepoint/validate')
@require_auth
def validate_sharepoint_path():
    """Validate SharePoint folder path"""
    try:
        data = request.json
        path = data.get('path')

        # TODO: Implement SharePoint validation
        return jsonify({
            'success': True,
            'valid': True,
            'message': 'SharePoint validation not yet implemented'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/sharepoint/list-folders')
@require_auth
def list_sharepoint_folders():
    """List subfolders in a SharePoint folder using Graph API"""
    try:
        data = request.json
        access_token = data.get('access_token')
        drive_id = data.get('drive_id')  # output_library_id
        folder_path = data.get('folder_path')  # output_folder_path

        if not access_token or not drive_id or not folder_path:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: access_token, drive_id, folder_path'
            }), 400

        # Handle two possible path formats:
        # 1. Full Graph API format: "/drives/{drive-id}/root:/path"
        # 2. Simple path format: "/path"

        if folder_path.startswith('/drives/'):
            # Extract the actual path from the full Graph API format
            # Format: /drives/{drive-id}/root:/actual/path
            logger.info(
                f"Folder path is in full Graph API format: {folder_path}")

            # Find the "/root:" part and extract what comes after it
            root_index = folder_path.find('/root:')
            if root_index != -1:
                actual_path = folder_path[root_index + 6:]  # Skip "/root:"
                logger.info(f"Extracted actual path: {actual_path}")

                # Construct Graph API URL using the extracted path
                graph_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:{actual_path}:/children"
            else:
                # Fallback: use the full path as-is (shouldn't happen but handle it)
                logger.warning(f"Could not find '/root:' in path, using as-is")
                graph_url = f"https://graph.microsoft.com/v1.0{folder_path}:/children"
        else:
            # Simple path format - construct the full URL
            logger.info(f"Folder path is in simple format: {folder_path}")
            graph_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:{folder_path}:/children"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }

        logger.info(f"Fetching folders from: {graph_url}")

        response = requests.get(graph_url, headers=headers)

        if not response.ok:
            error_text = response.text
            logger.error(f"Graph API error: {error_text}")
            return jsonify({
                'success': False,
                'error': f'Graph API request failed: {response.status_code} - {error_text}'
            }), response.status_code

        result = response.json()

        # Filter to only include folders (items with 'folder' property)
        folders = []
        for item in result.get('value', []):
            if 'folder' in item:
                folders.append({
                    'name': item.get('name'),
                    'id': item.get('id'),
                    # Just return the folder name, not full path
                    'path': item.get('name')
                })

        logger.info(f"Found {len(folders)} folders")

        return jsonify({
            'success': True,
            'data': folders
        })

    except Exception as e:
        logger.error(
            f"Failed to list SharePoint folders: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.post('/api/sharepoint/import-files')
@require_auth
def import_sharepoint_files():
    """Import files from SharePoint to blob storage (backend-driven)"""
    try:
        data = request.json
        tender_id = data.get('tender_id')
        access_token = data.get('access_token')
        items = data.get('items', [])
        category = data.get('category', 'sharepoint-import')

        if not tender_id or not access_token or not items:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: tender_id, access_token, items'
            }), 400

        # Verify tender exists
        tender = metadata_store.get_tender(tender_id)
        if not tender:
            return jsonify({
                'success': False,
                'error': 'Tender not found'
            }), 404

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Initialize job tracking
        with import_jobs_lock:
            sharepoint_import_jobs[job_id] = {
                'job_id': job_id,
                'tender_id': tender_id,
                'status': 'running',
                'progress': 0,
                'total': len(items),
                'current_file': '',
                'success_count': 0,
                'error_count': 0,
                'errors': [],
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

        # Start background import thread
        import_thread = threading.Thread(
            target=_process_sharepoint_import,
            args=(job_id, tender_id, access_token, items, category)
        )
        import_thread.daemon = True
        import_thread.start()

        logger.info(
            f"Started SharePoint import job {job_id} for tender {tender_id} with {len(items)} items")

        return jsonify({
            'success': True,
            'data': {
                'job_id': job_id,
                'status': 'running',
                'total': len(items)
            }
        })

    except Exception as e:
        logger.error(
            f"Failed to start SharePoint import: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.get('/api/sharepoint/import-jobs/<job_id>')
@require_auth
def get_sharepoint_import_job_status(job_id: str):
    """Get status of a SharePoint import job"""
    try:
        with import_jobs_lock:
            job = sharepoint_import_jobs.get(job_id)

        if not job:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404

        return jsonify({
            'success': True,
            'data': job
        })

    except Exception as e:
        logger.error(
            f"Failed to get import job status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _resolve_mfiles_import_filename(download_info: Dict[str, Any], document: Dict[str, str], display_id: str) -> str:
    candidates = [
        download_info.get('filename'),
        document.get('filename'),
        document.get('title'),
    ]
    chosen = ''
    for candidate in candidates:
        safe_name = _safe_import_filename(str(candidate or ''))
        if safe_name:
            chosen = safe_name
            break

    content_type = str(download_info.get('content_type')
                       or '').split(';')[0].strip().lower()
    if chosen and '.' not in chosen and content_type:
        guessed_extension = mimetypes.guess_extension(content_type)
        if guessed_extension:
            chosen = f"{chosen}{guessed_extension}"

    if not chosen:
        guessed_extension = mimetypes.guess_extension(
            content_type) if content_type else None
        chosen = f"mfiles-{display_id}{guessed_extension or '.bin'}"

    return chosen


def _ensure_unique_mfiles_filename(
    tender_id: str,
    category: str,
    filename: str,
    display_id: str,
    used_paths: set,
) -> str:
    """Ensure imported M-Files filenames do not overwrite existing files."""
    cleaned_display_id = re.sub(
        r'[^A-Za-z0-9._-]+', '-', str(display_id or '').strip()) or 'doc'
    base_name, extension = os.path.splitext(filename)
    extension = extension or ''

    def candidate_path(name: str) -> str:
        return f"{tender_id}/{category}/{name}"

    first_path = candidate_path(filename)
    if first_path not in used_paths:
        used_paths.add(first_path)
        return filename

    second_name = f"{base_name}-{cleaned_display_id}{extension}"
    second_path = candidate_path(second_name)
    if second_path not in used_paths:
        used_paths.add(second_path)
        return second_name

    counter = 2
    while True:
        numbered_name = f"{base_name}-{cleaned_display_id}-{counter}{extension}"
        numbered_path = candidate_path(numbered_name)
        if numbered_path not in used_paths:
            used_paths.add(numbered_path)
            return numbered_name
        counter += 1


def _process_mfiles_import(job_id: str, tender_id: str, documents: list, category: str, imported_by: str):
    """Background thread function to process M-Files document imports."""
    try:
        used_paths = set()
        try:
            existing_files = metadata_store.list_files(
                tender_id, exclude_batched=False)
            used_paths = {
                str(file.get('path') or '').strip()
                for file in existing_files
                if str(file.get('path') or '').strip()
            }
        except Exception:
            logger.warning(
                "Failed to pre-load existing file paths for tender %s. Falling back to per-job path tracking only.",
                tender_id,
                exc_info=True
            )

        for i, document in enumerate(documents):
            display_id = str(document.get('display_id') or '').strip()
            label = display_id or str(document.get('title') or 'unknown')

            with import_jobs_lock:
                if job_id in mfiles_import_jobs:
                    mfiles_import_jobs[job_id]['current_file'] = label
                    mfiles_import_jobs[job_id]['progress'] = i
                    mfiles_import_jobs[job_id]['updated_at'] = datetime.utcnow(
                    ).isoformat()

            try:
                if not display_id:
                    raise ValueError('Document display_id is missing')

                download_info = mfiles_client.download_document_contents(
                    display_id)
                content = download_info.get('content')
                if not isinstance(content, (bytes, bytearray)):
                    raise ValueError(
                        'M-Files download did not return file content')
                if len(content) == 0:
                    raise ValueError(
                        'M-Files download returned empty file content')

                filename = _resolve_mfiles_import_filename(
                    download_info, document, display_id)
                filename = _ensure_unique_mfiles_filename(
                    tender_id=tender_id,
                    category=category,
                    filename=filename,
                    display_id=display_id,
                    used_paths=used_paths,
                )
                file_stream = BytesIO(content)
                file_storage = FileStorage(
                    stream=file_stream,
                    filename=filename,
                    content_type=str(download_info.get(
                        'content_type') or 'application/octet-stream')
                )

                file_metadata = blob_service.upload_file(
                    tender_id=tender_id,
                    file=file_storage,
                    category=category,
                    uploaded_by=imported_by,
                    source='mfiles'
                )

                try:
                    metadata_store.upsert_file_record(tender_id, file_metadata)
                except Exception:
                    logger.error(
                        "M-Files import metadata write failed for %s. Deleting blob for compensation.",
                        file_metadata.get('path'),
                        exc_info=True
                    )
                    try:
                        blob_service.delete_file(
                            tender_id, file_metadata.get('path'))
                    except Exception:
                        logger.error(
                            "M-Files import compensation failed for %s",
                            file_metadata.get('path'),
                            exc_info=True
                        )
                    raise

                with import_jobs_lock:
                    if job_id in mfiles_import_jobs:
                        mfiles_import_jobs[job_id]['success_count'] += 1

                logger.info(
                    "Successfully imported M-Files document %s as %s (job %s)",
                    display_id,
                    filename,
                    job_id
                )

            except Exception as item_error:
                error_msg = f"{label}: {str(item_error)}"
                logger.error(
                    "Failed to import M-Files document %s in job %s: %s",
                    label,
                    job_id,
                    item_error
                )
                with import_jobs_lock:
                    if job_id in mfiles_import_jobs:
                        mfiles_import_jobs[job_id]['error_count'] += 1
                        mfiles_import_jobs[job_id]['errors'].append(error_msg)

        success_count = 0
        error_count = 0
        with import_jobs_lock:
            if job_id in mfiles_import_jobs:
                job = mfiles_import_jobs[job_id]
                job['status'] = 'completed' if job['error_count'] == 0 else 'completed_with_errors'
                job['progress'] = len(documents)
                job['current_file'] = ''
                job['updated_at'] = datetime.utcnow().isoformat()
                job['completed_at'] = datetime.utcnow().isoformat()
                success_count = job['success_count']
                error_count = job['error_count']

        logger.info(
            "M-Files import job %s completed: %s succeeded, %s failed",
            job_id,
            success_count,
            error_count
        )

        cleanup_thread = threading.Thread(
            target=_cleanup_import_job,
            args=(job_id, 'mfiles'),
            daemon=True
        )
        cleanup_thread.start()

    except Exception as e:
        logger.error("Fatal error in M-Files import job %s: %s",
                     job_id, e, exc_info=True)
        with import_jobs_lock:
            if job_id in mfiles_import_jobs:
                mfiles_import_jobs[job_id]['status'] = 'failed'
                mfiles_import_jobs[job_id]['errors'].append(
                    f"Fatal error: {str(e)}")
                mfiles_import_jobs[job_id]['updated_at'] = datetime.utcnow(
                ).isoformat()


def _process_sharepoint_import(job_id: str, tender_id: str, access_token: str, items: list, category: str):
    """Background thread function to process SharePoint file imports"""
    try:
        for i, item in enumerate(items):
            # Update current file
            file_name = item.get('name', 'unknown')
            relative_path = item.get('relativePath', '')

            with import_jobs_lock:
                if job_id in sharepoint_import_jobs:
                    sharepoint_import_jobs[job_id]['current_file'] = file_name
                    sharepoint_import_jobs[job_id]['progress'] = i
                    sharepoint_import_jobs[job_id]['updated_at'] = datetime.utcnow(
                    ).isoformat()

            try:
                # Check if it's a folder (folders don't have downloadUrl)
                download_url = item.get('downloadUrl')
                if not download_url:
                    logger.info(
                        f"Skipping folder or item without download URL: {file_name}")
                    continue

                # Download file from SharePoint
                logger.info(
                    f"Downloading {file_name} from SharePoint (job {job_id})...")
                response = requests.get(
                    download_url,
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=300  # 5 minute timeout for large files
                )

                if not response.ok:
                    raise Exception(
                        f"Failed to download: {response.status_code} {response.reason}")

                # Determine category (preserve folder structure if relativePath provided)
                upload_category = category
                if relative_path:
                    # Use the first folder in relative path as category
                    upload_category = relative_path.strip('/').split('/')[0]

                # Upload to blob storage
                logger.info(
                    f"Uploading {file_name} to blob storage...")

                # Create a FileStorage-like object from the downloaded content
                file_stream = BytesIO(response.content)
                file_storage = FileStorage(
                    stream=file_stream,
                    filename=file_name,
                    content_type=item.get(
                        'mimeType', 'application/octet-stream')
                )

                file_metadata = blob_service.upload_file(
                    tender_id=tender_id,
                    file=file_storage,
                    category=upload_category,
                    uploaded_by='SharePoint Import',
                    source='sharepoint'
                )
                try:
                    metadata_store.upsert_file_record(tender_id, file_metadata)
                except Exception:
                    logger.error(
                        "SharePoint import metadata write failed for %s. Deleting blob for compensation.",
                        file_metadata.get('path'),
                        exc_info=True
                    )
                    try:
                        blob_service.delete_file(
                            tender_id, file_metadata.get('path'))
                    except Exception:
                        logger.error(
                            "SharePoint import compensation failed for %s",
                            file_metadata.get('path'),
                            exc_info=True
                        )
                    raise

                # Increment success count
                with import_jobs_lock:
                    if job_id in sharepoint_import_jobs:
                        sharepoint_import_jobs[job_id]['success_count'] += 1

                logger.info(
                    f"Successfully imported {file_name} (job {job_id})")

            except Exception as item_error:
                error_msg = f"{file_name}: {str(item_error)}"
                logger.error(
                    f"Failed to import {file_name} in job {job_id}: {str(item_error)}")

                with import_jobs_lock:
                    if job_id in sharepoint_import_jobs:
                        sharepoint_import_jobs[job_id]['error_count'] += 1
                        sharepoint_import_jobs[job_id]['errors'].append(
                            error_msg)

        # Mark job as complete
        with import_jobs_lock:
            if job_id in sharepoint_import_jobs:
                job = sharepoint_import_jobs[job_id]
                job['status'] = 'completed' if job['error_count'] == 0 else 'completed_with_errors'
                job['progress'] = len(items)
                job['current_file'] = ''
                job['updated_at'] = datetime.utcnow().isoformat()
                job['completed_at'] = datetime.utcnow().isoformat()

        logger.info(
            f"SharePoint import job {job_id} completed: {sharepoint_import_jobs[job_id]['success_count']} succeeded, {sharepoint_import_jobs[job_id]['error_count']} failed")

        # Schedule cleanup
        cleanup_thread = threading.Thread(
            target=_cleanup_import_job,
            args=(job_id, 'sharepoint')
        )
        cleanup_thread.daemon = True
        cleanup_thread.start()

    except Exception as e:
        logger.error(
            f"Fatal error in SharePoint import job {job_id}: {str(e)}", exc_info=True)

        with import_jobs_lock:
            if job_id in sharepoint_import_jobs:
                sharepoint_import_jobs[job_id]['status'] = 'failed'
                sharepoint_import_jobs[job_id]['errors'].append(
                    f"Fatal error: {str(e)}")
                sharepoint_import_jobs[job_id]['updated_at'] = datetime.utcnow(
                ).isoformat()


def _cleanup_import_job(job_id: str, source: str = 'sharepoint'):
    """Remove completed import jobs from memory after cleanup period."""
    time.sleep(JOB_CLEANUP_SECONDS)
    with import_jobs_lock:
        if source == 'mfiles' and job_id in mfiles_import_jobs:
            del mfiles_import_jobs[job_id]
            logger.info(f"Cleaned up M-Files import job {job_id}")
        elif job_id in sharepoint_import_jobs:
            del sharepoint_import_jobs[job_id]
            logger.info(f"Cleaned up SharePoint import job {job_id}")


# Health check


@app.get('/api/health')
def health_check():
    """Health check endpoint (unauthenticated for monitoring)"""
    metadata_mode = os.getenv('METADATA_STORE_MODE', 'blob')
    metadata_health = metadata_store.check_health()
    status = 'healthy' if metadata_health.get('ok') else 'degraded'
    return jsonify({
        'status': status,
        'timestamp': datetime.utcnow().isoformat(),
        'metadata_mode': metadata_mode,
        'metadata': metadata_health
    })


@app.get('/api/config')
@require_auth
def get_config():
    """Get frontend configuration from environment variables"""
    is_mfiles_defaults_admin = _request_is_mfiles_queue_defaults_admin()
    return jsonify({
        'success': True,
        'data': {
            'entraClientId': os.getenv('ENTRA_CLIENT_ID', ''),
            'entraTenantId': os.getenv('ENTRA_TENANT_ID', ''),
            'sharepointBaseUrl': os.getenv('SHAREPOINT_BASE_URL', ''),
            'isMfilesDefaultsAdmin': is_mfiles_defaults_admin,
        }
    })


@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found'
        }), 404
    # For non-API routes, serve React app (client-side routing)
    return app.send_static_file('index.html')


@app.errorhandler(500)
def handle_500(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', debug=True, port=8080)
