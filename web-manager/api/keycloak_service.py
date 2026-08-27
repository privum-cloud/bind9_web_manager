"""
DNS Web Manager - Keycloak SSO Service
JWT validation and user provisioning for Keycloak integration
"""
from jose import jwt, JWTError
import requests
from cachetools import TTLCache
from flask import current_app

# Cache JWKS keys for 1 hour
_jwks_cache = TTLCache(maxsize=10, ttl=3600)


class KeycloakService:
    """Service class for Keycloak SSO operations"""

    @staticmethod
    def get_jwks():
        """Fetch and cache Keycloak JWKS public keys"""
        jwks_url = current_app.config['KEYCLOAK_JWKS_URL']

        if jwks_url in _jwks_cache:
            return _jwks_cache[jwks_url]

        try:
            # Note: verify=False for development with self-signed certs
            verify_ssl = current_app.config.get('KEYCLOAK_VERIFY_SSL', False)
            response = requests.get(jwks_url, timeout=10, verify=verify_ssl)
            response.raise_for_status()
            jwks = response.json()
            _jwks_cache[jwks_url] = jwks
            return jwks
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch JWKS from Keycloak: {str(e)}")

    @staticmethod
    def get_public_key(token):
        """Get the public key that matches the token's kid"""
        jwks = KeycloakService.get_jwks()
        unverified_header = jwt.get_unverified_header(token)

        for key in jwks.get('keys', []):
            if key.get('kid') == unverified_header.get('kid'):
                return key

        raise JWTError("Unable to find matching key in JWKS")

    @staticmethod
    def validate_token(token):
        """Validate Keycloak JWT token and extract claims"""
        try:
            public_key = KeycloakService.get_public_key(token)

            # Build issuer URL
            server_url = current_app.config['KEYCLOAK_SERVER_URL']
            realm = current_app.config['KEYCLOAK_REALM']
            issuer = f"{server_url}/realms/{realm}"

            payload = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=current_app.config['KEYCLOAK_CLIENT_ID'],
                issuer=issuer,
                options={
                    'verify_aud': True,
                    'verify_iss': True,
                    'verify_exp': True
                }
            )

            return payload
        except JWTError as e:
            raise ValueError(f"Invalid Keycloak token: {str(e)}")

    @staticmethod
    def map_groups_to_role(groups):
        """Map Keycloak groups to application role

        Priority order: admin > operator > viewer
        """
        if not groups:
            return 'viewer'

        group_mapping = current_app.config.get('KEYCLOAK_GROUP_MAPPING', {})

        # Normalize group names (handle nested groups like /parent/dns-admin)
        normalized_groups = []
        for group in groups:
            # Extract the last part of the group path
            group_name = group.split('/')[-1] if '/' in group else group
            normalized_groups.append(group_name)

        # Check for admin first (highest priority)
        for group_name in normalized_groups:
            if group_name in group_mapping and group_mapping[group_name] == 'admin':
                return 'admin'

        # Check for operator
        for group_name in normalized_groups:
            if group_name in group_mapping and group_mapping[group_name] == 'operator':
                return 'operator'

        # Check for viewer
        for group_name in normalized_groups:
            if group_name in group_mapping and group_mapping[group_name] == 'viewer':
                return 'viewer'

        # Default role if no matching group
        return 'viewer'

    @staticmethod
    def extract_user_info(payload):
        """Extract user information from Keycloak token payload"""
        import sys
        print(f"[SSO] Token payload keys: {payload.keys()}", file=sys.stderr)
        print(f"[SSO] sub value: {payload.get('sub')}", file=sys.stderr)

        return {
            'keycloak_id': payload.get('sub'),
            'username': payload.get('preferred_username'),
            'email': payload.get('email'),
            'groups': payload.get('groups', []),
            'first_name': payload.get('given_name', ''),
            'last_name': payload.get('family_name', ''),
            'email_verified': payload.get('email_verified', False)
        }

    @staticmethod
    def clear_jwks_cache():
        """Clear the JWKS cache (useful for key rotation)"""
        _jwks_cache.clear()

    @staticmethod
    def exchange_code_for_token(code, redirect_uri):
        """Exchange authorization code for access token

        Args:
            code: Authorization code from Keycloak redirect
            redirect_uri: The redirect URI used in the original auth request

        Returns:
            dict with access_token, refresh_token, etc.
        """
        server_url = current_app.config['KEYCLOAK_SERVER_URL']
        realm = current_app.config['KEYCLOAK_REALM']
        client_id = current_app.config['KEYCLOAK_CLIENT_ID']

        token_url = f"{server_url}/realms/{realm}/protocol/openid-connect/token"

        try:
            # Note: verify=False for development with self-signed certs
            # In production, set KEYCLOAK_VERIFY_SSL=true
            verify_ssl = current_app.config.get('KEYCLOAK_VERIFY_SSL', False)

            response = requests.post(
                token_url,
                data={
                    'grant_type': 'authorization_code',
                    'client_id': client_id,
                    'code': code,
                    'redirect_uri': redirect_uri
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                timeout=10,
                verify=verify_ssl
            )

            if response.status_code != 200:
                error_msg = response.json().get('error_description', 'Unknown error')
                raise ValueError(f"Token exchange failed: {error_msg}")

            return response.json()
        except requests.RequestException as e:
            raise ValueError(f"Failed to exchange code for token: {str(e)}")
