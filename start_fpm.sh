#!/bin/bash

echo "🚀 Starting Minikube..."
minikube start --driver=docker

echo "📦 Applying all Kubernetes configs..."
kubectl apply -f configmap.yaml
kubectl apply -f elasticsearch-deployment.yaml
kubectl apply -f server-deployment.yaml
kubectl apply -f proxy-agent-deployment.yaml
kubectl apply -f dashboard-deployment.yaml

echo "⏳ Waiting for pods to be ready..."
sleep 10
kubectl get pods

echo "🔍 Getting Elasticsearch URL..."
ES_URL=$(minikube service elasticsearch --url)
echo "✅ Use this ES_HOST in dashboard.py:"
echo ""
echo "ES_HOST = \"$ES_URL\""
echo ""

echo "🧠 Reminder: Run this locally to start dashboard GUI:"
echo "python3 dashboard.py"
