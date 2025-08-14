# server.py
import ssl
import socket
import threading
import json
import os
from datetime import datetime
from elasticsearch import Elasticsearch
import sys
import io

# إعدادات Elasticsearch
es = Elasticsearch("http://elasticsearch:9200")

# إعدادات TLS
CERTFILE = 'certs/server.crt'
KEYFILE = 'certs/server.key'
HOST = '0.0.0.0'
PORT = 8443

LOG_FILE = 'logs/traffic_log.jsonl'
os.makedirs('logs', exist_ok=True)

# تحليل وتسجيل البيانات
def handle_client(connstream, addr):
    json_payload_str = "" # تهيئة المتغير خارج كتلة try
    try:
        print(f"[DEBUG] handle_client started for {addr}", file=sys.stderr)
        raw_data = connstream.recv(8192)
        if not raw_data:
            print(f"[!] No data received from {addr} after SSL handshake. Client likely closed connection.", file=sys.stderr)
            return

        print(f"[DEBUG] Raw data received from {addr}: {raw_data!r}", file=sys.stderr)

        # البحث عن نهاية الرؤوس (سطر فارغ)
        header_end_index = raw_data.find(b'\r\n\r\n')
        
        # Add debug print for header_end_index
        print(f"[DEBUG] header_end_index: {header_end_index}", file=sys.stderr)

        if header_end_index == -1:
            print(f"[!] Invalid HTTP request format from {addr}: No end of headers found.", file=sys.stderr)
            return

        # استخراج الجزء الخاص بالرؤوس والجزء الخاص بالجسم
        headers_part = raw_data[:header_end_index].decode('utf-8')
        json_bytes_payload = raw_data[header_end_index + 4:] # +4 for \r\n\r\n

        # Add debug print for headers_part
        print(f"[DEBUG] Headers part: {headers_part!r}", file=sys.stderr)

        # البحث عن Content-Length في الرؤوس (للتصحيح والتحقق)
        content_length = 0
        for line in headers_part.split('\r\n'):
            if line.lower().startswith('content-length:'):
                try:
                    content_length = int(line.split(':')[1].strip())
                    break
                except ValueError:
                    pass

        print(f"[DEBUG] Content-Length header: {content_length}", file=sys.stderr)
        print(f"[DEBUG] Length of received body part: {len(json_bytes_payload)}", file=sys.stderr)
        print(f"[DEBUG] JSON payload bytes (first 20): {json_bytes_payload[:20]!r}", file=sys.stderr)


        # التأكد من أننا قرأنا كل الجسم (إذا كان Content-Length أكبر من 0)
        if content_length > 0 and len(json_bytes_payload) < content_length:
            # في سيناريو حقيقي، قد تحتاج إلى قراءة المزيد من connstream
            # ولكن لـ curl، عادة ما يرسل كل شيء مرة واحدة
            print(f"[!] Incomplete body received from {addr}. Expected {content_length}, got {len(json_bytes_payload)}.", file=sys.stderr)
            return

        if not json_bytes_payload:
            print(f"[!] No JSON payload found after headers from {addr}.", file=sys.stderr)
            return

        # فك تشفير حمولة JSON وإزالة أي مسافات بيضاء زائدة
        json_payload_str = json_bytes_payload.decode('utf8').strip()
        print(f"[DEBUG] Extracted JSON payload string for parsing (stripped): {json_payload_str!r}", file=sys.stderr)
        print(f"[DEBUG] Length of extracted JSON payload string (stripped): {len(json_payload_str)}", file=sys.stderr)


        # محاولة تحليل JSON
        decoded = json.loads(json_payload_str)

        print(f"[+] Received from {addr}: {decoded}")

        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(decoded) + '\n')

        es.index(
            index="forensic-logs",
            document=decoded,
            refresh=True
        )
        print("[✓] Stored entry in Elasticsearch.")
        client_sock.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK")

    except json.JSONDecodeError as e:
        print(f"[!] JSON decoding error from {addr}: {e} - Payload: {json_payload_str!r}", file=sys.stderr)
    except ssl.SSLError as e:
        print(f"[!] SSL error during client handling for {addr}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[!] General error handling client {addr}: {e}", file=sys.stderr)
    finally:
        if connstream:
            connstream.close()

# بدء الخادم
def start_server():
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
        print(f"[DEBUG] Certificates loaded: {CERTFILE}, {KEYFILE}", file=sys.stderr)
    except FileNotFoundError:
        print(f"[FATAL] Certificate file not found: {CERTFILE} or {KEYFILE}", file=sys.stderr)
        sys.exit(1)
    except ssl.SSLError as e:
        print(f"[FATAL] SSL Certificate or Key error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[FATAL] Unexpected error loading certificates: {e}", file=sys.stderr)
        sys.exit(1)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
        try:
            sock.bind((HOST, PORT))
            print(f"[DEBUG] Socket bound to {HOST}:{PORT}", file=sys.stderr)
        except OSError as e:
            print(f"[FATAL] Failed to bind socket to {HOST}:{PORT}: {e}", file=sys.stderr)
            sys.exit(1)

        sock.listen(5)
        print(f"[*] Forensic Control Center listening on {HOST}:{PORT}...")

        while True:
            client_sock, addr = sock.accept()
            print(f"[DEBUG] Accepted connection from {addr}", file=sys.stderr)
            connstream = None
            try:
                connstream = context.wrap_socket(client_sock, server_side=True)
                print(f"[DEBUG] SSL handshake successful with {addr}", file=sys.stderr)
                threading.Thread(target=handle_client, args=(connstream, addr)).start()
            except ssl.SSLError as e:
                print(f"[!] SSL handshake failed with {addr}: {e}", file=sys.stderr)
                client_sock.close()
            except Exception as e:
                print(f"[!] Unexpected error during SSL handshake with {addr}: {e}", file=sys.stderr)
                client_sock.close()

if __name__ == "__main__":
    start_server()
