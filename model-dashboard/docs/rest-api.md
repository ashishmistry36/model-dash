# REST API Reference

The Model Dashboard exposes a simple REST API for accessing model data.

## Base URL

```
http://your-server:8000
```

The API runs on port 8000 by default. Configure with `API_PORT` environment variable.

## Authentication

All API endpoints (except `/health`) require authentication using Bearer tokens.

### Getting a Token

1. Log in to the web dashboard at http://localhost:8501
2. Navigate to **Account → API Tokens**
3. Generate a new token and copy it immediately

### Using the Token

Include the token in the `Authorization` header:

```
Authorization: Bearer YOUR_TOKEN_HERE
```

## Endpoints

### Health Check

Check if the API is running. No authentication required.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "message": "API is running"
}
```

---

### List All Models

Get a list of all models.

```http
GET /api/v1/models
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "total": 4,
  "models": [
    {
      "name": "Dataset001_LiverSegmentation",
      "network_type": "nnUNet_v2",
      "description": "Automatic liver and liver lesion segmentation for CT images.",
      "version": "2.5",
      "enabled": true,
      "alias": "Liver and Lesion Segmentation",
      "create_date": "12/1/25",
      "last_modified_date": "1/25/26"
    },
    {
      "name": "MIST_Prostate",
      "network_type": "MIST",
      "description": "Prostate gland segmentation for MRI using MIST framework.",
      "version": "0.4.8",
      "enabled": true,
      "alias": "Prostate MRI Segmentation",
      "create_date": "9/15/25",
      "last_modified_date": "1/10/26"
    }
  ]
}
```

---

## Error Responses

### 401 Unauthorized

```json
{
  "detail": "Invalid API token"
}
```

Causes:
- Missing Authorization header
- Invalid or revoked token
- Expired token

### 500 Internal Server Error

```json
{
  "detail": "Error retrieving models: connection refused"
}
```

---

## Code Examples

### Python (requests)

```python
import requests

API_URL = "http://localhost:8000"
TOKEN = "your-api-token"

headers = {"Authorization": f"Bearer {TOKEN}"}

response = requests.get(f"{API_URL}/api/v1/models", headers=headers)
data = response.json()

print(f"Found {data['total']} models")
for model in data['models']:
    print(f"  - {model['name']} ({model['network_type']})")
```

### cURL

```bash
# Health check
curl http://localhost:8000/health

# List models
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/v1/models
```

### JavaScript (fetch)

```javascript
const API_URL = 'http://localhost:8000';
const TOKEN = 'your-api-token';

async function listModels() {
  const response = await fetch(`${API_URL}/api/v1/models`, {
    headers: {
      'Authorization': `Bearer ${TOKEN}`
    }
  });
  
  const data = await response.json();
  console.log(`Found ${data.total} models`);
  return data.models;
}
```

---

## OpenAPI Documentation

When the API is running, you can access the auto-generated OpenAPI docs at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
