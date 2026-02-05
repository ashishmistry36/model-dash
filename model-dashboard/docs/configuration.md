# Configuration Guide

This document describes all configuration options for the Model Dashboard.

## Configuration Files

### config/secrets.toml

Contains sensitive configuration that should not be committed to version control.

```toml
[model_db]
username = "argo"
password = "@rgo.password"
bucket = "argo-models"
namespace = "inference"
# host = "minio.example.com"  # Optional
# port = 9000                  # Optional

[ldap]
server = "ldap://ldap.example.com:389"
base_dn = "dc=example,dc=com"
user_dn_template = "uid={username},ou=users,dc=example,dc=com"
search_filter = "(uid={username})"
required_group = "cn=model-dashboard-users,ou=groups,dc=example,dc=com"
group_attribute = "memberOf"

[auth]
session_cookie_key = "model-dashboard-session"
api_token_expiry_days = 30
```

### config/config.toml

Streamlit server configuration.

```toml
[logger]
level = "info"
messageFormat = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

[server]
headless = true
runOnSave = true
baseUrlPath = "/argo-models"
maxUploadSize = 10000

[browser]
gatherUsageStats = false

[theme]
base = "dark"
```

## Environment Variables

Environment variables take precedence over configuration files.

### MinIO Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MINIO_HOST` | MinIO server hostname | `argo-artifacts.{namespace}.svc.cluster.local` |
| `MINIO_PORT` | MinIO server port | `9000` |
| `MINIO_USERNAME` | MinIO access key | `argo` |
| `MINIO_PASSWORD` | MinIO secret key | `@rgo.password` |
| `MINIO_BUCKET` | Bucket name for models | `argo-models` |
| `MINIO_NAMESPACE` | Kubernetes namespace | `inference` |

### LDAP Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LDAP_SERVER` | LDAP server URL | `ldap://ldap.example.com:389` |
| `LDAP_BASE_DN` | Base DN for searches | `dc=example,dc=com` |
| `LDAP_USER_DN_TEMPLATE` | User DN template (`{username}` is replaced) | See below |
| `LDAP_SEARCH_FILTER` | Search filter for user lookup | `(uid={username})` |
| `LDAP_REQUIRED_GROUP` | Required group DN (empty = no restriction) | `` |
| `LDAP_GROUP_ATTRIBUTE` | Attribute containing group membership | `memberOf` |

Default `LDAP_USER_DN_TEMPLATE`: `uid={username},ou=users,dc=example,dc=com`

### Authentication Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTH_DB_PATH` | Path to SQLite auth database | `/data/models/.auth/users.db` |
| `API_TOKEN_EXPIRY_DAYS` | Token expiry in days | `30` |
| `SESSION_COOKIE_KEY` | Session cookie name | `model-dashboard-session` |

### API Server Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `API_HOST` | API server bind address | `0.0.0.0` |
| `API_PORT` | API server port | `8000` |
| `API_RELOAD` | Enable auto-reload (dev mode) | `false` |

### Logging Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_DIR` | Directory for log files | `/data/models/.logs` |

### OAuth Callback (for reverse proxy setups)

| Variable | Description | Default |
|----------|-------------|---------|
| `CALLBACK_URL` | OAuth callback URL | (auto-detected) |

## Docker Configuration

When running in Docker, set environment variables:

```yaml
version: '3.8'
services:
  dashboard:
    image: model-dashboard:latest
    ports:
      - "8501:8501"
      - "8000:8000"
    environment:
      - MINIO_HOST=minio
      - MINIO_PORT=9000
      - MINIO_USERNAME=argo
      - MINIO_PASSWORD=secretpassword
      - LDAP_SERVER=ldap://ldap.company.com:389
      - LDAP_BASE_DN=dc=company,dc=com
      - LDAP_REQUIRED_GROUP=cn=ModelUsers,ou=groups,dc=company,dc=com
    volumes:
      - ./data:/data
```

## Kubernetes Configuration

Use ConfigMaps and Secrets:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: model-dashboard-config
data:
  MINIO_HOST: "minio.storage.svc.cluster.local"
  MINIO_PORT: "9000"
  MINIO_BUCKET: "argo-models"
  LDAP_SERVER: "ldap://ldap.company.com:389"
  LDAP_BASE_DN: "dc=company,dc=com"
---
apiVersion: v1
kind: Secret
metadata:
  name: model-dashboard-secrets
type: Opaque
stringData:
  MINIO_USERNAME: "argo"
  MINIO_PASSWORD: "secretpassword"
```

## URL Configuration

### Base URL Path

If running behind a reverse proxy with a path prefix:

```toml
[server]
baseUrlPath = "/argo-models"
```

This affects:
- Dashboard URL: `https://server.com/argo-models`
- API URL: `https://server.com/api/v1/...` (API runs separately)

### CORS Configuration

By default, the API allows all origins. To restrict:

Edit `src/model_dashboard/api.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

## Security Recommendations

### Production Settings

1. **Use HTTPS**: Run behind an HTTPS-enabled reverse proxy
2. **Restrict CORS**: Limit allowed origins in production
3. **Secure Secrets**: Use Kubernetes Secrets or vault integration
4. **Enable AD Groups**: Use `LDAP_REQUIRED_GROUP` to restrict access
5. **Limit Token Expiry**: Set reasonable token expiry periods
6. **Monitor Logs**: Configure log aggregation

### Cookie Security

In `config/config.toml`, set a random cookie secret for multi-replica deployments:

```toml
[server]
cookieSecret = "your-random-secret-key-here"
```

## Development Settings

For local development:

```bash
export MINIO_HOST=localhost
export MINIO_PORT=9000
export LDAP_REQUIRED_GROUP=""  # Disable group check
export API_RELOAD=true         # Enable hot reload
```

Run MinIO locally:
```bash
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=argo \
  -e MINIO_ROOT_PASSWORD=@rgo.password \
  minio/minio server /data --console-address ':9001'
```

Initialize test data:
```bash
python scripts/init_minio_data.py
python scripts/manage_users.py create admin password123 "Admin User"
```
