# agents/proxy_agent.py

import ssl
import socket
import json
import platform
from scapy.all import sniff, IP, TCP, UDP
from datetime import datetime

# إعدادات مركز التحكم
# قم بتحديث هذه القيم بناءً على مخرجاتك من 'minikube ip' و 'kubectl get svc fpm-server'
SERVER_HOST = "192.168.49.2"  # ضع هنا IP الخاص بـ Minikube
SERVER_PORT = 30000          # ضع هنا NodePort الخاص بـ FPM Server

# اسم الجهاز الحالي (لتمييز المصدر)
HOSTNAME = platform.node()

# تعريف الدالة التي تلتقط الترافيك
def packet_callback(packet):
    if IP in packet:
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "host": HOSTNAME,
            "src_ip": packet[IP].src,
            "dst_ip": packet[IP].dst,
            "protocol": packet[IP].proto,
        }

        if TCP in packet:
            data["src_port"] = packet[TCP].sport
            data["dst_port"] = packet[TCP].dport
            data["layer"] = "TCP"
        elif UDP in packet:
            data["src_port"] = packet[UDP].sport
            data["dst_port"] = packet[UDP].dport
            data["layer"] = "UDP"
        else:
            data["layer"] = "Other"

        send_data_to_server(data)

# إرسال البيانات إلى مركز التحكم باستخدام TLS
def send_data_to_server(data):
    # استخدام _create_unverified_context لتجاهل التحقق من الشهادة (لبيئة التطوير فقط)
    # في بيئة الإنتاج، يجب استخدام شهادة موثوقة والتحقق منها.
    context = ssl._create_unverified_context()

    try:
        # إنشاء اتصال TCP عادي
        with socket.create_connection((SERVER_HOST, SERVER_PORT)) as sock:
            # تغليف الـ socket باتصال SSL/TLS
            with context.wrap_socket(sock, server_hostname=SERVER_HOST) as ssock:
                # إرسال البيانات بعد تحويلها إلى JSON ثم إلى بايتات
                ssock.sendall(json.dumps(data).encode('utf-8'))
                print(f"[+] Data sent successfully from {HOSTNAME}.", file=sys.stdout)
    except ConnectionRefusedError:
        print(f"[!] Connection refused to {SERVER_HOST}:{SERVER_PORT}. Is the FPM Server running?", file=sys.stderr)
    except Exception as e:
        print(f"[!] Error sending data from {HOSTNAME}: {e}", file=sys.stderr)

# نقطة التشغيل
def start_agent():
    print(f"[*] Starting proxy agent on {HOSTNAME}...", file=sys.stdout)
    print(f"[*] Sending captured data to FPM Server at: {SERVER_HOST}:{SERVER_PORT}", file=sys.stdout)
    try:
        # بدء التقاط حركة المرور
        sniff(prn=packet_callback, store=False)
    except PermissionError:
        print("[!] Permission denied. You might need to run this script with administrator/root privileges (e.g., sudo python3 proxy_agent.py).", file=sys.stderr)
    except Exception as e:
        print(f"[!] An error occurred during sniffing: {e}", file=sys.stderr)

if __name__ == "__main__":
    # تأكد من أن مخرجات stdout و stderr غير مخزنة مؤقتًا
    import sys
    import os
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)
    start_agent()
