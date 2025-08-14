FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ كل الملفات (بما فيها dashboard.py والشهادات)
COPY . .

# تأكد من نسخ الشهادات
COPY certs /app/certs

# فتح المنفذ الذي يعمل عليه Flask داخل الحاوية
EXPOSE 6000

# تشغيل Flask مع دعم TLS
CMD ["python3", "dashboard.py"]
