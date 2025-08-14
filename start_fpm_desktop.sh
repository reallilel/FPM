#!/bin/bash

# اسم السكربت: start_fpm_desktop.sh
# الوصف: يقوم هذا السكربت بأتمتة نشر وتشغيل مكونات مشروع FPM.
#        يشغل Minikube، يعيد نشر تطبيقات Kubernetes،
#        يفتح لوحة تحكم الويب، ويشغل تطبيق Tkinter (إذا كان موجوداً).

# Exit immediately if a command exits with a non-zero status.
set -e
# Print commands and their arguments as they are executed.
set -x

echo "Starting FPM Project Automation..."

# 1. التحقق من حالة Minikube وبدء تشغيله إذا لم يكن يعمل
echo "Checking Minikube status..."
if ! minikube status &> /dev/null; then
    echo "Minikube is not running. Starting Minikube..."
    minikube start --driver=docker --memory=4096 --cpus=2 || { echo "Error: Failed to start Minikube. Exiting."; exit 1; }
    echo "Minikube started successfully."
else
    echo "Minikube is already running."
fi

# Set Docker environment for Minikube
# This is crucial for Docker commands to build images directly into Minikube's daemon
eval $(minikube docker-env)

# 2. حذف وإعادة تطبيق Deployments و Services (Clean Up)
echo "Deleting existing Kubernetes deployments and services..."
# Delete Deployments first
kubectl delete deployment fpm-dashboard elasticsearch fpm-server --ignore-not-found=true || true
# Then delete Services
kubectl delete service fpm-dashboard elasticsearch fpm-server --ignore-not-found=true || true

# Wait a bit to ensure old pods and services are fully terminated
echo "Waiting for old pods and services to terminate..."
sleep 10 # Increased sleep time for more robustness

# --- 3. Build Docker Images ---
echo "Building Docker images..."
# Build FPM Server image
echo "Building fpm-server image..."
docker build -t reallilel/fpm-server:latest -f Dockerfile.server . --no-cache

# Build FPM Dashboard image
echo "Building fpm-dashboard image..."
docker build -t reallilel/fpm-dashboard:latest -f Dockerfile.dashboard . --no-cache


echo "Applying Kubernetes deployments and services..."

# Apply Elasticsearch deployment and service
echo "Applying Elasticsearch deployment..."
kubectl apply -f elasticsearch-deployment.yaml || { echo "Error: Failed to apply elasticsearch-deployment.yaml. Exiting."; exit 1; }
# Add a check for service creation
sleep 2 # Give Kubernetes a moment to register the service
kubectl get service elasticsearch || { echo "Error: Elasticsearch service not found after apply. Exiting."; exit 1; }
echo "Elasticsearch deployment applied. Waiting for Elasticsearch pod to be ready..."
kubectl wait --for=condition=ready pod -l app=elasticsearch --timeout=300s || { echo "Error: Elasticsearch pod not ready. Check logs. Exiting."; exit 1; }
echo "Elasticsearch pod is ready."

# Apply Server deployment and service
echo "Applying FPM Server deployment..."
kubectl apply -f server-deployment.yaml || { echo "Error: Failed to apply server-deployment.yaml. Exiting."; exit 1; }
# Add a check for service creation
sleep 2 # Give Kubernetes a moment to register the service
kubectl get service fpm-server || { echo "Error: FPM Server service not found after apply. Exiting."; exit 1; }
echo "FPM Server deployment applied. Waiting for FPM Server pod to be ready..."
kubectl wait --for=condition=ready pod -l app=fpm-server --timeout=300s || { echo "Error: FPM Server pod not ready. Check logs. Exiting."; exit 1; }
echo "FPM Server pod is ready."

# Apply Dashboard deployment and service
echo "Applying FPM Dashboard deployment..."
kubectl apply -f dashboard-deployment.yaml || { echo "Error: Failed to apply dashboard-deployment.yaml. Exiting."; exit 1; }
# Add a check for service creation
sleep 2 # Give Kubernetes a moment to register the service
kubectl get service fpm-dashboard || { echo "Error: FPM Dashboard service not found after apply. Exiting."; exit 1; }
echo "FPM Dashboard deployment applied. Waiting for FPM Dashboard pod to be ready..."
kubectl wait --for=condition=ready pod -l app=fpm-dashboard --timeout=300s || { echo "Error: FPM Dashboard pod not ready. Check logs. Exiting."; exit 1; }
echo "FPM Dashboard pod is ready."

# 4. Get Service URLs
echo "Getting FPM Dashboard URL..."
# Removed: kubectl wait --for=condition=ready service fpm-dashboard --timeout=120s
# Removed: kubectl wait --for=condition=ready service fpm-server --timeout=120s
# Removed: kubectl wait --for=condition=ready service elasticsearch --timeout=120s # <--- تم إزالة هذا السطر أيضاً


DASHBOARD_URL=$(minikube service fpm-dashboard --url)
SERVER_URL=$(minikube service fpm-server --url)
ELASTICSEARCH_URL=$(minikube service elasticsearch --url)


if [[ -z "$DASHBOARD_URL" ]]; then
    echo "Error: Could not get FPM Dashboard URL. Ensure the service is correctly exposed. Exiting."
    exit 1
fi

# Use HTTP for Dashboard URL as we've temporarily disabled HTTPS in dashboard.py
# DASHBOARD_URL_HTTPS="${DASHBOARD_URL/http:/https:}" # Removed: No longer forcing HTTPS
echo "FPM Dashboard URL (HTTP): $DASHBOARD_URL" # Changed message to HTTP
echo "FPM Server URL: $SERVER_URL"
echo "Elasticsearch URL: $ELASTICSEARCH_URL"

echo "Opening FPM Dashboard in your default web browser..."
xdg-open "$DASHBOARD_URL" || { echo "Warning: Failed to open browser automatically. Please open the URL manually: $DASHBOARD_URL"; } # Changed to DASHBOARD_URL

# 5. Run Tkinter dashboard (tk_dashboard.py)
echo "Starting Tkinter Dashboard (tk_dashboard.py)..."
# Set Elasticsearch address automatically for Tkinter
# We need the IP:PORT part of the URL
TK_ES_HOST_IP_PORT=$(echo $ELASTICSEARCH_URL | sed 's|http://||')
sed -i "s|ES_HOST = \".*\"|ES_HOST = \"http://$TK_ES_HOST_IP_PORT\"|" tk_dashboard.py

# Set FPM Server URL automatically for proxy_agent.py (for Windows VM)
# proxy_agent.py expects HTTPS, so we manually add https://
TK_SERVER_URL_IP_PORT=$(echo $SERVER_URL | sed 's|http://||')
sed -i "s|SERVER_URL = \".*\"|SERVER_URL = \"https://$TK_SERVER_URL_IP_PORT\"|" proxy_agent.py


python3 tk_dashboard.py &
echo "Tkinter Dashboard started in the background."

echo "All components are launched. Please check your browser for the dashboard."
echo "Script finished."
