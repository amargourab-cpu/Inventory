import customtkinter as ctk
from PIL import Image, ImageTk
import os
import sys
import json
import pandas as pd
import re
import math
from tkinter import filedialog, messagebox

# --- 1. BUNDLING & PATH LOGIC ---
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- 2. SHARED VISUAL STANDARDS & CONFIG ---
TYPE_COLORS = {
    "AT-48": "#006B63", "CT1000": "#E5E1DA", "EP2000": "#4E7C88",
    "EP800": "#D9F28B", "EP2500": "#3BC6EB", "RAD IO-TEMP": "#FFA211",
    "RAD IO-ANA": "#CF3335", "CAN HUB": "#6579e2"
}
APTIV_STATUS_MAP = {
    "In inventory": "#00AC9E", "Employee Use": "#3BC6EB",
    "Demo": "#FFA211", "Deployed": "#6579E2", "Not Deployable": "#F84018"
}

CONFIG_FILE = os.path.expanduser("~/.aptiv_config.txt")

def get_database_path():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            saved_path = f.read().strip()
            if os.path.exists(saved_path): return saved_path
    selected_path = filedialog.askdirectory(title="Select Database Location")
    if selected_path:
        with open(CONFIG_FILE, "w") as f: f.write(selected_path)
        return selected_path
    sys.exit()

DATABASE_PATH = get_database_path()
MOD2_BASE_PATH = os.path.join(DATABASE_PATH, "Customer Owned VDR")
MOD3_BASE_DIR = os.path.join(DATABASE_PATH, "Aptiv Inventory")
MOD3_DATA_FILE = os.path.join(MOD3_BASE_DIR, "inventory_data.json")

# --- 3. APTIV DASHBOARD LOGIC (INTEGRATED FROM DASH.PY) ---
class AptivGauge(ctk.CTkCanvas):
    def __init__(self, master, count, title, **kwargs):
        super().__init__(master, width=140, height=180, bg="#000000", highlightthickness=0, **kwargs)
        color = TYPE_COLORS.get(title.upper(), "#00AC9E")
        cx, cy, r = 70, 70, 50
        self.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#1a1c23", width=8)
        self.create_arc(cx-r, cy-r, cx+r, cy+r, outline=color, width=8, style="arc", start=90, extent=-270)
        self.create_text(cx, cy, text=str(count), fill="white", font=("Impact", 28, "bold"))
        self.create_text(cx, cy+95, text=title, fill="white", font=("Arial", 11, "bold"))

class AptivDashboard(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Aptiv Inventory Analytics")
        self.geometry("1400x900")
        self.configure(fg_color="#000000")
        ctk.CTkLabel(self, text="APTIV INVENTORY DASHBOARD", font=("Impact", 36), text_color="white").pack(pady=20)
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(expand=True, fill="both", padx=20)
        self.refresh()

    def refresh(self):
        # Data aggregation logic from Dash.py
        global_totals = {}
        if os.path.exists(MOD3_DATA_FILE):
            try:
                with open(MOD3_DATA_FILE, 'r') as f:
                    data = json.load(f)
                    for entry in (data if isinstance(data, list) else [data]):
                        v_type = entry.get('type', 'UNKNOWN').upper()
                        global_totals[v_type] = global_totals.get(v_type, 0) + 1
            except: pass
        
        g_cont = ctk.CTkFrame(self.scroll, fg_color="transparent")
        g_cont.pack(fill="x", pady=10)
        for i, (vdr, count) in enumerate(global_totals.items()):
            AptivGauge(g_cont, count, vdr).grid(row=0, column=i, padx=15, pady=20)

# --- 4. CUSTOMER DASHBOARD LOGIC (INTEGRATED FROM CUSTDASH.PY) ---
class GlobalDial(ctk.CTkCanvas):
    def __init__(self, master, model, count, color, **kwargs):
        super().__init__(master, width=150, height=170, bg="#000000", highlightthickness=0, **kwargs)
        cx, cy, r, num_ticks = 75, 75, 55, 40
        for i in range(num_ticks):
            angle = math.radians(i * (360 / num_ticks) + 90)
            is_active = (i / num_ticks) < min((count / 30), 1.0)
            tick_color = color if is_active else "#1a1a1a"
            x1, y1 = cx + (r-8) * math.cos(angle), cy + (r-8) * math.sin(angle)
            x2, y2 = cx + r * math.cos(angle), cy + r * math.sin(angle)
            self.create_line(x1, y1, x2, y2, fill=tick_color, width=3)
        self.create_text(cx, cy, text=str(count), fill="white", font=("Arial", 28, "bold"))
        self.create_text(cx, cy+85, text=model, fill="white", font=("Arial", 12, "bold"))

class CustomerDashboard(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Customer Inventory Dashboard")
        self.geometry("1400x950")
        self.configure(fg_color="#000000")
        ctk.CTkLabel(self, text="TOTAL INVENTORY OVERVIEW", font=("Impact", 30), text_color="white").pack(pady=20)
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=50)
        self.refresh()

    def refresh(self):
        # Data aggregation logic from Custdash.py
        global_counts = {}
        if os.path.exists(MOD2_BASE_PATH):
            for cust in os.listdir(MOD2_BASE_PATH):
                p = os.path.join(MOD2_BASE_PATH, cust, "vdr_data.json")
                if os.path.exists(p):
                    try:
                        with open(p, 'r') as f:
                            data = json.load(f)
                            for entry in (data if isinstance(data, list) else [data]):
                                model = entry.get("vdr", "UNKNOWN").split('-')[0].upper()
                                global_counts[model] = global_counts.get(model, 0) + 1
                    except: pass
        
        colors = ["#00f2a1", "#00d4ff", "#4cc9f0", "#8e44ad", "#f39c12"]
        for i, (m, c) in enumerate(sorted(global_counts.items())):
            GlobalDial(self.top_frame, m, c, colors[i % 5]).pack(side="left", expand=True)

# --- 5. MOD2 & MOD3 CLASSES (EXACT GUI PRESERVED) ---
class CustomerOwnedVDR(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Customer Owned VDR Management")
        self.geometry("1300x850")
        self.configure(fg_color="#1a1a1a")
        ctk.CTkLabel(self, text="Customer Inventory Management", font=("Arial Bold", 32)).pack(pady=20)
        self.table_scroll = ctk.CTkScrollableFrame(self, fg_color="#242424")
        self.table_scroll.pack(fill="both", expand=True, padx=40)
        ctk.CTkButton(self, text="Back to Home", command=lambda: self.destroy()).pack(pady=15)

class AptivInventory(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Aptiv Inventory Management")
        self.geometry("1550x950")
        self.configure(fg_color="#1a1a1a")
        ctk.CTkLabel(self, text="Aptiv Inventory Management", font=("Arial Bold", 28)).pack(pady=15)
        self.table_scroll = ctk.CTkScrollableFrame(self, fg_color="#1a1a1a")
        self.table_scroll.pack(fill="both", expand=True, padx=40)
        ctk.CTkButton(self, text="Back to Home", command=lambda: self.destroy()).pack(pady=20)

# --- 6. MAIN LAUNCHER APP ---
ctk.set_appearance_mode("Dark")

class InventoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aptiv Inventory Management System")
        self.geometry("1100x700") 
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(0, weight=1)
        self.image_path = get_resource_path("Asset/Launchpage.jpg")
        self.bg_image_label = ctk.CTkLabel(self, text=""); self.bg_image_label.grid(row=0, column=0, sticky="nsew")
        self.setup_ui_buttons(); self.bind("<Configure>", self.resizer)

    def resizer(self, event):
        if os.path.exists(self.image_path):
            img = Image.open(self.image_path)
            self.bg_ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(event.width, event.height))
            self.bg_image_label.configure(image=self.bg_ctk_img)

    def setup_ui_buttons(self):
        btn_style = {"width": 320, "height": 55, "font": ("Arial", 17, "bold"), "fg_color": "#2D74BC", "corner_radius": 10}
        ctk.CTkButton(self, text="Show Analytics Dashboard", **btn_style, command=self.open_sel).place(relx=0.05, rely=0.35)
        ctk.CTkButton(self, text="Customer Owned Devices", **btn_style, command=lambda: CustomerOwnedVDR(self)).place(relx=0.05, rely=0.46)
        ctk.CTkButton(self, text="Aptiv Inventory", **btn_style, command=lambda: AptivInventory(self)).place(relx=0.05, rely=0.57)

    def open_sel(self):
        sel = ctk.CTkToplevel(self); sel.geometry("400x250"); sel.attributes("-topmost", True)
        ctk.CTkButton(sel, text="Aptiv Analytics", command=lambda: [sel.destroy(), AptivDashboard(self)]).pack(pady=10)
        ctk.CTkButton(sel, text="Customer Analytics", command=lambda: [sel.destroy(), CustomerDashboard(self)]).pack(pady=10)

if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()