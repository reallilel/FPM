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
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------
🔹 الـ Python Scripts (المنطق الأساسي للمشروع):

analyzer.py → مسؤول عن تحليل الـ network logs (فلترة، استخراج أنماط).

correlator.py → بيربط الأحداث مع بعض (مثلاً: packet + user session + timeline).

reporter.py → بيولّد تقارير جاهزة من البيانات (ممكن PDF/HTML/JSON).

server.py → السيرفر المركزي اللي يستقبل البيانات من الـ agents ويخزنها في Elasticsearch.

proxy_agent.py → الكلاينت/الـ agent اللي ينشبك على الأجهزة ويجمع الـ traffic ويرسله مشفر للسيرفر.

dashboard.py → واجهة ويب بسيطة تعرض البيانات (مرتبطة بـ Flask غالبًا).

tk_dashboard.py → الواجهة الرسومية الرئيسية (GUI) باستخدام Tkinter.

timeline_plot.py → مسؤول عن توليد الرسوم الزمنية (timeline visualization) للأحداث.

generate_fake_logs.py → سكربت يولد بيانات وهمية للاختبار والتجارب.

🔹 Docker & Kubernetes (النشر والتشغيل):

Dockerfile → ملف Docker رئيسي لبناء المشروع.

Dockerfile.server → نسخة Docker خاصة بسيرفر الـ FPM.

Dockerfile.agent → نسخة Docker خاصة بالـ agent.

Dockerfile.dashboard → نسخة Docker خاصة بالـ dashboard.

server-deployment.yaml → تعريف Deployment للسيرفر على Kubernetes.

proxy-agent-deployment.yaml → تعريف Deployment للـ agents على Kubernetes.

dashboard-deployment.yaml → تعريف Deployment للـ dashboard.

elasticsearch-deployment.yaml → نشر Elasticsearch داخل الـ cluster.

dashboard-service.yaml → Service لربط الـ dashboard بالـ cluster.

configmap.yaml → ConfigMap يخزن الإعدادات (مثلاً شهادات TLS أو متغيرات بيئة).

🔹 الأمان والشهادات:

server.crt.pem → شهادة TLS (Public).

server.key.pem → المفتاح الخاص (Private Key).

certs/ → مجلد فيه باقي الشهادات أو CA.

secrit.txt → على الأغلب ملف تجريبي/سري (ممكن يكون Password أو Token).

🔹 تشغيل المشروع (Scripts & Tools):

start_fpm.sh → سكربت لتشغيل المشروع (نسخة CLI).

start_fpm_desktop.sh → سكربت مخصص لتشغيل المشروع مع واجهة Tkinter تلقائيًا.

minikube-linux-amd64 → نسخة تنفيذية من Minikube (لتشغيل Kubernetes محلي).

🔹 مجلدات إضافية:

logs/ → يخزن الـ runtime logs.

reports/ → مخرجات التقارير النهائية (PDF, JSON, HTML).

static/ → ملفات ثابتة (CSS/JS/Images) للـ dashboard.

__pycache__/ → ملفات بايثون المترجمة (تُنشأ تلقائيًا).

venv/ → بيئة بايثون الافتراضية.

docker_build_output.log → لوج لعملية بناء Docker.

README.md → توثيق المشروع.

requirements.txt → مكتبات بايثون المطلوبة.

test_context.tar → ممكن يكون أرشيف تجارب/بيئة اختبار محفوظة.
