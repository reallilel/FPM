# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from elasticsearch import Elasticsearch
import subprocess
import webbrowser
import threading
import json
import requests
import csv
import io
from datetime import datetime, timedelta
from PIL import ImageTk, Image
from timeline_plot import generate_timeline_plot # This line imports the function from the new timeline_plot.py file

# --- Configuration ---
ES_HOST = "http://192.168.49.2:30574" 
ES_INDEX = "forensic-logs"
LINKED_ALERTS_FILE = "logs/linked_alerts.jsonl"
EXPORT_FOLDER = "reports"
TIMELINE_IMAGE_PATH = "static/timeline.png"
REFRESH_INTERVAL_MS = 5000 # تحديث كل 5 ثوانٍ (5000 ميلي ثانية)

# Ensure necessary directories exist
os.makedirs(EXPORT_FOLDER, exist_ok=True)
os.makedirs("logs", exist_ok=True)
os.makedirs("static", exist_ok=True)

# --- Colors and Fonts (Matching Web Dashboard) ---
BG_COLOR = "#1a1a2e"
CONTAINER_BG = "#22223b"
TEXT_COLOR = "#e0e0e0"
PRIMARY_COLOR = "#00bcd4" # Cyan
SECONDARY_COLOR = "#ff6f61" # Coral
BORDER_COLOR = "#3e3e3e"
TABLE_HEADER_BG = "#2a2a4a"
TABLE_ROW_EVEN = "#252540"
TABLE_ROW_HOVER = "#3a3a5e"
BUTTON_BG = PRIMARY_COLOR
BUTTON_TEXT = "#1a1a2e"
BUTTON_HOVER_BG = "#00a3b8"
ERROR_COLOR = "#ff4d4d"

FONT_FAMILY = "Inter" 
FALLBACK_FONT = "Arial" 

# --- Elasticsearch Client (for Tkinter app to connect directly) ---
es = None
try:
    es = Elasticsearch(ES_HOST)
    if not es.ping():
        print(f"Warning: Could not connect to Elasticsearch at {ES_HOST} from Tkinter app.")
        es = None
    else:
        print(f"Successfully connected to Elasticsearch at {ES_HOST} from Tkinter app.")
except Exception as e:
    print(f"Error initializing Elasticsearch for Tkinter app: {e}")
    es = None

class FPMDashboardGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Forensic Proxy Mesh Dashboard")
        self.root.geometry("1200x700")
        self.root.configure(bg=BG_COLOR)

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame", background=CONTAINER_BG)
        self.style.configure("TLabel", background=CONTAINER_BG, foreground=TEXT_COLOR, font=(FALLBACK_FONT, 10))
        self.style.configure("TButton", background=BUTTON_BG, foreground=BUTTON_TEXT, font=(FALLBACK_FONT, 10, "bold"), borderwidth=0, relief="flat", padding=(10, 5))
        self.style.map("TButton",
                       background=[('active', BUTTON_HOVER_BG)],
                       foreground=[('active', BUTTON_TEXT)])

        self.style.configure("Treeview",
                             background=CONTAINER_BG,
                             foreground=TEXT_COLOR,
                             fieldbackground=CONTAINER_BG,
                             rowheight=28)
        self.style.map("Treeview", background=[('selected', PRIMARY_COLOR)])
        self.style.configure("Treeview.Heading",
                             background=TABLE_HEADER_BG,
                             foreground=PRIMARY_COLOR,
                             font=(FALLBACK_FONT, 10, "bold"),
                             relief="flat")
        self.style.map("Treeview.Heading",
                       background=[('active', TABLE_HEADER_BG)])

        self.create_widgets()
        self.load_alerts()
        self.root.after(REFRESH_INTERVAL_MS, self.auto_refresh) # بدء التحديث التلقائي

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="20 20 20 20", style="TFrame")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        title = ttk.Label(main_frame, text="Network Alerts Dashboard (GUI)", font=(FONT_FAMILY, 24, "bold"), foreground=PRIMARY_COLOR, background=CONTAINER_BG)
        title.pack(pady=(0, 20))

        button_frame = ttk.Frame(main_frame, style="TFrame")
        button_frame.pack(pady=(0, 20))

        buttons_config = [
            ("🏠 Home", lambda: self.load_alerts()),
            ("🔗 Linked Incidents", self.load_linked_incidents),
            ("🕒 Timeline View", self.show_timeline),
            ("📤 Export JSON", lambda: self.export_data(format="json")),
            ("📊 Export CSV", lambda: self.export_data(format="csv")),
            ("⚙️ Generate Test Data", self.generate_test_data),
            ("🔄 Correlate Incidents", self.correlate_incidents),
        ]

        for text, command in buttons_config:
            btn = ttk.Button(button_frame, text=text, command=lambda c=command: threading.Thread(target=c).start(), style="TButton")
            btn.pack(side="left", padx=5, pady=5)

        filter_frame = ttk.Frame(main_frame, style="TFrame")
        filter_frame.pack(pady=(0, 20))

        self.filter_entry = ttk.Entry(filter_frame, width=40, font=(FALLBACK_FONT, 10))
        self.filter_entry.pack(side="left", padx=5)
        self.filter_entry.bind("<Return>", lambda event: self.filter_alerts())

        filter_btn = ttk.Button(filter_frame, text="🔍 Filter", command=self.filter_alerts, style="TButton")
        filter_btn.pack(side="left", padx=5)

        self.status_label = ttk.Label(main_frame, text="Alerts loaded from Elasticsearch.", style="TLabel")
        self.status_label.pack(pady=(0, 10))

        self.tree = ttk.Treeview(main_frame, columns=("timestamp", "src_ip", "dst_ip", "port", "alert_reason"), show="headings")
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("src_ip", text="Source IP")
        self.tree.heading("dst_ip", text="Destination IP")
        self.tree.heading("port", text="Port")
        self.tree.heading("alert_reason", text="Alert Reason")

        self.tree.column("timestamp", width=180, anchor="w")
        self.tree.column("src_ip", width=120, anchor="w")
        self.tree.column("dst_ip", width=120, anchor="w")
        self.tree.column("port", width=80, anchor="center")
        self.tree.column("alert_reason", width=250, anchor="w")

        self.tree.pack(expand=True, fill="both", padx=10, pady=10)

        scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        
    def auto_refresh(self):
        """
        تقوم هذه الدالة بتحديث قائمة التنبيهات تلقائيًا.
        """
        # تجنب التحديث إذا كان هناك فلتر مطبق
        if not self.filter_entry.get().strip():
            self.load_alerts()
        # إعادة جدولة هذه الدالة للتشغيل مرة أخرى بعد فترة زمنية
        self.root.after(REFRESH_INTERVAL_MS, self.auto_refresh)

    def filter_alerts(self):
        user_filter = self.filter_entry.get().strip()
        self.load_alerts(user_filter=user_filter)

    def generate_test_data(self):
        if not es:
            messagebox.showerror("Error", "Elasticsearch is not available.")
            return

        try:
            dummy_data = {
                "timestamp": datetime.now().isoformat() + "Z",
                "src_ip": "192.168.1.100",
                "dst_ip": "10.0.0.1",
                "dst_port": 80,
                "protocol": "HTTP",
                "action": "allow",
                "byte_count": 1500,
                "flow_id": "dummy-flow-" + str(datetime.now().timestamp()),
                "alert_reason": ["Generated Test Data"]
            }
            es.index(index=ES_INDEX, document=dummy_data, refresh=True)
            messagebox.showinfo("Success", "✅ Test data generated successfully.")
            # لا حاجة لـ self.load_alerts() هنا لأن التحديث التلقائي سيتولى الأمر
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate test data:\n{e}")

    def correlate_incidents(self):
        if not es:
            messagebox.showerror("Error", "Elasticsearch is not available.")
            return

        try:
            res = es.search(index=ES_INDEX, body={"query": {"match_all": {}}}, size=100)
            entries = [hit["_source"] for hit in res["hits"]["hits"]]

            linked_alerts = []
            for i, entry in enumerate(entries):
                try:
                    entry_timestamp = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
                except ValueError:
                    print(f"Warning: Invalid timestamp format for entry: {entry.get('timestamp')}")
                    continue

                for j in range(i + 1, len(entries)):
                    other = entries[j]
                    try:
                        other_timestamp = datetime.fromisoformat(other["timestamp"].replace('Z', '+00:00'))
                    except ValueError:
                        print(f"Warning: Invalid timestamp format for other entry: {other.get('timestamp')}")
                        continue

                    if (
                        entry.get("src_ip") == other.get("src_ip") and
                        abs(entry_timestamp - other_timestamp) <= timedelta(minutes=5)
                    ):
                        linked_alert = {
                            "timestamp": datetime.now().isoformat() + "Z",
                            "entry": entry,
                            "linked_with": other,
                            "alert_reason": "Correlated Incident"
                        }
                        linked_alerts.append(linked_alert)
            
            with open(LINKED_ALERTS_FILE, "w") as f:
                for alert in linked_alerts:
                    f.write(json.dumps(alert) + "\n")
            
            messagebox.showinfo("Success", f"✅ {len(linked_alerts)} incidents correlated and saved.")
            self.load_linked_incidents()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to perform correlation:\n{e}")

    def export_data(self, format="json"):
        if not es:
            messagebox.showerror("Error", "Elasticsearch is not available.")
            return

        try:
            res = es.search(index=ES_INDEX, body={"query": {"match_all": {}}}, size=10000)
            data = [hit['_source'] for hit in res['hits']['hits']]

            if format == "json":
                filename = os.path.join(EXPORT_FOLDER, "exported_alerts.json")
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                messagebox.showinfo("Success", f"✅ Data exported successfully to {filename}")
            elif format == "csv":
                filename = os.path.join(EXPORT_FOLDER, "exported_alerts.csv")
                output = io.StringIO()
                writer = csv.writer(output)

                if data:
                    all_keys = set()
                    for doc in data:
                        all_keys.update(doc.keys())
                    header = sorted(list(all_keys))
                    writer.writerow(header)
                
                for row in data:
                    writer.writerow([row.get(key, '') for key in header])
                
                with open(filename, "w", newline='') as f:
                    f.write(output.getvalue())
                messagebox.showinfo("Success", f"✅ Data exported successfully to {filename}")
            else:
                messagebox.showerror("Error", "Invalid export format. Choose 'json' or 'csv'.")
                return

            webbrowser.open(os.path.abspath(EXPORT_FOLDER))
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{e}")

    def show_timeline(self):
        """
        Generates the timeline plot image and displays it in a new Tkinter Toplevel window.
        """
        self.status_label.config(text="Generating timeline plot...", foreground=PRIMARY_COLOR)
        self.root.update_idletasks()

        success = generate_timeline_plot(TIMELINE_IMAGE_PATH) 

        if success:
            try:
                timeline_window = tk.Toplevel(self.root)
                timeline_window.title("Correlated Incident Timeline")
                timeline_window.geometry("1000x700")
                timeline_window.configure(bg=BG_COLOR)

                img = Image.open(TIMELINE_IMAGE_PATH)
                
                max_width = 950
                max_height = 600
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                self.timeline_photo = ImageTk.PhotoImage(img)

                image_label = tk.Label(timeline_window, image=self.timeline_photo, bg=BG_COLOR)
                image_label.pack(padx=10, pady=10, expand=True)

                self.status_label.config(text="Timeline plot displayed.", foreground=TEXT_COLOR)

            except FileNotFoundError:
                messagebox.showerror("Error", f"Timeline image not found at {TIMELINE_IMAGE_PATH}. Please try generating it again.")
                self.status_label.config(text="Timeline image not found.", foreground=ERROR_COLOR)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to display timeline image:\n{e}")
                self.status_label.config(text="Failed to display timeline.", foreground=ERROR_COLOR)
        else:
            messagebox.showwarning("No Data", "Could not generate timeline plot. Ensure data exists and plotting function works.")
            self.status_label.config(text="Timeline generation failed.", foreground=ERROR_COLOR)

    def load_alerts(self, user_filter=None):
        self.tree.delete(*self.tree.get_children())
        self.status_label.config(text="Loading alerts from Elasticsearch...", foreground=TEXT_COLOR)
        self.root.update_idletasks()

        if not es:
            self.status_label.config(text="Elasticsearch not available.", foreground=ERROR_COLOR)
            # تم إزالة مربع الحوار messagebox.showerror() لمنع تكراره عند التحديث التلقائي
            return

        try:
            if not es.indices.exists(index=ES_INDEX):
                self.status_label.config(text="No data found. Generate some test data.", foreground=TEXT_COLOR)
                # تم إزالة مربع الحوار messagebox.showinfo() لمنع تكراره عند التحديث التلقائي
                return

            query = {"match_all": {}}
            if user_filter:
                query = {
                    "multi_match": {
                        "query": user_filter,
                        "fields": ["src_ip", "dst_ip", "timestamp", "alert_reason", "flow_id"]
                    }
                }
            
            res = es.search(index=ES_INDEX, body={"query": query, "size": 100})
            for hit in res['hits']['hits']:
                doc = hit['_source']
                
                # --- هذا هو الجزء المعدّل للتأكد من عرض البيانات بشكل سليم ---
                # استخدام .get() لتجنب أخطاء KeyError إذا كان الحقل غير موجود
                # وتوفير قيمة افتراضية مناسبة
                timestamp = doc.get("timestamp", "N/A")
                src_ip = doc.get("src_ip", "None")
                dst_ip = doc.get("dst_ip", "None")
                dst_port = doc.get("dst_port", "None")

                alert_reason = doc.get("alert_reason", "N/A")
                if isinstance(alert_reason, list) and alert_reason:
                     alert_reason = alert_reason[0]
                elif not alert_reason:
                    alert_reason = "Live Packet"

                self.tree.insert("", "end", values=(
                    timestamp,
                    src_ip,
                    dst_ip,
                    dst_port,
                    alert_reason
                ))
            self.status_label.config(text=f"{len(self.tree.get_children())} alerts loaded from Elasticsearch.", foreground=TEXT_COLOR)

        except requests.exceptions.ConnectionError as e:
            self.status_label.config(text="Connection to Elasticsearch failed.", foreground=ERROR_COLOR)
        except Exception as e:
            self.status_label.config(text=f"Failed to load data: {e}", foreground=ERROR_COLOR)

    def load_linked_incidents(self):
        self.tree.delete(*self.tree.get_children())
        self.status_label.config(text="Loading linked incidents...", foreground=TEXT_COLOR)
        self.root.update_idletasks()

        if not es: 
            self.status_label.config(text="Elasticsearch not available.", foreground=ERROR_COLOR)
            messagebox.showerror("Error", "Elasticsearch connection failed. Cannot load linked incidents.")
            return

        if os.path.exists(LINKED_ALERTS_FILE):
            try:
                with open(LINKED_ALERTS_FILE, 'r') as file:
                    linked_alerts = []
                    for line in file:
                        try:
                            alert = json.loads(line.strip())
                            entry = alert.get("entry", {})
                            linked_alerts.append({
                                "timestamp": alert.get("timestamp"),
                                "src_ip": entry.get("src_ip"),
                                "dst_ip": entry.get("dst_ip"),
                                "dst_port": entry.get("dst_port"),
                                "alert_reason": "🔗 Linked Incident"
                            })
                        except Exception as e:
                            print(f"Error parsing linked alert: {e} - Line: {line.strip()}")
                            continue
                
                for alert in linked_alerts:
                    self.tree.insert("", "end", values=(
                        alert.get("timestamp"),
                        alert.get("src_ip"),
                        alert.get("dst_ip"),
                        alert.get("dst_port"),
                        alert.get("alert_reason")
                    ))
                self.status_label.config(text=f"{len(linked_alerts)} linked incidents loaded.", foreground=TEXT_COLOR)
            except Exception as e:
                self.status_label.config(text=f"Failed to load linked incidents: {e}", foreground=ERROR_COLOR)
                messagebox.showerror("Error", f"Failed to load linked incidents:\n{e}")
        else:
            self.status_label.config(text=f"Warning: {LINKED_ALERTS_FILE} not found.", foreground=ERROR_COLOR)
            messagebox.showwarning("Warning", f"Linked incidents file not found: {LINKED_ALERTS_FILE}\nPlease run 'Correlate Incidents' first.")


if __name__ == '__main__':
    root = tk.Tk()
    app = FPMDashboardGUI(root)
    root.mainloop()
