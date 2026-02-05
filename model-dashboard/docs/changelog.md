# Changelog

All notable changes to the Model Dashboard are documented in this file.

## [2.0.0] - 2026-02-05

### 🔐 Authentication Overhaul

#### Removed
- **GitHub SSO Authentication**: Removed GitHub OAuth integration

#### Added
- **LDAP Authentication**: Full LDAP/Active Directory integration with group-based access control
- **Local User Database**: SQLite-based local authentication
- **API Token Authentication**: Bearer token authentication for REST API access

### 🔑 REST API

#### Added
- **REST API Module** (`api.py`):
  - FastAPI-based REST API
  - Bearer token authentication
  - Endpoints:
    - `GET /health` - Health check (no auth)
    - `GET /api/v1/models` - List all models (auth required)

- **API Token Management**:
  - Token creation with expiry dates
  - Token revocation
  - Token usage tracking
  - UI page for token management

- **New Entry Points**:
  - `model-api` - Start REST API server only
  - `model-dashboard-all` - Start both dashboard and API

### 📄 New Pages

- **API Tokens Page** (`pages/tokens.py`): Generate, view, and revoke API tokens

### 🔧 Configuration

#### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `LDAP_SERVER` | LDAP server URL | `ldap://ldap.example.com:389` |
| `LDAP_BASE_DN` | LDAP base DN | `dc=example,dc=com` |
| `LDAP_REQUIRED_GROUP` | Required AD group DN | `` |
| `AUTH_DB_PATH` | Path to SQLite auth DB | `/data/models/.auth/users.db` |
| `MINIO_HOST` | MinIO server host | Auto-detected |
| `MINIO_PORT` | MinIO server port | `9000` |
| `MINIO_USERNAME` | MinIO access key | `argo` |
| `MINIO_PASSWORD` | MinIO secret key | - |
| `API_HOST` | API server host | `0.0.0.0` |
| `API_PORT` | API server port | `8000` |

### 📦 Dependencies

#### Added
- `ldap3` - LDAP authentication
- `fastapi` - REST API framework
- `uvicorn[standard]` - ASGI server
- `streamlit-cookies-controller` - Session management

### 🛠️ Scripts

- `scripts/init_minio_data.py` - Initialize MinIO with sample models
- `scripts/manage_users.py` - CLI for local user management

### 📚 Kubernetes Deployment

- Added `k8s/` directory with deployment manifests
- Includes MinIO, ConfigMap, Secret, PVC, and Deployment resources

---

## [1.0.0] - Previous Version

Initial release with GitHub SSO authentication.
