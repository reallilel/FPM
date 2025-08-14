# timeline_plot.py (English Version with Web Dashboard Aesthetics)

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import json
import os
import sys # Import sys for stderr prints
import pytz # Import pytz for timezone handling

LINKED_ALERTS_FILE = "logs/linked_alerts.jsonl"

def generate_timeline_plot(save_path="static/timeline.png"):
    """
    Generates a timeline plot of correlated incidents and saves it as an image.

    Args:
        save_path (str): The file path to save the generated plot image.
                         Defaults to "static/timeline.png".

    Returns:
        bool: True if the plot was generated successfully, False otherwise.
    """
    # --- Configuration for Plot Aesthetics (Matching Web Dashboard) ---
    DARK_BACKGROUND = "#1a1a2e" # Dark background color
    CONTAINER_BG = "#22223b" # Slightly lighter dark blue for main container
    TEXT_COLOR = "#e0e0e0"     # Light Gray for general text
    PRIMARY_COLOR = "#00bcd4"  # Cyan for primary elements (line, title)
    SECONDARY_COLOR = "#ff6f61" # Coral for markers
    BORDER_COLOR = "#3e3e3e"   # Border/grid color
    ANNOTATION_BG_COLOR = "#2a2a4a" # Darker blue for annotation background

    # --- Timezone Configuration ---
    # Define the target timezone (e.g., 'Asia/Amman' for Jordan)
    TARGET_TIMEZONE = pytz.timezone('Asia/Amman')
    UTC_TIMEZONE = pytz.utc

    timestamps = []
    labels = []

    # --- Data Loading from JSONL File ---
    try:
        if not os.path.exists(LINKED_ALERTS_FILE):
            print(f"[!] Correlated incidents file not found: {LINKED_ALERTS_FILE}", file=sys.stderr)
            return False

        with open(LINKED_ALERTS_FILE, 'r') as file:
            for line in file:
                try:
                    alert = json.loads(line.strip())
                    ts_str = alert.get("timestamp")
                    entry = alert.get("entry", {})
                    
                    if ts_str:
                        # Parse timestamp as UTC, then convert to target timezone
                        try:
                            # First, parse the timestamp string into a datetime object
                            # Assume timestamps are stored in ISO 8601 format, potentially with 'Z' for UTC
                            if ts_str.endswith('Z'):
                                dt_utc = datetime.fromisoformat(ts_str[:-1]).replace(tzinfo=UTC_TIMEZONE)
                            elif '+' in ts_str or '-' in ts_str: # Check for explicit timezone offset
                                dt_utc = datetime.fromisoformat(ts_str)
                            else: # Assume local time if no timezone info, then convert to UTC
                                dt_utc = datetime.fromisoformat(ts_str).replace(tzinfo=UTC_TIMEZONE) # Treat as UTC if no Z or offset
                            
                            # Convert the UTC datetime object to the target local timezone
                            ts_local = dt_utc.astimezone(TARGET_TIMEZONE)
                            timestamps.append(ts_local)
                        except ValueError as ve:
                            print(f"[!] Invalid timestamp format encountered: {ts_str} - {ve}", file=sys.stderr)
                            continue # Skip this entry if timestamp parsing fails
                        
                        # Construct a more informative label
                        alert_reason = alert.get('alert_reason', entry.get('alert_reason', 'N/A'))
                        src_ip = entry.get('src_ip', 'N/A')
                        dst_ip = entry.get('dst_ip', 'N/A')
                        dst_port = entry.get('dst_port', 'N/A')
                        
                        labels.append(f"Src: {src_ip}\nDst: {dst_ip}:{dst_port}\nAlert: {alert_reason}")
                except Exception as e:
                    print(f"[!] Failed to parse line in {LINKED_ALERTS_FILE}: {line.strip()} - {e}", file=sys.stderr)
                    continue
    except Exception as e:
        print(f"❌ Error loading data from {LINKED_ALERTS_FILE}: {e}", file=sys.stderr)
        return False

    # --- Handle No Data Scenario ---
    if not timestamps:
        print("ℹ️ No valid timeline data found to plot. Ensure 'linked_alerts.jsonl' contains correlated alerts.", file=sys.stderr)
        return False

    # --- Ensure Output Directory Exists ---
    output_dir = os.path.dirname(save_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # --- Plotting Configuration ---
    fig, ax = plt.subplots(figsize=(14, 8)) # Create a figure and a set of subplots

    # Set background colors for the figure and axes
    fig.patch.set_facecolor(CONTAINER_BG) # Use CONTAINER_BG for the overall figure background
    ax.set_facecolor(ANNOTATION_BG_COLOR) # Use ANNOTATION_BG_COLOR for the plot area background

    # Plot the timeline data
    # Using a constant Y-value for all points to represent a single timeline
    y_values = [1] * len(timestamps) 
    
    ax.plot_date(timestamps, y_values,
                 linestyle='-',
                 marker='o',
                 color=PRIMARY_COLOR, # Line color (Cyan)
                 markersize=10,
                 markeredgecolor=SECONDARY_COLOR, # Marker edge color (Coral)
                 markerfacecolor=SECONDARY_COLOR, # Marker face color (Coral)
                 linewidth=2)

    # Annotate each data point with its corresponding label
    # Position labels dynamically to avoid overlap
    y_offset_multiplier = 0.1 # Adjust this for vertical spacing between labels
    for i, label in enumerate(labels):
        # Alternate text position slightly above/below the line to reduce overlap
        y_text_pos = y_values[i] + (y_offset_multiplier * (i % 2 == 0 and 1 or -1))
        ax.annotate(label, (timestamps[i], y_text_pos),
                    textcoords="offset points", xytext=(0, 10), # Offset from the point
                    fontsize=9,
                    color=TEXT_COLOR,
                    ha='center', # Horizontal alignment
                    va='bottom' if (i % 2 == 0) else 'top', # Vertical alignment based on alternation
                    rotation=0, # Keep text horizontal for better readability
                    bbox=dict(boxstyle="round,pad=0.3",
                              fc=ANNOTATION_BG_COLOR, # Fill color of the box
                              ec=PRIMARY_COLOR, # Edge color of the box (Cyan)
                              lw=0.5,
                              alpha=0.8)) # Slightly less transparent

    # --- Customize Axes and Labels ---
    # Format x-axis (time) to include full date and time
    # Matplotlib will now correctly display the time in the TARGET_TIMEZONE because the datetime objects are timezone-aware
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S', tz=TARGET_TIMEZONE)) # Specify timezone for formatter
    fig.autofmt_xdate(rotation=45) # Automatically format and rotate date labels

    # Remove y-axis ticks and labels as it's a single timeline
    ax.set_yticks([])
    ax.set_yticklabels([])
    ax.set_ylabel("") # Remove y-axis label

    # Adjust y-limits to give space for annotations
    ax.set_ylim(0.5, 1.5) # Adjust based on y_values and annotation offsets

    # Set plot title and axis labels
    ax.set_title("🔗 Forensic Proxy Mesh: Correlated Incident Timeline",
                 fontsize=18,
                 color=PRIMARY_COLOR, # Title color (Cyan)
                 pad=20)
    ax.set_xlabel("Time", fontsize=12, color=TEXT_COLOR)

    # Configure grid and plot spines (borders)
    ax.grid(True, linestyle='--', alpha=0.3, color=BORDER_COLOR) # Grid color
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER_COLOR) # Set color of the plot borders
    ax.tick_params(axis='x', colors=TEXT_COLOR) # Color of x-axis ticks
    ax.tick_params(axis='y', colors=TEXT_COLOR) # Color of y-axis ticks

    plt.tight_layout() # Adjust layout to prevent labels/elements from overlapping
    
    # --- Save Plot and Clean Up ---
    try:
        plt.savefig(save_path, facecolor=fig.get_facecolor(), bbox_inches='tight') # Save the generated plot
        plt.close(fig) # Close the figure to free up memory
        print(f"[✔] Plot saved to: {save_path}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"❌ Error saving plot to {save_path}: {e}", file=sys.stderr)
        return False

# --- Standalone Test (if script is run directly) ---
if __name__ == '__main__':
    print("Generating timeline plot for standalone test...")
    if generate_timeline_plot("static/test_timeline.png"):
        print("Timeline plot generated successfully at static/test_timeline.png")
    else:
        print("Failed to generate test plot.")
