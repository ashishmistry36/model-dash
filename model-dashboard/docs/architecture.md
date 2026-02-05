# Architecture Overview

The Model Dashboard is a web application for managing inference models with enterprise authentication and REST API access.

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Model Dashboard                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐                 │
│  │   Streamlit UI   │     │    FastAPI       │                 │
│  │   (Port 8501)    │     │    REST API      │                 │
│  │                  │     │   (Port 8000)    │                 │
│  └────────┬─────────┘     └────────┬─────────┘                 │
│           │                        │                            │
│           └──────────┬─────────────┘                            │
│                      │                                          │
│              ┌───────┴───────┐                                  │
│              │   auth.py     │                                  │
│              │ Authentication│                                  │
│              └───────┬───────┘                                  │
│                      │                                          │
│      ┌───────────────┼───────────────┐                         │
│      │               │               │                          │
│  ┌───┴───┐      ┌────┴────┐    ┌────┴────┐                     │
│  │ LDAP/ │      │ SQLite  │    │  MinIO  │                     │
│  │  AD   │      │  Auth   │    │ Models  │                     │
│  └───────┘      │   DB    │    │   DB    │                     │
│                 └─────────┘    └─────────┘                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Frontend (Streamlit)

The web UI is built with [Streamlit](https://streamlit.io/):

- **Login Page**: Authentication with LDAP or local credentials
- **Model Dashboard**: View and manage inference models
- **Upload Page**: Upload new model packages
- **Create Page**: Create model definitions
- **User Profile**: View account information
- **API Tokens**: Generate and manage API tokens

### REST API (FastAPI)

Simple API for programmatic access:

- `GET /health` - Health check
- `GET /api/v1/models` - List all models

### Authentication (auth.py)

Unified authentication module:

- LDAP/Active Directory authentication
- Local SQLite user database
- API token management

### Model Storage (MinIO)

Models stored in MinIO object storage as JSON objects.

## File Structure

```
model-dashboard/
├── config/
│   ├── config.toml         # Streamlit configuration
│   └── secrets.toml        # Sensitive configuration
│
├── docs/                   # Documentation
│
├── k8s/                    # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── pvc.yaml
│   ├── minio.yaml
│   ├── deployment.yaml
│   └── init-data-job.yaml
│
├── scripts/
│   ├── init_minio_data.py  # Initialize test data
│   └── manage_users.py     # User management CLI
│
├── src/
│   ├── pyproject.toml      # Package configuration
│   └── model_dashboard/
│       ├── __init__.py     # Entry points
│       ├── app.py          # Main Streamlit app
│       ├── api.py          # FastAPI REST API
│       ├── auth.py         # Authentication
│       ├── connection.py   # MinIO database
│       ├── models.py       # Pydantic models
│       ├── utils.py        # Utilities
│       └── pages/
│           ├── models.py   # Dashboard page
│           ├── upload.py   # Upload page
│           ├── create.py   # Create page
│           ├── user.py     # Profile page
│           └── tokens.py   # API tokens page
│
├── Dockerfile
└── requirements.txt
```

## Database Schema

### Users Table (SQLite)

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### API Tokens Table (SQLite)

```sql
CREATE TABLE api_tokens (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    token_hash TEXT UNIQUE NOT NULL,
    description TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP,
    last_used_at TIMESTAMP
);
```

## Ports

| Service | Port |
|---------|------|
| Streamlit Dashboard | 8501 |
| FastAPI REST API | 8000 |
| MinIO API | 9000 |
| MinIO Console | 9001 |
