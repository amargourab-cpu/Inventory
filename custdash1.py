import customtkinter as ctk
import os
import json
import re
import math
import subprocess
import sys
from tkinter import filedialog, messagebox

# --- Dynamic Path Configuration ---
CONFIG_FILE = os.path.expanduser("~/.aptiv_config.txt")

def resolve_customer_vdr_root(path):
    if not path:
        return None
    path = os.path.expanduser(path)
    if os.path.basename(path).strip().lower() == "customer owned vdr" and os.path.exists(path):
        return path
    candidate = os.path.join(path, "Customer Owned VDR")
    if os.path.exists(candidate):
        return candidate
    return None


def get_dynamic_data_path():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            base_path = f.read().strip()
            resolved = resolve_customer_vdr_root(base_path)
            if resolved:
                return resolved

    selected_path = filedialog.askdirectory(title="Select Customer Owned VDR Root Folder")
    if selected_path:
        resolved = resolve_customer_vdr_root(selected_path) or selected_path
        with open(CONFIG_FILE, "w") as f:
            f.write(selected_path)
        return resolved

    messagebox.showwarning("Data Path Required", "Customer Owned VDR folder was not selected. Dashboard data may be empty.")
    return ""


DATA_PATH = None

MODEL_COLOR_PALETTE = [
    "#00f2a1", "#00d4ff", "#4cc9f0", "#8e44ad", "#f39c12", "#fb8b24", "#72efdd", "#ff6d00", "#6d597a", "#2f6690",
    "#00adb5", "#ff5722", "#7c4dff", "#42a5f5", "#c2185b", "#00897b", "#6a1b9a", "#fdd835", "#00acc1", "#d84315"
]
MODEL_COLORS = {}

def get_model_color(model):
    key = str(model).strip().upper()
    if not key: return "#00f2a1"
    if key in MODEL_COLORS: return MODEL_COLORS[key]
    used = set(MODEL_COLORS.values())
    for color in MODEL_COLOR_PALETTE:
        if color not in used:
            MODEL_COLORS[key] = color
            return color
    MODEL_COLORS[key] = MODEL_COLOR_PALETTE[len(MODEL_COLORS) % len(MODEL_COLOR_PALETTE)]
    return MODEL_COLORS[key]

def enable_smooth_scrolling(scroll_frame, orientation="vertical"):
    canvas = getattr(scroll_frame, "_canvas", None)
    if canvas is None: return
    def on_mousewheel(event):
        if hasattr(event, 'delta') and event.delta:
            delta = -1 if event.delta > 0 else 1
        elif getattr(event, 'num', None) == 4: delta = -1
        elif getattr(event, 'num', None) == 5: delta = 1
        else: return
        if orientation == "horizontal": canvas.xview_scroll(delta, "units")
        else: canvas.yview_scroll(delta, "units")
        return "break"
    def on_enter(_):
        scroll_frame.bind_all("<MouseWheel>", on_mousewheel)
        scroll_frame.bind_all("<Button-4>", on_mousewheel)
        scroll_frame.bind_all("<Button-5>", on_mousewheel)
    def on_leave(_):
        scroll_frame.unbind_all("<MouseWheel>")
        scroll_frame.unbind_all("<Button-4>")
        scroll_frame.unbind_all("<Button-5>")
    scroll_frame.bind("<Enter>", on_enter)
    scroll_frame.bind("<Leave>", on_leave)

def get_detailed_inventory():
    global DATA_PATH
    global_counts, customer_data = {}, {}
    if not DATA_PATH or not os.path.exists(DATA_PATH):
        DATA_PATH = get_dynamic_data_path()
    if not DATA_PATH or not os.path.exists(DATA_PATH):
        return global_counts, customer_data
    for customer_name in os.listdir(DATA_PATH):
        customer_path = os.path.join(DATA_PATH, customer_name)
        if not os.path.isdir(customer_path): continue
        customer_data[customer_name] = {}
        for root, dirs, files in os.walk(customer_path):
            for file in files:
                if file.lower() == 'vdr_data.json':
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            items = data if isinstance(data, list) else [data]
                            for entry in items:
                                model, package = "UNKNOWN", entry.get("package", "Default Pkg")
                                for key, val in entry.items():
                                    if key.lower().startswith('vdr'):
                                        match = re.search(r"([a-zA-Z]+\d+)", str(val))
                                        if match: model = match.group(1).upper()
                                if model not in customer_data[customer_name]:
                                    customer_data[customer_name][model] = {'OK': 0, 'NOK': 0, 'Packages': {}}
                                if package not in customer_data[customer_name][model]['Packages']:
                                    customer_data[customer_name][model]['Packages'][package] = {'OK': 0, 'NOK': 0}
                                status = entry.get("status", "OK").upper()
                                stat_key = 'OK' if status == "OK" else 'NOK'
                                customer_data[customer_name][model][stat_key] += 1
                                customer_data[customer_name][model]['Packages'][package][stat_key] += 1
                                global_counts[model] = global_counts.get(model, 0) + 1
                    except Exception as e: print(f"Error: {e}")
    return global_counts, customer_data

class GlobalSegmentedDial(ctk.CTkCanvas):
    def __init__(self, master, model, count, color=None, **kwargs):
        super().__init__(master, width=150, height=170, bg="#081327", highlightthickness=0, **kwargs)
        self.count, self.model = count, model
        self.color = color or get_model_color(model)
        self.draw()

    def draw(self):
        cx, cy, r, num_ticks = 75, 75, 55, 40
        for i in range(num_ticks):
            angle = math.radians(i * (360 / num_ticks) + 90)
            is_active = (i / num_ticks) < min((self.count / 30), 1.0)
            tick_color = self.color if is_active else "#1a1a1a"
            x1, y1 = cx + (r-8) * math.cos(angle), cy + (r-8) * math.sin(angle)
            x2, y2 = cx + r * math.cos(angle), cy + r * math.sin(angle)
            self.create_line(x1, y1, x2, y2, fill=tick_color, width=3)
        self.create_text(cx, cy, text=str(self.count), fill="white", font=("Arial", 28, "bold"))
        self.create_text(cx, cy+85, text=self.model, fill="white", font=("Arial", 12, "bold"))

class SegmentedPillar(ctk.CTkCanvas):
    def __init__(self, master, model, ok, nok, **kwargs):
        super().__init__(master, width=90, height=180, bg="#081327", highlightthickness=0, **kwargs)
        self.ok, self.nok, self.model = ok, nok, model
        self.draw()

    def draw(self):
        w, h, max_seg, seg_h, gap, bar_w = 90, 150, 15, 6, 3, 15
        for i in range(max_seg):
            y_pos = h - (i * (seg_h + gap))
            ok_active = i < self.ok
            self.create_rectangle(15, y_pos-seg_h, 15+bar_w, y_pos, fill="#00f2a1" if ok_active else "#1a1a1a", outline="")
            if ok_active and i == self.ok - 1:
                self.create_text(15 + bar_w/2, y_pos - seg_h - 12, text=str(self.ok), fill="#00f2a1", font=("Arial", 11, "bold"))
            nok_active = i < self.nok
            self.create_rectangle(45, y_pos-seg_h, 45+bar_w, y_pos, fill="#ff4d4d" if nok_active else "#1a1a1a", outline="")
            if nok_active and i == self.nok - 1:
                self.create_text(45 + bar_w/2, y_pos - seg_h - 12, text=str(self.nok), fill="#ff4d4d", font=("Arial", 11, "bold"))
        if self.model: self.create_text(45, h + 20, text=self.model, fill="#8a8da4", font=("Arial", 12, "bold"))

class StackedPillar(ctk.CTkCanvas):
    def __init__(self, master, ok, nok, **kwargs):
        super().__init__(master, width=40, height=140, bg="#081327", highlightthickness=0, **kwargs)
        self.ok, self.nok = ok, nok
        self.draw()

    def draw(self):
        w, h, gap, dash_h, max_seg = 40, 120, 3, 5, 15
        cx, bar_w = w / 2, 20
        for i in range(max_seg):
            y_pos = h - (i * (dash_h + gap))
            if i < self.nok: color = "#ff4d4d"
            elif i < (self.ok + self.nok): color = "#00f2a1"
            else: color = "#1a1a1a"
            self.create_rectangle(cx-bar_w/2, y_pos-dash_h, cx+bar_w/2, y_pos, fill=color, outline="")

class CustomerSection(ctk.CTkFrame):
    def __init__(self, master, name, models):
        super().__init__(master, fg_color="#0c1d2f", border_width=1, border_color="#1e3249", corner_radius=18)
        self.pack(fill="x", padx=20, pady=10)
        self.models = models
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text=name.upper(), font=("Impact", 22), text_color="#ffffff").grid(row=0, column=0, sticky="nw", padx=20, pady=15)
        self.graph_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.graph_frame.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        for m, d in models.items():
            SegmentedPillar(self.graph_frame, m, d['OK'], d['NOK']).pack(side="left", padx=10)
        self.table_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.table_frame.grid(row=1, column=1, padx=40, sticky="e")
        headers = ["VDR TYPE", "OK", "NOK", "TOTAL"]
        for i, head in enumerate(headers):
            ctk.CTkLabel(self.table_frame, text=head, font=("Arial", 11, "bold"), text_color="#8a8da4").grid(row=0, column=i, padx=15)
        for r, (m, d) in enumerate(models.items()):
            lbl = ctk.CTkLabel(self.table_frame, text=m, text_color="white", cursor="hand2", font=("Arial", 12, "bold"))
            lbl.grid(row=r+1, column=0, pady=5)
            lbl.bind("<Button-1>", lambda e, m_name=m: self.open_breakdown(m_name))
            ctk.CTkLabel(self.table_frame, text=str(d['OK']), text_color="#00f2a1", font=("Arial", 12, "bold")).grid(row=r+1, column=1)
            ctk.CTkLabel(self.table_frame, text=str(d['NOK']), text_color="#ff4d4d", font=("Arial", 12, "bold")).grid(row=r+1, column=2)
            ctk.CTkLabel(self.table_frame, text=str(d['OK']+d['NOK']), text_color="white", font=("Arial", 12, "bold")).grid(row=r+1, column=3)

    def open_breakdown(self, m_name):
        pop = ctk.CTkToplevel(self); pop.title(f"Breakdown: {m_name}"); pop.geometry("850x550"); pop.configure(fg_color="#081327"); pop.attributes("-topmost", True)
        ctk.CTkLabel(pop, text=f"PACKAGE BREAKDOWN: {m_name}", font=("Impact", 24), text_color="#8ae3ff").pack(pady=20)
        scroll = ctk.CTkScrollableFrame(pop, fg_color="#07131f", orientation="horizontal", height=220, corner_radius=18, border_width=1, border_color="#1d334c")
        scroll.pack(fill="x", padx=20, pady=(0, 20)); chart_container = ctk.CTkFrame(scroll, fg_color="#081327"); chart_container.pack(side="top", fill="x", pady=10)
        enable_smooth_scrolling(scroll, orientation="horizontal")
        table_scroll = ctk.CTkScrollableFrame(pop, fg_color="#07131f", height=220, corner_radius=18, border_width=1, border_color="#1d334c"); table_scroll.pack(fill="both", expand=True, padx=20)
        enable_smooth_scrolling(table_scroll)
        for p_name, stats in self.models[m_name]['Packages'].items():
            unit = ctk.CTkFrame(chart_container, fg_color="transparent"); unit.pack(side="left", padx=15)
            StackedPillar(unit, stats['OK'], stats['NOK']).pack()
            ctk.CTkLabel(unit, text=p_name, text_color="white", font=("Arial", 9, "bold"), wraplength=80).pack()
        h_f = ctk.CTkFrame(table_scroll, fg_color="transparent"); h_f.pack(fill="x", pady=5)
        ctk.CTkLabel(h_f, text="PACKAGE", text_color="#8a8da4", font=("Arial", 11, "bold"), width=300, anchor="w").pack(side="left")
        ctk.CTkLabel(h_f, text="OK", text_color="#00f2a1", font=("Arial", 11, "bold"), width=60).pack(side="left")
        ctk.CTkLabel(h_f, text="NOK", text_color="#ff4d4d", font=("Arial", 11, "bold"), width=60).pack(side="left")
        for p_name, stats in self.models[m_name]['Packages'].items():
            row = ctk.CTkFrame(table_scroll, fg_color="transparent"); row.pack(fill="x")
            ctk.CTkLabel(row, text=p_name, text_color="white", font=("Arial", 11), width=300, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(stats['OK']), text_color="#00f2a1", font=("Arial", 11, "bold"), width=60).pack(side="left")
            ctk.CTkLabel(row, text=str(stats['NOK']), text_color="#ff4d4d", font=("Arial", 11, "bold"), width=60).pack(side="left")

class DashboardUI:
    def _build_ui(self):
        self.title("Customer Inventory Overview")
        self.geometry("1400x950")
        self.configure(fg_color="#07131f")
        header_bar = ctk.CTkFrame(self, fg_color="#0b1d2f", corner_radius=22, border_width=1, border_color="#1d3249")
        header_bar.pack(fill="x", padx=24, pady=(20, 10))
        ctk.CTkLabel(header_bar, text="CUSTOMER INVENTORY OVERVIEW", font=("Impact", 32), text_color="#ffffff").pack(pady=24)
        subtitle = ctk.CTkLabel(header_bar, text="A polished customer dashboard with consistent graph styling", font=("Arial", 12), text_color="#a8bfda")
        subtitle.pack(pady=(0, 18))
        self.summary_scroll = ctk.CTkScrollableFrame(self, fg_color="#07131f", orientation="horizontal", height=260, corner_radius=22, border_width=1, border_color="#1d3249")
        self.summary_scroll.pack(fill="x", padx=24, pady=(0, 20))
        enable_smooth_scrolling(self.summary_scroll, orientation="horizontal")
        ctk.CTkLabel(self, text="CUSTOMER WISE DISTRIBUTION", font=("Impact", 30), text_color="#ffffff").pack(pady=(10, 10))
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#07131f", corner_radius=22, border_width=1, border_color="#1d3249")
        self.scroll.pack(expand=True, fill="both", padx=24, pady=(0, 20))
        enable_smooth_scrolling(self.scroll)
        self.refresh()

class Dashboard(ctk.CTk, DashboardUI):
    def __init__(self):
        super().__init__()
        self._build_ui()

class DashboardWindow(ctk.CTkToplevel, DashboardUI):
    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()

    def refresh(self):
        for w in self.summary_scroll.winfo_children(): w.destroy()
        for w in self.scroll.winfo_children(): w.destroy()
        globals_d, customers_d = get_detailed_inventory()
        for i, (m, c) in enumerate(sorted(globals_d.items())):
            GlobalSegmentedDial(self.summary_scroll, m, c).grid(row=0, column=i, padx=15, pady=18)
        for customer, models in customers_d.items():
            if models: CustomerSection(self.scroll, customer, models)

def show_dashboard(parent=None):
    if parent is None:
        app = Dashboard()
        app.mainloop()
        return app
    return DashboardWindow(parent)