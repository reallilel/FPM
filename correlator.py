# correlator.py
import json
import os
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta

ES_HOST = "http://192.168.49.2:32304"
ES_INDEX = "forensic-logs"
LINKED_ALERTS_FILE = "logs/linked_alerts.jsonl"

# اتصل بـ Elasticsearch
es = Elasticsearch(ES_HOST)
if not es.ping():
    print("❌ لا يمكن الاتصال بـ Elasticsearch")
    exit()

# ابحث عن آخر 100 سجل
res = es.search(index=ES_INDEX, body={"query": {"match_all": {}}}, size=100)

# اجمع البيانات
entries = [hit["_source"] for hit in res["hits"]["hits"]]

# قم بالتحليل البسيط
linked_alerts = []
for i, entry in enumerate(entries):
    for j in range(i + 1, len(entries)):
        other = entries[j]
        if (
            entry["src_ip"] == other["src_ip"] and
            abs(datetime.fromisoformat(entry["timestamp"]) - datetime.fromisoformat(other["timestamp"])) <= timedelta(minutes=5)
        ):
            linked_alert = {
                "timestamp": entry["timestamp"],
                "entry": entry,
                "linked_with": other
            }
            linked_alerts.append(linked_alert)

# أنشئ المجلد إن لم يكن موجود
os.makedirs("logs", exist_ok=True)

# احفظ النتائج
with open(LINKED_ALERTS_FILE, "w") as f:
    for alert in linked_alerts:
        f.write(json.dumps(alert) + "\n")

print(f"✅ تم حفظ {len(linked_alerts)} حادث مترابط في {LINKED_ALERTS_FILE}")
