"""
Authentication utilities for extracting user information from Container Apps headers
"""
import base64
import json
from typing import Dict, Optional


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
    if "X-MS-CLIENT-PRINCIPAL" not in headers:
        return {
            'name': default_username,
            'email': None,
            'id': None
        }

    try:
        token = json.loads(base64.b64decode(
            headers.get("X-MS-CLIENT-PRINCIPAL")))
        claims = {claim["typ"]: claim["val"]
                  for claim in token.get("claims", [])}

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
