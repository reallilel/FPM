import requests
import json
import time
import random
from datetime import datetime

SERVER_URL = "https://192.168.49.2:30000/log"  # عدّل إذا اختلف عندك
VERIFY_TLS = False  # اجعلها True إذا كنت تستخدم شهادة موثوقة

SAMPLE_IPS = ["192.168.1.10", "10.0.0.5", "172.16.0.2", "192.168.100.11"]
DEST_IPS = ["8.8.8.8", "10.0.0.20", "192.168.0.1"]
PROTOCOLS = ["TCP", "UDP"]
ACTIONS = ["allow", "deny"]

def generate_entry():
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "src_ip": random.choice(SAMPLE_IPS),
        "dst_ip": random.choice(DEST_IPS),
        "dst_port": random.choice([80, 443, 22, 21, 6666, 31337]),
        "protocol": random.choice(PROTOCOLS),
        "action": random.choice(ACTIONS),
        "byte_count": random.randint(200, 10000),
        "flow_id": f"auto-{random.randint(1000, 9999)}"
    }

def send_entry(entry):
    try:
        response = requests.post(SERVER_URL,
                                 headers={"Content-Type": "application/json"},
                                 data=json.dumps(entry),
                                 verify=VERIFY_TLS)
        if response.status_code == 200:
            print(f"[✓] Sent: {entry['flow_id']}")
        else:
            print(f"[✗] Failed ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    print("🚀 Generating and sending fake logs...")
    for _ in range(10):  # عدّد التكرارات حسب الرغبة
        entry = generate_entry()
        send_entry(entry)
        time.sleep(0.5)  # انتظار نصف ثانية بين الطلبات
