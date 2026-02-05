# Model Dashboard

A Streamlit-based web dashboard for managing inference models with LDAP authentication and REST API access.

## Features

- **LDAP/Local Authentication**: Enterprise-ready authentication with AD group-based access control
- **REST API**: Full API access to model data with token-based authentication
- **Model Management**: Upload, create, edit, and manage inference models
- **MinIO Integration**: Stores models in MinIO object storage

## Quick Start

### Installation

```bash
pip install -r requirements.txt
pip install -e .
```

### Running the Dashboard

```bash
model-dashboard
```

### Running the REST API

```bash
model-api
```

### Running Both Services

```bash
model-dashboard-all
```

## Configuration

See `config/secrets.toml` for configuration options, or use environment variables:

- `LDAP_SERVER` - LDAP server URL
- `LDAP_REQUIRED_GROUP` - AD group DN for access control
- `MINIO_HOST` / `MINIO_PORT` - MinIO connection settings

## Documentation

Full documentation is available in the `docs/` directory:

- [Architecture](../docs/architecture.md)
- [Authentication](../docs/authentication.md)
- [REST API](../docs/rest-api.md)
- [Configuration](../docs/configuration.md)
- [Deployment](../docs/deployment.md)
- [Changelog](../docs/changelog.md)

## Version

2.0.0 - LDAP Authentication & REST API
