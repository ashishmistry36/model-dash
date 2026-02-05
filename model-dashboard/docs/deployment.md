# Deployment Guide

This guide covers deploying the Model Dashboard in various environments.

## Prerequisites

- Python 3.10+
- MinIO server (or S3-compatible storage)
- LDAP server (optional, for enterprise auth)
- Docker (for containerized deployment)

## Local Development

### 1. Install Dependencies

```bash
cd model-dashboard
pip install -r requirements.txt
pip install -e src/
```

### 2. Start MinIO (if not available)

```bash
docker run -d -p 9000:9000 -p 9001:9001 \
  --name minio \
  -e MINIO_ROOT_USER=argo \
  -e MINIO_ROOT_PASSWORD=@rgo.password \
  minio/minio server /data --console-address ':9001'
```

### 3. Initialize Test Data

```bash
export MINIO_HOST=localhost
python scripts/init_minio_data.py
python scripts/manage_users.py create admin password123 "Admin"
```

### 4. Run the Dashboard

```bash
# Dashboard only
model-dashboard

# API only
model-api

# Both
model-dashboard-all
```

Access at:
- Dashboard: http://localhost:8501
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Docker Deployment

### Build the Image

```bash
docker build -t model-dashboard:latest \
  --build-arg XNAT_UNAME=xnat \
  --build-arg XNAT_GROUP=xnat \
  --build-arg XNAT_UID=1000 \
  --build-arg XNAT_GID=1000 \
  .
```

### Run with Docker

```bash
docker run -d \
  --name model-dashboard \
  -p 8501:8501 \
  -p 8000:8000 \
  -v /data/models:/data/models \
  -e MINIO_HOST=minio.local \
  -e MINIO_USERNAME=argo \
  -e MINIO_PASSWORD=secretpassword \
  -e LDAP_SERVER=ldap://ldap.company.com:389 \
  model-dashboard:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  dashboard:
    build: .
    ports:
      - "8501:8501"
      - "8000:8000"
    environment:
      - MINIO_HOST=minio
      - MINIO_PORT=9000
      - MINIO_USERNAME=argo
      - MINIO_PASSWORD=secretpassword
      - MINIO_BUCKET=argo-models
      - LDAP_SERVER=ldap://ldap:389
      - AUTH_DB_PATH=/data/auth/users.db
    volumes:
      - ./data:/data
    depends_on:
      - minio

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=argo
      - MINIO_ROOT_PASSWORD=secretpassword
    command: server /data --console-address ':9001'
    volumes:
      - minio-data:/data

volumes:
  minio-data:
```

Run:
```bash
docker-compose up -d
```

## Kubernetes Deployment

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: model-dashboard-config
  namespace: inference
data:
  MINIO_HOST: "argo-artifacts.inference.svc.cluster.local"
  MINIO_PORT: "9000"
  MINIO_BUCKET: "argo-models"
  MINIO_NAMESPACE: "inference"
  LDAP_SERVER: "ldap://ldap.company.com:389"
  LDAP_BASE_DN: "dc=company,dc=com"
  LDAP_REQUIRED_GROUP: "cn=ModelDashboardUsers,ou=groups,dc=company,dc=com"
```

### Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: model-dashboard-secrets
  namespace: inference
type: Opaque
stringData:
  MINIO_USERNAME: "argo"
  MINIO_PASSWORD: "your-secret-password"
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: model-dashboard
  namespace: inference
spec:
  replicas: 2
  selector:
    matchLabels:
      app: model-dashboard
  template:
    metadata:
      labels:
        app: model-dashboard
    spec:
      containers:
      - name: dashboard
        image: model-dashboard:latest
        ports:
        - containerPort: 8501
          name: dashboard
        - containerPort: 8000
          name: api
        envFrom:
        - configMapRef:
            name: model-dashboard-config
        - secretRef:
            name: model-dashboard-secrets
        volumeMounts:
        - name: data
          mountPath: /data
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "1Gi"
            cpu: "500m"
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: model-dashboard-data
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: model-dashboard
  namespace: inference
spec:
  selector:
    app: model-dashboard
  ports:
  - name: dashboard
    port: 8501
    targetPort: 8501
  - name: api
    port: 8000
    targetPort: 8000
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: model-dashboard
  namespace: inference
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  rules:
  - host: xnat.example.com
    http:
      paths:
      - path: /argo-models(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: model-dashboard
            port:
              number: 8501
      - path: /api/v1(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: model-dashboard
            port:
              number: 8000
```

### PersistentVolumeClaim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-dashboard-data
  namespace: inference
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
```

## Reverse Proxy Configuration

### Nginx

```nginx
server {
    listen 443 ssl;
    server_name xnat.example.com;

    # Dashboard
    location /argo-models {
        proxy_pass http://model-dashboard:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    # API
    location /api/v1 {
        proxy_pass http://model-dashboard:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Traefik

```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: IngressRoute
metadata:
  name: model-dashboard
spec:
  entryPoints:
    - websecure
  routes:
    - match: Host(`xnat.example.com`) && PathPrefix(`/argo-models`)
      kind: Rule
      services:
        - name: model-dashboard
          port: 8501
    - match: Host(`xnat.example.com`) && PathPrefix(`/api/v1`)
      kind: Rule
      services:
        - name: model-dashboard
          port: 8000
```

## Health Checks

### Dashboard Health

The Streamlit dashboard doesn't have a built-in health endpoint. Use TCP checks:

```yaml
livenessProbe:
  tcpSocket:
    port: 8501
  initialDelaySeconds: 30
  periodSeconds: 10
```

### API Health

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## High Availability

For HA deployments:

1. **Multiple Replicas**: Run 2+ pods
2. **Shared Cookie Secret**: Set `cookieSecret` in config for session sharing
3. **External Database**: Move SQLite auth DB to PostgreSQL
4. **MinIO Cluster**: Use distributed MinIO or S3

## Monitoring

### Metrics

The API can be extended with Prometheus metrics:

```python
# api.py
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

### Logging

Logs are written to:
- stdout/stderr (for container logs)
- `/data/models/.logs/model_dashboard.log` (rotated daily)

Configure log aggregation (e.g., Fluentd, CloudWatch) for centralized logging.

## Troubleshooting

### Container Won't Start

1. Check logs: `docker logs model-dashboard`
2. Verify MinIO connectivity
3. Check environment variables

### LDAP Connection Issues

1. Verify LDAP server reachability
2. Check firewall rules for port 389/636
3. Test with ldapsearch tool

### MinIO Connection Issues

1. Verify MinIO host and port
2. Check credentials
3. Ensure bucket exists

### API Returns 401

1. Token may be expired
2. User account may be disabled
3. Check Authorization header format
