"""
Authentication utilities for extracting user information from Container Apps headers
"""
import base64
import json
import logging
from functools import wraps
from typing import Dict, List, Optional, Set

from flask import request, jsonify

logger = logging.getLogger(__name__)

GROUP_CLAIM_TYPES = {
    'groups',
    'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups',
}


def require_auth(f):
    """
    Decorator to require authentication on Flask routes.
    Checks for X-MS-CLIENT-PRINCIPAL header from Container Apps built-in auth.
    Returns 401 if not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "X-MS-CLIENT-PRINCIPAL" not in request.headers:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def _decode_client_principal(headers) -> Optional[Dict]:
    if "X-MS-CLIENT-PRINCIPAL" not in headers:
        return None

    try:
        return json.loads(base64.b64decode(headers.get("X-MS-CLIENT-PRINCIPAL")))
    except Exception as exc:
        print(f"Error decoding X-MS-CLIENT-PRINCIPAL: {exc}")
        return None


def _get_claims_list(token: Optional[Dict]) -> List[Dict]:
    if not isinstance(token, dict):
        return []
    claims = token.get('claims', [])
    return claims if isinstance(claims, list) else []


def extract_user_info(headers, default_username="Unknown") -> Dict[str, str]:
    """
    Extract user information from the X-MS-CLIENT-PRINCIPAL header
    provided by Azure Container Apps built-in authentication.

    Args:
        headers: Request headers
        default_username: Default username if header is not present

    Returns:
        Dictionary containing user information (name, email, etc.)
    """
    token = _decode_client_principal(headers)
    if not token:
        return {
            'name': default_username,
            'email': None,
            'id': None
        }

    try:
        claims = {}
        for claim in _get_claims_list(token):
            claim_type = claim.get("typ")
            if claim_type not in claims:
                claims[claim_type] = claim.get("val")

        return {
            'name': claims.get("name", default_username),
            'email': claims.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"),
            'id': claims.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier"),
            'auth_type': token.get("auth_typ"),
            'claims': claims
        }
    except Exception as e:
        print(f"Error extracting user info: {e}")
        return {
            'name': default_username,
            'email': None,
            'id': None
        }


def extract_group_ids(headers) -> Set[str]:
    """Extract Entra group object IDs from the client principal claims."""
    token = _decode_client_principal(headers)
    if not token:
        return set()

    groups: Set[str] = set()
    for claim in _get_claims_list(token):
        claim_type = str(claim.get('typ') or '').strip()
        claim_value = str(claim.get('val') or '').strip()
        if not claim_value:
            continue
        if claim_type in GROUP_CLAIM_TYPES or claim_type.endswith('/claims/groups'):
            groups.add(claim_value)
    return groups


def extract_group_claims(headers) -> List[Dict[str, str]]:
    """Return raw group claim type/value pairs for debugging authorization issues."""
    token = _decode_client_principal(headers)
    if not token:
        return []

    resolved_claims: List[Dict[str, str]] = []
    for claim in _get_claims_list(token):
        claim_type = str(claim.get('typ') or '').strip()
        claim_value = str(claim.get('val') or '').strip()
        if not claim_value:
            continue
        if claim_type in GROUP_CLAIM_TYPES or claim_type.endswith('/claims/groups'):
            resolved_claims.append({
                'type': claim_type,
                'value': claim_value,
            })

    logger.debug("Resolved raw group claims: %s", resolved_claims)
    return resolved_claims
