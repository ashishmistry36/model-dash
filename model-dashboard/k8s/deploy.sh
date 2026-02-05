#!/bin/bash
# Deploy Model Dashboard to Minikube
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "=========================================="
echo "Model Dashboard - Minikube Deployment"
echo "=========================================="

# Check if minikube is running
if ! minikube status | grep -q "Running"; then
    echo "Starting Minikube..."
    minikube start
fi

echo ""
echo "Step 1: Building Docker image in Minikube..."
echo "----------------------------------------------"
eval $(minikube docker-env)
docker build -t model-dashboard:latest \
    --build-arg XNAT_UNAME=xnat \
    --build-arg XNAT_GROUP=xnat \
    --build-arg XNAT_UID=1000 \
    --build-arg XNAT_GID=1000 \
    .

echo ""
echo "Step 2: Creating Kubernetes resources..."
echo "-----------------------------------------"

# Apply in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/minio.yaml

echo ""
echo "Step 3: Waiting for MinIO to be ready..."
echo "-----------------------------------------"
kubectl wait --namespace model-dashboard \
    --for=condition=ready pod \
    --selector=app=minio \
    --timeout=120s

echo ""
echo "Step 4: Initializing MinIO with test data..."
echo "---------------------------------------------"
kubectl apply -f k8s/init-data-job.yaml

# Wait for init job to complete
kubectl wait --namespace model-dashboard \
    --for=condition=complete job/init-minio-data \
    --timeout=60s || true

echo ""
echo "Step 5: Deploying Model Dashboard..."
echo "------------------------------------"
kubectl apply -f k8s/deployment.yaml

echo ""
echo "Step 6: Waiting for Dashboard to be ready..."
echo "---------------------------------------------"
kubectl wait --namespace model-dashboard \
    --for=condition=ready pod \
    --selector=app=model-dashboard \
    --timeout=180s

echo ""
echo "Step 7: Creating test users..."
echo "-------------------------------"
kubectl apply -f k8s/create-user-job.yaml

# Wait for user creation job
sleep 10
kubectl wait --namespace model-dashboard \
    --for=condition=complete job/create-admin-user \
    --timeout=60s || true

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Pod Status:"
kubectl get pods -n model-dashboard
echo ""
echo "Services:"
kubectl get svc -n model-dashboard
echo ""
echo "To access the dashboard, run:"
echo "  minikube service model-dashboard -n model-dashboard --url"
echo ""
echo "Or use port-forward:"
echo "  kubectl port-forward -n model-dashboard svc/model-dashboard 8501:8501 8000:8000"
echo ""
echo "Test Credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo "  Auth Type: Local Account"
echo ""
