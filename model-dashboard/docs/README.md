# Model Dashboard Documentation

A Streamlit-based web dashboard for managing inference models with LDAP/local authentication and REST API access.

## Contents

- [Architecture](./architecture.md) - System architecture overview
- [Authentication](./authentication.md) - Authentication configuration (LDAP & local)
- [REST API](./rest-api.md) - API reference and usage
- [Configuration](./configuration.md) - Environment variables and settings
- [Deployment](./deployment.md) - Deployment guide
- [Changelog](./changelog.md) - Version history and changes

## Quick Start

### Running the Dashboard

```bash
# Install dependencies
pip install -r requirements.txt

# Start the dashboard
model-dashboard
```

### Running the REST API

```bash
# Start the API server
model-api

# Or run both dashboard and API together
model-dashboard-all
```

### Creating a Local User

```bash
# Create an admin user
python scripts/manage_users.py create admin mypassword "Admin User" --email admin@example.com
```

### Initializing Test Data

```bash
# Populate MinIO with sample models
python scripts/init_minio_data.py
```

## Features

- **LDAP/Local Authentication**: Enterprise-ready authentication with AD group-based access control
- **REST API**: API access to model data with token-based authentication
- **Model Management**: Upload, create, edit, and manage inference models
- **MinIO Integration**: Stores models in MinIO object storage

## Default Ports

| Service | Port |
|---------|------|
| Dashboard (Streamlit) | 8501 |
| REST API (FastAPI) | 8000 |

## Test Credentials

For local development with the Kubernetes deployment:

- **Username**: `admin`
- **Password**: `admin123`
- **Auth Type**: Local Account
