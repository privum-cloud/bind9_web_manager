# Keycloak SSO

PRIVUM DNS Manager supports Single Sign-On via Keycloak, or any OIDC-compatible provider.
Local admin login stays available alongside it as a break-glass path.

## Step 1 — Configure Keycloak

1. **Create a realm** (or use an existing one):
   - Name: `dns-manager`

2. **Create a client**:
   - Client ID: `dns-web-manager`
   - Client type: `public`
   - Valid redirect URIs: `https://your-dns-manager.example.com/*`
   - Web origins: `https://your-dns-manager.example.com`

3. **Put groups in the token**:
   - Client Scopes → `dns-web-manager-dedicated` → Add mapper
   - Mapper type: `Group Membership`
   - Name: `groups`
   - Token claim name: `groups`
   - Full group path: `OFF`

4. **Create the groups** used for role mapping:

   | Group | Role in DNS Manager |
   |---|---|
   | `dns-admin` | Full administrative access |
   | `dns-operator` | Manage zones and records |
   | `dns-viewer` | Read-only access |

5. **Assign users** to the appropriate groups.

## Step 2 — Configure DNS Manager

Edit `/opt/dns-manager/.env`:

```bash
# Enable Keycloak SSO
KEYCLOAK_ENABLED=true

# Keycloak server URL (no trailing slash)
KEYCLOAK_SERVER_URL=https://keycloak.example.com

# Realm name
KEYCLOAK_REALM=dns-manager

# Client ID (must match the Keycloak client)
KEYCLOAK_CLIENT_ID=dns-web-manager

# Group to role mapping (JSON)
KEYCLOAK_GROUP_MAPPING={"dns-admin":"admin","dns-operator":"operator","dns-viewer":"viewer"}

# Keep local admin login as a fallback (recommended)
LOCAL_ADMIN_ENABLED=true

# SSL verification (keep true in production)
KEYCLOAK_VERIFY_SSL=true
```

## Step 3 — Restart

```bash
sudo systemctl restart dns-manager-api
```

## How the login flow works

1. The user clicks **"Login with SSO"** on the login page.
2. The browser is redirected to Keycloak to authenticate.
3. Keycloak redirects back with an authorization code.
4. DNS Manager exchanges the code for a token and validates it against the realm's JWKS.
5. The user is created or updated from their Keycloak profile.
6. Their role is assigned from their group membership.

Group-to-role mapping is re-evaluated on **every request**, so removing someone from a Keycloak
group takes effect immediately — no need to touch DNS Manager.

## Roles and permissions

| Role | Permissions |
|---|---|
| `admin` | Full access: users, zones, records, settings, backups |
| `operator` | Manage zones and records; view settings |
| `viewer` | Read-only access to zones and records |

## Break-glass access

A user flagged as a **local admin** is exempt from Keycloak role re-mapping and can always log in
with their local password. Keep at least one such account so an outage or misconfiguration on the
Keycloak side can't lock you out of your own DNS.
