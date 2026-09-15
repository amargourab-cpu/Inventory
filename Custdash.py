import customtkinter as ctk
import os
import json
import re
import math
import subprocess
import sys
import threading
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

# Unified with Executive Dashboard OEM & Type Accent Colors
MODEL_COLOR_PALETTE = [
    "#3BC6EB", "#FFA211", "#6579E2", "#00AC9E", "#8064A2", "#9BBB59", "#4F81BD", 
    "#44d7b6", "#81c8ff", "#6bd5d2", "#f9d166", "#5ac7ff", "#ffb96b"
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

# --- Executive Visual Components ---
class EnhancedMetricCard(ctk.CTkFrame):
    def __init__(self, master, title, data, accent="#3BC6EB", on_enlarge=None, **kwargs):
        super().__init__(master, fg_color="#162535", corner_radius=12, border_width=1, border_color="#2a3f50", **kwargs)
        ctk.CTkFrame(self, fg_color=accent, height=4).pack(fill="x", side="top")
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(header, text=title.upper(), font=("Arial", 16, "bold"), text_color="#b7c8dc", wraplength=130).pack(side="left")
        if on_enlarge:
            ctk.CTkButton(header, text="◤", width=22, height=22, fg_color="transparent", text_color=accent, hover_color="#2a3f50", command=on_enlarge).pack(side="right")
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=4)
        ctk.CTkLabel(content, text=str(sum(data.values())), font=("Arial", 24, "bold"), text_color="white").pack(anchor="nw")
        breakdown = ctk.CTkFrame(content, fg_color="transparent")
        breakdown.pack(fill="x", pady=(10, 0))
        for v_type, count in data.items():
            ctk.CTkLabel(breakdown, text=f"{v_type}: {count}", font=("Arial", 12, "bold"), text_color="#81c8ff", anchor="w").pack(fill="x", pady=1)

class Gauge(ctk.CTkCanvas):
    def __init__(self, master, count, title, size=140, **kwargs):
        bg_color = kwargs.pop("bg", "#07131f") 
        super().__init__(master, width=size, height=size, bg=bg_color, highlightthickness=0, **kwargs)
        
        cx, cy = size / 2, size / 2
        r = size * 0.28 
        arc_width = max(10, int(size / 12))
        
        self.create_arc(cx - r, cy - r, cx + r, cy + r, outline="#1d2a40", width=arc_width, style="arc", start=210, extent=-240)
        
        if count <= 300:
            max_scale = 300.0
            step = 30.0
        else:
            raw_step = count / 8.0 
            step = max(10.0, float(math.ceil(raw_step / 10.0) * 10))
            max_scale = step * 10.0
            
        minor_step = step / 5.0
        current_val = 0
        
        while current_val <= max_scale + 1e-6:
            fraction = current_val / max_scale
            angle = 210 - (fraction * 240)
            rad = math.radians(angle)
            
            is_major = abs((current_val % step)) < 1e-4 or abs((current_val % step) - step) < 1e-4
            tick_len = size * 0.03 if is_major else size * 0.015
            
            r_inner = r + (arc_width / 2) + (size * 0.015)
            r_outer = r_inner + tick_len
            
            x1 = cx + r_inner * math.cos(rad)
            y1 = cy - r_inner * math.sin(rad)
            x2 = cx + r_outer * math.cos(rad)
            y2 = cy - r_outer * math.sin(rad)
            
            self.create_line(x1, y1, x2, y2, fill="#4a627a", width=2 if is_major else 1)
            
            if is_major:
                r_text = r_outer + (size * 0.05)
                tx = cx + r_text * math.cos(rad)
                ty = cy - r_text * math.sin(rad)
                self.create_text(tx, ty, text=str(int(round(current_val))), fill="#b7c8dc", font=("Arial", max(9, int(size/28)), "bold"))
            
            current_val += minor_step
        
        start_angle = 210
        fill_fraction = min(count / max_scale, 1.0) 
        total_fill_extent = int(-(fill_fraction * 240))
        
        if total_fill_extent == 0 and count > 0:
            total_fill_extent = -1 
            
        steps = abs(total_fill_extent)
        start_rgb = self.hex_to_rgb("#FFA211")
        end_rgb = self.hex_to_rgb("#F84018")
        
        if steps > 0:
            for i in range(steps):
                frac = i / max(steps - 1, 1)
                color = self.rgb_to_hex(self.interpolate_color(start_rgb, end_rgb, frac))
                self.create_arc(cx - r, cy - r, cx + r, cy + r, outline=color, width=arc_width, style="arc", start=start_angle - i, extent=-2)
        
        self.create_text(cx, cy, text=str(count), fill="white", font=("Arial", int(size / 5), "bold"))
        self.create_text(cx, cy + (size * 0.15), text=title, fill="#b7c8dc", font=("Arial", int(size / 14), "bold"))

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb_tuple):
        return "#%02x%02x%02x" % rgb_tuple

    def interpolate_color(self, start_rgb, end_rgb, t):
        return (
            int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * t),
            int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * t),
            int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * t)
        )

class GenericPillBar(ctk.CTkCanvas):
    def __init__(self, master, counts, title, color_map, size_w=170, size_h=200, bg="#091a2a", **kwargs):
        super().__init__(master, width=size_w, height=size_h, bg=bg, highlightthickness=0, **kwargs)
        items = counts or {}
        
        total = max(items.values()) if items else 1
        if total == 0: total = 1
        num_items = len(items)
        max_h = size_h * 0.55
        base_y = size_h * 0.70

        available_width = size_w * 0.85
        bar_width = min(60, (available_width / num_items) * 0.6) if num_items else 40
        gap = (available_width - (bar_width * num_items)) / (num_items + 1) if num_items else 0
        start_x = size_w * 0.075 + gap

        for i, (label, count) in enumerate(items.items()):
            color = color_map.get(label, get_model_color(label))
            h = (count / total * max_h)
            if count == 0: h = 3
            x = start_x + (i * (bar_width + gap))
            
            self.create_rectangle(x, base_y-h, x+bar_width, base_y, fill=color, outline="")
            self.create_oval(x, base_y-h-(bar_width*0.2), x+bar_width, base_y-h+(bar_width*0.2), fill=color, outline="")
            self.create_text(x + (bar_width/2), base_y - h - 25, text=str(count), fill="white", font=("Arial", int(size_h/22), "bold"))
            font_sz = 12
            self.create_text(x + (bar_width/2), base_y + 25, text=label, fill="#ffffff", font=("Helvetica", font_sz, "italic"), width=bar_width + gap, justify="center")

        self.create_text(size_w/2, size_h * 0.90, text=title, fill="#6fd8ff", font=("Impact", int(size_h/15)))


# --- Main Dashboard Classes ---
class DashboardUI:
    def _build_ui(self):
        self.title("Customer Inventory Overview")
        self.geometry("1500x950")
        self.configure(fg_color="#07131f")
        self._active_drilldown_popup = None
        self._active_enlarge_popup = None
        
        header_bar = ctk.CTkFrame(self, fg_color="#0b1d2e", corner_radius=22)
        header_bar.pack(fill="x", padx=24, pady=(20, 10))
        
        ctk.CTkLabel(header_bar, text="CUSTOMER INVENTORY OVERVIEW", font=("Impact", 34, "bold"), text_color="#ffffff").pack(pady=24)
        
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(expand=True, fill="both")
        
        self.loading_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.loading_frame.pack(pady=100)
        self.loading_label = ctk.CTkLabel(self.loading_frame, text="Aggregating Customer Data...", font=("Arial", 20, "bold"), text_color="#7f9fc7")
        self.loading_label.pack(pady=(0, 20))
        
        self.progress_bar = ctk.CTkProgressBar(self.loading_frame, width=400, mode="indeterminate", progress_color="#6fd8ff")
        self.progress_bar.pack()
        self.progress_bar.start()
        
        self.fetched_data = None
        
        self.data_thread = threading.Thread(target=self.fetch_data_in_background, daemon=True)
        self.data_thread.start()
        
        self.check_queue()

    def fetch_data_in_background(self):
        try:
            self.fetched_data = get_detailed_inventory()
        except Exception as e:
            self.fetched_data = e

    def check_queue(self):
        if self.fetched_data is not None:
            self.progress_bar.stop()
            self.loading_frame.destroy()
            
            if isinstance(self.fetched_data, Exception):
                messagebox.showerror("Data Error", f"An error occurred loading the dashboard:\n{self.fetched_data}")
            else:
                self.render_ui(*self.fetched_data)
        else:
            self.after(100, self.check_queue)

    def close_drilldown_popup(self):
        if getattr(self, '_active_drilldown_popup', None) and self._active_drilldown_popup.winfo_exists():
            self._active_drilldown_popup.destroy()
        self._active_drilldown_popup = None

    def close_enlarge_popup(self):
        if getattr(self, '_active_enlarge_popup', None) and self._active_enlarge_popup.winfo_exists():
            self._active_enlarge_popup.destroy()
        self._active_enlarge_popup = None

    def show_enlarged_popup(self, title, data, type_flag="card", color_map=None):
        self.close_enlarge_popup()
        pop = ctk.CTkToplevel(self)
        pop.title(f"Details: {title}")
        pop.geometry("1000x750")
        pop.configure(fg_color="#07131f")
        pop.attributes("-topmost", True)
        
        header_text = f"TOTAL STOCK OF {title}" if type_flag == "gauge" else title
        ctk.CTkLabel(pop, text=header_text, font=("Impact", 34, "bold"), text_color="#6fd8ff").pack(pady=30)
        
        if type_flag == "gauge":
            w = Gauge(pop, data, title, size=550)
            w.pack(expand=True)
        else:
            w = GenericPillBar(pop, data, title, color_map or {}, size_w=950, size_h=500, bg="#07131f")
            w.pack(expand=True, pady=20)
        
        ctk.CTkButton(pop, text="CLOSE VIEW", fg_color="#CF3335", hover_color="#A32426", height=40, font=("Arial", 12, "bold"), command=pop.destroy).pack(pady=30)
        self._active_enlarge_popup = pop

    def show_package_drilldown(self, customer, model, package_data):
        self.close_drilldown_popup()
        pop = ctk.CTkToplevel(self)
        pop.geometry("1400x850")
        pop.title(f"Package Breakdown: {customer} - {model}")
        pop.configure(fg_color="#07131f")
        pop.attributes("-topmost", True)
        self._active_drilldown_popup = pop
        
        ctk.CTkLabel(pop, text=f"PACKAGE BREAKDOWN: {customer} ({model})", font=("Impact", 32, "bold"), text_color="#6fd8ff").pack(pady=20)
        ctk.CTkButton(pop, text="← BACK", fg_color="#e74c3c", text_color="white", hover_color="#c0392b", font=("Arial", 12, "bold"), command=self.close_drilldown_popup).pack(pady=(0, 10))
        
        scroll = ctk.CTkScrollableFrame(pop, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        fixed_cols = 4
        for col in range(fixed_cols):
            scroll.columnconfigure(col, weight=1)
            
        for i, (pkg, stats) in enumerate(package_data.items()):
            row, col = i // fixed_cols, i % fixed_cols
            card_cont = ctk.CTkFrame(scroll, fg_color="transparent")
            card_cont.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            EnhancedMetricCard(card_cont, pkg, stats, accent=get_model_color(model), on_enlarge=lambda p=pkg, s=stats: self.show_enlarged_popup(f"{p}", s, "bar", {"OK": "#00AC9E", "NOK": "#CF3335"})).pack(fill="both", expand=True)

    def render_ui(self, global_counts, customer_data):
        self.summary_scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color="#081327", orientation="horizontal", height=230, corner_radius=22, border_width=1, border_color="#1d3249")
        self.summary_scroll.pack(fill="x", padx=24, pady=(0, 20))
        
        for m, c in sorted(global_counts.items()):
            card_cont = ctk.CTkFrame(self.summary_scroll, fg_color="transparent")
            card_cont.pack(side="left", padx=10, pady=15, fill="y")
            EnhancedMetricCard(card_cont, m, {"Total": c}, accent=get_model_color(m), on_enlarge=lambda v=m, count=c: self.show_enlarged_popup(v, count, "gauge")).pack(fill="both", expand=True)

        ctk.CTkLabel(self.content_frame, text="CUSTOMER WISE DISTRIBUTION", font=("Impact", 22), text_color="#cfe0ff").pack(anchor="w", padx=30, pady=(10, 10))
        
        self.scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color="#081327", corner_radius=22, border_width=1, border_color="#1d3249")
        self.scroll.pack(expand=True, fill="both", padx=24, pady=(0, 20))

        for ent, models in customer_data.items():
            if not models: continue
            cont = ctk.CTkFrame(self.scroll, fg_color="#091a2a", border_width=1, border_color="#1f3345")
            cont.pack(fill="x", padx=20, pady=10)
            
            hdr_row = ctk.CTkFrame(cont, fg_color="transparent")
            hdr_row.pack(fill="x", padx=20, pady=12)
            ctk.CTkLabel(hdr_row, text=ent.upper(), font=("Arial", 20, "bold"), text_color="#6fd8ff").pack(side="left")
            
            cards = ctk.CTkFrame(cont, fg_color="transparent")
            cards.pack(fill="x", padx=20, pady=(0, 18))
            
            fixed_cols = 5 
            for col in range(fixed_cols):
                cards.columnconfigure(col, weight=1)
                
            for i, (m, d) in enumerate(models.items()):
                card_cont = ctk.CTkFrame(cards, fg_color="transparent")
                card_cont.grid(row=i // fixed_cols, column=i % fixed_cols, padx=6, pady=6, sticky="nsew")
                
                display_data = {"OK": d['OK'], "NOK": d['NOK']}
                EnhancedMetricCard(card_cont, m, display_data, accent=get_model_color(m), on_enlarge=lambda t=m, stat=display_data, cust=ent: self.show_enlarged_popup(f"{cust} - {t}", stat, "bar", {"OK": "#00AC9E", "NOK": "#CF3335"})).pack(fill="both", expand=True)
                
                ctk.CTkButton(card_cont, text="VIEW DETAILS ◤", font=("Arial", 10, "bold"), fg_color="transparent", text_color=get_model_color(m), command=lambda c_name=ent, m_name=m, p_data=d['Packages']: self.show_package_drilldown(c_name, m_name, p_data)).pack(pady=4)

class Dashboard(ctk.CTk, DashboardUI):
    def __init__(self):
        super().__init__()
        self._build_ui()

class DashboardWindow(ctk.CTkToplevel, DashboardUI):
    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()

def show_dashboard(parent=None):
    if parent is None:
        app = Dashboard()
        app.mainloop()
        return app
    return DashboardWindow(parent)