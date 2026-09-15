import os
import json
import socket
from datetime import datetime

# Logging Configuration
LOG_DIR = '/Users/gourab.palui/Library/CloudStorage/OneDrive-Aptiv/Software/INV logs'

def get_pc_name():
    """Get PC hostname and username"""
    try:
        username = os.getenv('USER', 'Unknown')
        hostname = socket.gethostname()
        return f"{username}@{hostname}"
    except:
        return "Unknown_PC"

def get_timestamp_12hr():
    """Get current timestamp in 12-hour format"""
    return datetime.now().strftime("%m/%d/%Y %I:%M:%S %p")

def ensure_log_dir():
    """Create log directory if it doesn't exist"""
    try:
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create log directory: {e}")

def log_action(action_type, details=""):
    """
    Log user actions to JSON file
    
    Args:
        action_type: Type of action (ADD_VDR, DELETE_VDR, UPDATE_VDR, ADD_ITEM_DB, DELETE_ITEM_DB, 
                                     VIEW_DASHBOARD, OPEN_CUSTOMER_VDR, OPEN_APTIV_INV, EXPORT_EXCEL, etc.)
        details: Additional information about the action (optional)
    """
    try:
        ensure_log_dir()
        
        # Generate log file name based on current date
        log_filename = datetime.now().strftime("INV_Log_%Y_%m_%d.json")
        log_filepath = os.path.join(LOG_DIR, log_filename)
        
        # Create log entry
        log_entry = {
            "pc_name": get_pc_name(),
            "timestamp": get_timestamp_12hr(),
            "action": action_type,
            "details": details
        }
        
        # Load existing logs or create new list
        logs = []
        if os.path.exists(log_filepath):
            try:
                with open(log_filepath, 'r') as f:
                    logs = json.load(f)
                    if not isinstance(logs, list):
                        logs = []
            except:
                logs = []
        
        # Append new entry
        logs.append(log_entry)
        
        # Write updated logs
        with open(log_filepath, 'w') as f:
            json.dump(logs, f, indent=4)
    
    except Exception as e:
        print(f"Error logging action: {e}")
