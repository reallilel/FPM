# 🕵️‍♂️ Forensic Proxy Mesh (FPM)

**Forensic Proxy Mesh (FPM)** is a system for collecting and analyzing network traffic from multiple agents and sending it to an **Elasticsearch server**, then displaying it on a **GUI dashboard** for analysis.

In the current configuration, the Agent has been modified to only send events for:
- Opening a new website (URL entered and loaded).
- Clicking on a link within a website.

---

## 📂 Project Components
- **fpm-server** → Central server that receives and processes agent data.
- **fpm-agent** → Client-side script that runs on monitored machines to capture traffic events.
- **Elasticsearch** → Stores all incoming event data from agents.
- **GUI Dashboard** → Visual interface to view and analyze traffic data.

---

## ⚙️ Requirements
Before running FPM, ensure you have:
- **Kali Linux / Linux host** (for the server side)
- **Windows or Linux machine** (for the agent)
- **Python 3.8+**
- **Docker** & **Minikube**
- **kubectl**
- **Elasticsearch** (configured with TLS)
- **Required Python packages**:
  ```bash
  pip install -r requirements.txt

🚀 How to Run
1️⃣ Start Minikube
minikube start --driver=docker

2️⃣ Deploy Elasticsearch & FPM Services
kubectl apply -f elasticsearch-deployment.yaml
kubectl apply -f server-deployment.yaml
kubectl apply -f dashboard-deployment.yaml
kubectl apply -f proxy-agent-deployment.yaml

3️⃣ Start the Server Locally (Optional for Debug)
python server.py

4️⃣ Forward Ports for Access
kubectl port-forward --address 0.0.0.0 svc/fpm-server 30000:8443
kubectl port-forward --address 0.0.0.0 svc/fpm-dashboard 6060:6000


Server API → https://<server-ip>:30000

Dashboard GUI → http://<server-ip>:6060

🖥️ Running the Agent

On the monitored machine:

python proxy_agent.py


The agent will:

Capture new site visits and link clicks.

Send the event data (IP address, full URL, timestamp) to the FPM server in real-time.

📊 Viewing Data

Open the Dashboard in your browser:

http://<server-ip>:6060


View logs in Network Alerts or Traffic Overview sections.

Data is retrieved from Elasticsearch in near real-time.

🛠 Troubleshooting

If the agent fails to connect, ensure:

Server IP and port in proxy_agent.py match the exposed NodePort or port-forward address.

The server and Elasticsearch pods are running:

kubectl get pods


To view server logs:

kubectl logs deployment/fpm-server -f
