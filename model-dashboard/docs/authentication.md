# Authentication Guide

The Model Dashboard supports two authentication methods:

1. **LDAP/Active Directory** - For enterprise environments
2. **Local Database** - For standalone deployments or fallback

## LDAP Authentication

LDAP authentication allows users to sign in with their network credentials and validates membership in a required AD group.

### Configuration

Configure LDAP via environment variables or `config/secrets.toml`:

```toml
[ldap]
server = "ldap://ldap.example.com:389"
base_dn = "dc=example,dc=com"
user_dn_template = "uid={username},ou=users,dc=example,dc=com"
search_filter = "(uid={username})"
required_group = "cn=model-dashboard-users,ou=groups,dc=example,dc=com"
group_attribute = "memberOf"
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LDAP_SERVER` | LDAP server URL | `ldap://dc1.company.com:389` |
| `LDAP_BASE_DN` | Base DN for searches | `dc=company,dc=com` |
| `LDAP_USER_DN_TEMPLATE` | Template for user DN | `cn={username},ou=users,dc=company,dc=com` |
| `LDAP_SEARCH_FILTER` | Filter for user search | `(sAMAccountName={username})` |
| `LDAP_REQUIRED_GROUP` | DN of required group (empty = all authenticated users) | `cn=ModelDashboardUsers,ou=groups,...` |
| `LDAP_GROUP_ATTRIBUTE` | Attribute containing group membership | `memberOf` |

### Active Directory Configuration

For Active Directory environments, use these settings:

```bash
export LDAP_SERVER="ldap://your-dc.company.com:389"
export LDAP_BASE_DN="dc=company,dc=com"
export LDAP_USER_DN_TEMPLATE="cn={username},cn=users,dc=company,dc=com"
export LDAP_SEARCH_FILTER="(sAMAccountName={username})"
export LDAP_REQUIRED_GROUP="cn=ModelDashboardUsers,ou=SecurityGroups,dc=company,dc=com"
export LDAP_GROUP_ATTRIBUTE="memberOf"
```

### Group-Based Access Control

To restrict access to members of a specific AD group:

1. Create an AD group (e.g., `ModelDashboardUsers`)
2. Add authorized users to the group
3. Set `LDAP_REQUIRED_GROUP` to the group's full DN

Users not in the required group will see an "unauthorized" error.

To allow all authenticated users (no group restriction):
```bash
export LDAP_REQUIRED_GROUP=""
```

## Local Database Authentication

Local authentication stores users in a SQLite database for environments without LDAP.

### Database Location

Default: `/data/models/.auth/users.db`

Override with:
```bash
export AUTH_DB_PATH="/path/to/users.db"
```

### Managing Users

Use the CLI tool to manage local users:

```bash
# Create a user
python scripts/manage_users.py create admin password123 "Admin User" --email admin@company.com

# List all users
python scripts/manage_users.py list

# Disable a user
python scripts/manage_users.py disable username

# Enable a user
python scripts/manage_users.py enable username

# Reset password
python scripts/manage_users.py reset-password username newpassword

# Delete a user
python scripts/manage_users.py delete username
```

### Password Security

Passwords are hashed using SHA-256 before storage. The actual passwords are never stored.

## API Token Authentication

For REST API access, users can generate API tokens from the dashboard.

### Token Features

- Generated with cryptographically secure random tokens
- Configurable expiry (default: 30 days)
- Usage tracking (last used timestamp)
- Revocable at any time

### Generating Tokens

1. Log in to the dashboard
2. Navigate to **Account → API Tokens**
3. Enter a description for the token
4. Click **Generate Token**
5. **Copy the token immediately** - it won't be shown again

### Using Tokens

Include the token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://your-server/api/v1/models
```

Python example:
```python
import requests

headers = {"Authorization": "Bearer YOUR_TOKEN"}
response = requests.get(
    "https://your-server/api/v1/models",
    headers=headers
)
```

### Token Expiry

Tokens expire after 30 days by default. Configure with:
```bash
export API_TOKEN_EXPIRY_DAYS=90
```

### Revoking Tokens

1. Navigate to **Account → API Tokens**
2. Scroll to **Revoke Token**
3. Paste the token you want to revoke
4. Click **Revoke Token**

## Session Management

Web sessions are stored in browser cookies and validated on each request.

### Cookie Configuration

```bash
export SESSION_COOKIE_KEY="model-dashboard-session"
```

### Session Security

- Sessions are stored as JSON in cookies
- Cookie is removed on logout
- Session persists across browser refreshes

## Troubleshooting

### LDAP Connection Failed

1. Verify LDAP server is accessible:
   ```bash
   ldapsearch -x -H ldap://your-server:389 -b "dc=company,dc=com"
   ```

2. Check firewall rules for port 389 (or 636 for LDAPS)

3. Verify the user DN template is correct for your directory structure

### User Not Authorized

If users get "not authorized" errors:

1. Verify user is in the required AD group:
   ```bash
   ldapsearch -x -H ldap://server:389 -b "dc=company,dc=com" \
     "(sAMAccountName=username)" memberOf
   ```

2. Check the `LDAP_REQUIRED_GROUP` value matches the exact DN

3. Temporarily clear `LDAP_REQUIRED_GROUP` to test basic authentication

### API Token Invalid

1. Verify the token hasn't expired
2. Check the token was copied correctly (no extra spaces)
3. Ensure the user account is still active
