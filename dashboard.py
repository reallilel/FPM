# dashboard.py (Professional & English Version - HTTP Only - Local ES Host)
from flask import Flask, render_template_string, redirect, url_for, request, send_file
from elasticsearch import Elasticsearch
import json
import os
from datetime import datetime, timedelta
import io
import csv
import sys

# Elasticsearch settings
# عند التشغيل محليًا، يجب استخدام عنوان IP ومنفذ NodePort لـ Elasticsearch في Minikube.
# قم بتغيير هذا العنوان بعد الحصول عليه من 'minikube service elasticsearch --url'
ES_HOST = "http://192.168.49.2:30574" # <-- تم تحديث هذا السطر بالـ IP والمنفذ الصحيحين لديك
ES_INDEX = "forensic-logs"
LINKED_ALERTS_FILE = "logs/linked_alerts.jsonl"

# Initialize Elasticsearch client
es = None
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    es = Elasticsearch(ES_HOST)
    if not es.ping():
        print(f"Warning: Could not connect to Elasticsearch at {ES_HOST}. Ensure Elasticsearch service is running.", file=sys.stderr)
        es = None
    else:
        print(f"Successfully connected to Elasticsearch at {ES_HOST}.", file=sys.stderr)
except Exception as e:
    print(f"Error initializing Elasticsearch: {e}", file=sys.stderr)
    es = None

app = Flask(__name__)

# Ensure logs directory exists for linked_alerts.jsonl
os.makedirs("logs", exist_ok=True)

# Enhanced HTML Template (remains the same as previous professional version)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FPM Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #1a1a2e; /* Dark Blue */
            --text-color: #e0e0e0; /* Light Gray */
            --primary-color: #00bcd4; /* Cyan */
            --secondary-color: #ff6f61; /* Coral */
            --border-color: #3e3e3e;
            --table-header-bg: #2a2a4a; /* Darker Blue */
            --table-row-even: #252540;
            --table-row-hover: #3a3a5e;
            --button-bg: var(--primary-color);
            --button-text: #1a1a2e;
            --button-hover-bg: #00a3b8;
            --error-color: #ff4d4d;
        }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #22223b; /* Slightly lighter dark blue */
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        h1 {
            color: var(--primary-color);
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            font-weight: 700;
        }
        .button-container {
            text-align: center;
            margin-bottom: 30px;
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
        }
        .button-container a, .button-container form button {
            padding: 12px 20px;
            background-color: var(--button-bg);
            color: var(--button-text);
            text-decoration: none;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: background-color 0.3s ease, transform 0.2s ease;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        .button-container a:hover, .button-container form button:hover {
            background-color: var(--button-hover-bg);
            transform: translateY(-2px);
        }
        .button-container form {
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        form input[type="text"] {
            padding: 10px 15px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background-color: #333;
            color: var(--text-color);
            outline: none;
            transition: border-color 0.3s ease;
        }
        form input[type="text"]:focus {
            border-color: var(--primary-color);
        }
        .status {
            text-align: center;
            margin-bottom: 20px;
            font-size: 1em;
            color: var(--text-color);
            background-color: #2a2a4a;
            padding: 10px;
            border-radius: 8px;
        }
        .error-message {
            color: var(--error-color);
            font-weight: bold;
            text-align: center;
            padding: 15px;
            background-color: #3a1a1a;
            border-radius: 8px;
            margin-top: 20px;
        }
        table {
            width: 100%;
            margin: 20px auto;
            border-collapse: separate; /* Use separate to allow border-radius on cells */
            border-spacing: 0; /* Remove space between cell borders */
            border-radius: 8px;
            overflow: hidden; /* Ensures rounded corners are applied */
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        th, td {
            border: 1px solid var(--border-color);
            padding: 15px;
            text-align: left;
        }
        th {
            background-color: var(--table-header-bg);
            font-weight: 700;
            color: var(--primary-color);
            text-transform: uppercase;
            font-size: 0.9em;
        }
        tr:nth-child(even) {
            background-color: var(--table-row-even);
        }
        tr:hover {
            background-color: var(--table-row-hover);
        }
        /* Rounded corners for table */
        th:first-child { border-top-left-radius: 8px; }
        th:last-child { border-top-right-radius: 8px; }
        tr:last-child td:first-child { border-bottom-left-radius: 8px; }
        tr:last-child td:last-child { border-bottom-right-radius: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Network Alerts Dashboard (Web)</h1>
        <div class="button-container">
            <a href="/">🏠 Home</a>
            <a href="/linked">🔗 Linked Incidents</a>
            <a href="/timeline">🕒 Timeline View</a>
            <a href="/export?format=json">📤 Export JSON</a>
            <a href="/export?format=csv">📊 Export CSV</a>
            <form method="get" action="/">
                <input type="text" name="filter" placeholder="IP or Timestamp">
                <button type="submit">🔍 Filter</button>
            </form>
            <form method="post" action="/generate">
                <button type="submit">⚙️ Generate Test Data</button>
            </form>
            <form method="post" action="/correlate">
                <button type="submit">🔄 Correlate Incidents</button>
            </form>
        </div>
        <div class="status">Alerts loaded from Elasticsearch.</div>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Source IP</th>
                    <th>Destination IP</th>
                    <th>Port</th>
                    <th>Alert Reason</th>
                </tr>
            </thead>
            <tbody>
                {% if alerts %}
                    {% for alert in alerts %}
                    <tr>
                        <td>{{ alert.timestamp }}</td>
                        <td>{{ alert.src_ip }}</td>
                        <td>{{ alert.dst_ip }}</td>
                        <td>{{ alert.dst_port }}</td>
                        <td>{{ alert.alert_reason }}</td>
                    </tr>
                    {% endfor %}
                {% else %}
                    <tr><td colspan="5" class="error-message">No alerts to display or an error occurred during loading.</td></tr>
                {% endif %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

# HTML template for the Timeline View using Plotly.js
TIMELINE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Timeline View</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        :root {
            --bg-color: #1a1a2e; /* Dark Blue */
            --text-color: #e0e0e0; /* Light Gray */
            --primary-color: #00bcd4; /* Cyan */
            --secondary-color: #ff6f61; /* Coral */
            --border-color: #3e3e3e;
            --table-header-bg: #2a2a4a; /* Darker Blue */
            --table-row-even: #252540;
            --table-row-hover: #3a3a5e;
            --button-bg: var(--primary-color);
            --button-text: #1a1a2e;
            --button-hover-bg: #00a3b8;
            --error-color: #ff4d4d;
        }
        body { 
            font-family: 'Inter', sans-serif; 
            background-color: var(--bg-color); 
            color: var(--text-color); 
            margin: 0; 
            padding: 20px; 
            line-height: 1.6; 
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px; 
            background-color: #22223b; 
            border-radius: 10px; 
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); 
        }
        h1 { 
            color: var(--primary-color); 
            text-align: center; 
            margin-bottom: 30px; 
            font-size: 2.5em; 
            font-weight: 700; 
        }
        .button-container { 
            text-align: center; 
            margin-bottom: 30px; 
            display: flex; 
            flex-wrap: wrap; 
            justify-content: center; 
            gap: 10px; 
        }
        .button-container a { 
            padding: 12px 20px; 
            background-color: var(--button-bg); 
            color: var(--button-text); 
            text-decoration: none; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-weight: 600; 
            transition: background-color 0.3s ease, transform 0.2s ease; 
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); 
        }
        .button-container a:hover { 
            background-color: var(--button-hover-bg); 
            transform: translateY(-2px); 
        }
        .timeline-content { 
            text-align: center; 
            padding: 50px; 
            font-size: 1.2em; 
            color: #a0a0a0; 
        }
        #timeline-plot {
            border-radius: 8px; /* Apply border-radius to the plot container */
            overflow: hidden; /* Ensure content respects border-radius */
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Security Incidents Timeline</h1>
        <div class="button-container">
            <a href="/">🏠 Home</a>
            <a href="/linked">🔗 Linked Incidents</a>
            <a href="/export?format=json">📤 Export JSON</a>
            <a href="/export?format=csv">📊 Export CSV</a>
        </div>
        <div id="timeline-plot" style="width: 100%; height: 500px; margin: auto;"></div>
        <script>
            // Parse JSON data passed from Flask
            const timestamps = JSON.parse({{ timestamps|tojson }});
            const labels = JSON.parse({{ labels|tojson }});
            const ids = JSON.parse({{ ids|tojson }});

            const data = [{
                x: timestamps,
                y: ids,
                mode: 'markers+text',
                type: 'scatter',
                text: labels,
                textposition: 'top center',
                marker: { 
                    size: 12, 
                    color: 'var(--primary-color)', // Changed marker color to primary-color (Cyan)
                    line: {
                        color: 'var(--primary-color)', // Changed border color to primary-color (Cyan)
                        width: 1
                    }
                },
                textfont: {
                    family: 'Inter, sans-serif',
                    size: 10,
                    color: 'var(--text-color)' // Changed text color to text-color (Light Gray)
                },
                hoverinfo: 'text' // Show only the custom text on hover
            }];

            const layout = {
                title: {
                    text: 'Correlated Incident Timeline',
                    font: {
                        family: 'Inter', sans-serif',
                        size: 20,
                        color: 'var(--primary-color)'
                    }
                },
                plot_bgcolor: '#2a2a4a', /* Match table header background */
                paper_bgcolor: '#22223b', /* Match container background */
                font: { color: 'var(--text-color)', family: 'Inter, sans-serif' },
                xaxis: { 
                    title: 'Time',
                    gridcolor: 'var(--border-color)',
                    linecolor: 'var(--border-color)',
                    zerolinecolor: 'var(--border-color)',
                    tickfont: { color: 'var(--text-color)' },
                    rangeselector: {
                        buttons: [
                            {
                                count: 1,
                                label: '1h',
                                step: 'hour',
                                stepmode: 'backward'
                            },
                            {
                                count: 6,
                                label: '6h',
                                step: 'hour',
                                stepmode: 'backward'
                            },
                            {
                                count: 1,
                                label: '1d',
                                step: 'day',
                                stepmode: 'backward'
                            },
                            {
                                step: 'all'
                            }
                        ]
                    },
                    rangeslider: {visible: true}
                },
                yaxis: { 
                    title: 'Incident ID',
                    gridcolor: 'var(--border-color)',
                    linecolor: 'var(--border-color)',
                    zerolinecolor: 'var(--border-color)',
                    tickfont: { color: 'var(--text-color)' },
                    showticklabels: true, // Show y-axis labels
                    dtick: 1 // Ensure integer ticks for incident IDs
                },
                margin: { l: 50, r: 50, b: 100, t: 80 },
                hovermode: 'closest' // Show hover info for the closest point
            };
            Plotly.newPlot('timeline-plot', data, layout, {responsive: true}); // Make plot responsive
        </script>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    """Renders the main dashboard showing live alerts from Elasticsearch."""
    alerts_data = []
    user_filter = request.args.get("filter", "")
    query = {"match_all": {}}
    if user_filter:
        query = {
            "multi_match": {
                "query": user_filter,
                "fields": ["src_ip", "dst_ip", "timestamp", "alert_reason", "flow_id"] # Added flow_id for filtering
            }
        }

    if es:
        try:
            res = es.search(index=ES_INDEX, body={"query": query, "size": 100})
            for hit in res['hits']['hits']:
                doc = hit['_source']
                alert_reason = "(Live Packet)"
                if "alerts" in doc and doc["alerts"]:
                    alert_reason = doc["alerts"][0]

                alerts_data.append({
                    "timestamp": doc.get("timestamp"),
                    "src_ip": doc.get("src_ip"),
                    "dst_ip": doc.get("dst_ip"),
                    "dst_port": doc.get("dst_port"),
                    "alert_reason": doc.get("alert_reason", alert_reason) # Use existing alert_reason if present
                })
        except Exception as e:
            print(f"Failed to load from Elasticsearch: {e}", file=sys.stderr)
            alerts_data = [{"timestamp": "Error", "src_ip": "", "dst_ip": "", "dst_port": "", "alert_reason": f"Data load failed: {e}"}]
    else:
        alerts_data = [{"timestamp": "Error", "src_ip": "", "dst_ip": "", "dst_port": "", "alert_reason": "Elasticsearch not available"}]

    return render_template_string(HTML_TEMPLATE, alerts=alerts_data)

@app.route('/linked')
def linked_incidents():
    """Renders a dashboard page showing correlated incidents from a local JSONL file."""
    linked_alerts = []
    if os.path.exists(LINKED_ALERTS_FILE):
        with open(LINKED_ALERTS_FILE, 'r') as file:
            for line in file:
                try:
                    alert = json.loads(line.strip())
                    entry = alert.get("entry", {})
                    linked_alerts.append({
                        "timestamp": alert.get("timestamp"),
                        "src_ip": entry.get("src_ip"),
                        "dst_ip": entry.get("dst_ip"),
                        "dst_port": entry.get("dst_port"),
                        "alert_reason": "🔗 Linked Incident" # Keep emoji for visual distinction
                    })
                except Exception as e:
                    print(f"Error parsing linked alert: {e} - Line: {line.strip()}", file=sys.stderr)
                    continue
    else:
        print(f"Warning: {LINKED_ALERTS_FILE} not found.", file=sys.stderr)

    # Use the same HTML template for linked incidents
    return render_template_string(HTML_TEMPLATE, alerts=linked_alerts)

@app.route('/generate', methods=['POST'])
def generate():
    """Generates and indexes dummy network traffic data into Elasticsearch."""
    if es:
        try:
            dummy_data = {
                "timestamp": datetime.now().isoformat(timespec='microseconds') + "Z", # Added microseconds for better timeline granularity
                "src_ip": "192.168.1.100",
                "dst_ip": "10.0.0.1",
                "dst_port": 80,
                "protocol": "HTTP",
                "action": "allow",
                "byte_count": 1500,
                "flow_id": "dummy-flow-" + str(datetime.now().timestamp()),
                "alerts": ["Generated Test Data"]
            }
            es.index(index=ES_INDEX, document=dummy_data, refresh=True)
            print(f"Generated dummy data: {dummy_data}", file=sys.stderr)
        except Exception as e:
            print(f"Failed to generate dummy data: {e}", file=sys.stderr)
    return redirect(url_for('index'))

@app.route('/correlate', methods=['POST'])
def correlate_incidents():
    """
    Correlates incidents based on simple logic (same source IP within 5 minutes)
    and saves them to a local JSONL file.
    """
    if es:
        try:
            # Load latest 100 records from Elasticsearch
            res = es.search(index=ES_INDEX, body={"query": {"match_all": {}}}, size=100)
            entries = [hit["_source"] for hit in res["hits"]["hits"]]

            linked_alerts = []
            # Simple correlation logic: same source IP within 5 minutes
            for i, entry in enumerate(entries):
                try:
                    entry_timestamp = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
                except ValueError:
                    print(f"Warning: Invalid timestamp format for entry: {entry.get('timestamp')}", file=sys.stderr)
                    continue

                for j in range(i + 1, len(entries)):
                    other = entries[j]
                    try:
                        other_timestamp = datetime.fromisoformat(other["timestamp"].replace('Z', '+00:00'))
                    except ValueError:
                        print(f"Warning: Invalid timestamp format for other entry: {other.get('timestamp')}", file=sys.stderr)
                        continue

                    # Correlation condition: same source IP and within 5 minutes
                    if (
                        entry.get("src_ip") == other.get("src_ip") and
                        abs(entry_timestamp - other_timestamp) <= timedelta(minutes=5)
                    ):
                        linked_alert = {
                            "timestamp": datetime.now().isoformat(timespec='microseconds') + "Z", # Timestamp of correlation event
                            "entry": entry,
                            "linked_with": other,
                            "alert_reason": "Correlated Incident" # Add a reason for linked incidents
                        }
                        linked_alerts.append(linked_alert)
            
            # Ensure the logs directory exists
            os.makedirs("logs", exist_ok=True)

            # Save results to linked_alerts.jsonl
            with open(LINKED_ALERTS_FILE, "w") as f:
                for alert in linked_alerts:
                    f.write(json.dumps(alert) + "\n")
            
            print(f"Successfully correlated {len(linked_alerts)} incidents and saved to {LINKED_ALERTS_FILE}", file=sys.stderr)

        except Exception as e:
            print(f"Failed to perform correlation: {e}", file=sys.stderr)
            
    return redirect(url_for('linked_incidents')) # Redirect to the linked incidents page after correlation

@app.route('/timeline')
def timeline():
    """
    Generates data for the timeline plot from Elasticsearch and renders it using Plotly.js.
    """
    timestamps = []
    labels = []
    ids = []
    if es:
        try:
            # Fetch all documents, sorted by timestamp, to ensure correct timeline order
            res = es.search(index=ES_INDEX, body={"query": {"match_all": {}}}, size=10000, sort=[{"timestamp": {"order": "asc"}}])
            for i, hit in enumerate(res['hits']['hits']):
                doc = hit['_source']
                ts = doc.get("timestamp")
                if ts:
                    timestamps.append(ts)
                    # Create a detailed label for each event on the timeline
                    alert_reason = doc.get('alert_reason', '(Live Packet)')
                    # If 'alerts' field exists and is not empty, use the first alert message
                    if "alerts" in doc and doc["alerts"]:
                        alert_reason = doc["alerts"][0]

                    labels.append(f"Src: {doc.get('src_ip', 'N/A')}<br>Dst: {doc.get('dst_ip', 'N/A')}:{doc.get('dst_port', 'N/A')}<br>Alert: {alert_reason}")
                    ids.append(i + 1) # Use 1-based index for better readability on Y-axis
        except Exception as e:
            print(f"Failed to load timeline data from Elasticsearch: {e}", file=sys.stderr)
            # You might want to pass an error message to the template here for display
            
    # Render the timeline template, passing data as JSON strings
    return render_template_string(TIMELINE_TEMPLATE, timestamps=json.dumps(timestamps), labels=json.dumps(labels), ids=json.dumps(ids))

@app.route('/export')
def export():
    """
    Exports all alerts from Elasticsearch to a specified file format (JSON or CSV).
    """
    export_format = request.args.get("format", "json").lower()
    if es:
        try:
            res = es.search(index=ES_INDEX, body={"query": {"match_all": {}}}, size=10000) # Increased size for export
            data = [hit['_source'] for hit in res['hits']['hits']]

            if export_format == "json":
                filename = "exported_alerts.json"
                # Save to a temporary file, then send it
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                return send_file(filename, as_attachment=True, mimetype='application/json')
            elif export_format == "csv":
                filename = "exported_alerts.csv"
                output = io.StringIO() # Create a CSV in memory
                writer = csv.writer(output)

                if data:
                    # Collect all possible keys from all documents for a comprehensive header
                    all_keys = set()
                    for doc in data:
                        all_keys.update(doc.keys())
                    header = sorted(list(all_keys)) # Sort keys for consistent header
                    writer.writerow(header)
                    
                    # Write rows
                    for row in data:
                        writer.writerow([row.get(key, '') for key in header])
                    
                    output.seek(0) # Rewind to the beginning of the stream
                    # Send the in-memory CSV file
                    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), as_attachment=True, mimetype='text/csv', download_name=filename)
            else:
                return "Invalid export format. Choose 'json' or 'csv'.", 400
        except Exception as e:
            print(f"Export failed: {e}", file=sys.stderr)
            return f"Export failed: {e}", 500
    return "No data to export or Elasticsearch not available.", 404

if __name__ == '__main__':
    # Running Flask with HTTP (removed ssl_context for now)
    app.run(host='0.0.0.0', port=6000)
