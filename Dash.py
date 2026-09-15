import math
import customtkinter as ctk
import subprocess
import sys
import os
import re
import json
import threading
from tkinter import filedialog, messagebox

# --- Dynamic Path Configuration ---
CONFIG_FILE = os.path.expanduser("~/.aptiv_config.txt")


def resolve_aptiv_root(path):
    if not path:
        return None
    path = os.path.expanduser(path)
    if os.path.basename(path).strip().lower() == "aptiv inventory" and os.path.exists(path):
        return path
    candidate = os.path.join(path, "Aptiv Inventory")
    if os.path.exists(candidate):
        return candidate
    return None


def get_dynamic_aptiv_path():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            base_path = f.read().strip()
            resolved = resolve_aptiv_root(base_path)
            if resolved:
                return resolved

    selected_path = filedialog.askdirectory(title="Select Aptiv Inventory Root Folder")
    if selected_path:
        resolved = resolve_aptiv_root(selected_path) or selected_path
        with open(CONFIG_FILE, "w") as f:
            f.write(selected_path)
        return resolved

    messagebox.showwarning("Data Path Required", "Aptiv Inventory folder was not selected. Dashboard data may be empty.")
    return ""


APTIV_PATH = None

TYPE_COLORS = {
    "AT-48": "#44d7b6", "CT1000": "#81c8ff", "EP2000": "#6bd5d2",
    "EP800": "#f9d166", "EP2500": "#5ac7ff", "RAD IO-TEMP": "#ffb96b",
    "RAD IO-ANA": "#ff6f6f", "CAN HUB": "#7a81ff"
}

APTIV_STATUS_MAP = {
    "In inventory": "#4fd3c7", "Employee Use": "#5bc4ff", "Demo": "#ffb558",
    "Deployed": "#8f9dff", "Not Deployable": "#ff6f7d", "Saleable": "#00AC9E"
}


HARDWARE_STATUS_COLORS = {
    "OK": "#00AC9E",
    "NOK": "#CF3335"
}

OEM_COLORS = ["#3BC6EB", "#FFA211", "#6579E2", "#00AC9E", "#CF3335", "#8064A2", "#9BBB59", "#4F81BD"]

# --- Data Engine ---
def get_type_color(title):
    return TYPE_COLORS.get(str(title).strip().upper(), "#00B4D8")

def get_aptiv_data():
    global APTIV_PATH
    global_totals, entity_split, stats, oem_cust_map = {}, {}, {"oem": {}, "hw_breakdown": {}}, {}
    oem_package_type_map, oem_package_cust_map = {}, {}
    
    if not APTIV_PATH or not os.path.exists(APTIV_PATH):
        APTIV_PATH = get_dynamic_aptiv_path()
    if not APTIV_PATH or not os.path.exists(APTIV_PATH):
        return global_totals, entity_split, stats, oem_cust_map, oem_package_type_map, oem_package_cust_map
    
    for root, _, files in os.walk(APTIV_PATH):
        for file in files:
            if file.lower() == 'inventory_data.json':
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        data = json.load(f)
                        entries = data if isinstance(data, list) else [data]
                        
                        for entry in entries:
                            v_raw = str(entry.get('type') or "").strip()
                            if not v_raw or v_raw.lower() == "inst type": 
                                continue
                            
                            match = re.match(r"^([a-zA-Z0-9\s-]+)", v_raw)
                            if not match: continue
                            v_type = match.group(1).upper().strip()
                            
                            global_totals[v_type] = global_totals.get(v_type, 0) + 1
                            oem = str(entry.get('oem', 'Aptiv')).strip().upper()
                            cust = str(entry.get('custodian', 'Unassigned')).strip()
                            package = str(entry.get('package') or entry.get('pkg') or entry.get('package_name') or 'Default').strip() or 'Default'
                            st = entry.get('status', 'In inventory')
                            
                            hw_raw = str(entry.get('hw_status') or entry.get('hardware_status') or "OK").strip().upper()
                            hw_status = "OK" if hw_raw == "OK" else "NOK"
                            
                            if oem not in stats["oem"]: stats["oem"][oem] = {}
                            stats["oem"][oem][v_type] = stats["oem"][oem].get(v_type, 0) + 1
                            
                            if v_type not in stats["hw_breakdown"]:
                                stats["hw_breakdown"][v_type] = {"OK": 0, "NOK": 0}
                            stats["hw_breakdown"][v_type][hw_status] += 1

                            if oem not in oem_package_type_map: oem_package_type_map[oem] = {}
                            if package not in oem_package_type_map[oem]: oem_package_type_map[oem][package] = {}
                            oem_package_type_map[oem][package][v_type] = oem_package_type_map[oem][package].get(v_type, 0) + 1

                            if oem not in oem_package_cust_map: oem_package_cust_map[oem] = {}
                            if package not in oem_package_cust_map[oem]: oem_package_cust_map[oem][package] = {}
                            if cust not in oem_package_cust_map[oem][package]: oem_package_cust_map[oem][package][cust] = {}
                            oem_package_cust_map[oem][package][cust][v_type] = oem_package_cust_map[oem][package][cust].get(v_type, 0) + 1

                            if oem not in oem_cust_map: oem_cust_map[oem] = {}
                            if cust not in oem_cust_map[oem]: oem_cust_map[oem][cust] = {}
                            oem_cust_map[oem][cust][v_type] = oem_cust_map[oem][cust].get(v_type, 0) + 1

                            ent = os.path.basename(root) if os.path.basename(root) != "Aptiv Inventory" else "ACS-INDIA"
                            if ent not in entity_split: entity_split[ent] = {}
                            if v_type not in entity_split[ent]: entity_split[ent][v_type] = {s: 0 for s in APTIV_STATUS_MAP}
                            entity_split[ent][v_type][st if st in APTIV_STATUS_MAP else "In inventory"] += 1
                except: 
                    continue
                    
    return global_totals, entity_split, stats, oem_cust_map, oem_package_type_map, oem_package_cust_map

class ColorLegendHorizontal(ctk.CTkFrame):
    def __init__(self, master, color_map, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        for label, color in color_map.items():
            item = ctk.CTkFrame(self, fg_color="transparent")
            item.pack(side="left", padx=15)
            dot = ctk.CTkCanvas(item, width=12, height=12, bg="#091a2a", highlightthickness=0)
            dot.pack(side="left", padx=5)
            dot.create_oval(2, 2, 10, 10, fill=color, outline="")
            ctk.CTkLabel(item, text=label, font=("Arial", 10, "bold"), text_color="#b7c8dc").pack(side="left")

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
        
        # 1. Background Track
        self.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            outline="#1d2a40", width=arc_width, style="arc",
            start=210, extent=-240
        )
        
        # --- DYNAMIC / FIXED SCALE LOGIC ---
        if count <= 300:
            max_scale = 300.0
            step = 30.0
        else:
            raw_step = count / 8.0 
            step = max(10.0, float(math.ceil(raw_step / 10.0) * 10))
            max_scale = step * 10.0
            
        minor_step = step / 5.0
        
        # 2. Outer Tick Marks & Numbers
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
        
        # 3. Hex-Compatible Gradient Arc (Dynamic Fill with Overflow Protection)
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
                self.create_arc(
                    cx - r, cy - r, cx + r, cy + r,
                    outline=color, width=arc_width, style="arc",
                    start=start_angle - i, extent=-2
                )
        
        # 4. Text Overlay
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
        if total == 0:
            total = 1
        num_items = len(items)
        max_h = size_h * 0.55
        base_y = size_h * 0.70

        available_width = size_w * 0.85
        bar_width = min(60, (available_width / num_items) * 0.6) if num_items else 40
        gap = (available_width - (bar_width * num_items)) / (num_items + 1) if num_items else 0
        start_x = size_w * 0.075 + gap

        for i, (label, count) in enumerate(items.items()):
            color = color_map.get(label, get_type_color(label))
            h = (count / total * max_h)
            if count == 0:
                h = 3
            x = start_x + (i * (bar_width + gap))
            
            self.create_rectangle(x, base_y-h, x+bar_width, base_y, fill=color, outline="")
            self.create_oval(x, base_y-h-(bar_width*0.2), x+bar_width, base_y-h+(bar_width*0.2), fill=color, outline="")
            self.create_text(x + (bar_width/2), base_y - h - 25, text=str(count), fill="white", font=("Arial", int(size_h/22), "bold"))
            font_sz = 12
            self.create_text(x + (bar_width/2), base_y + 25, text=label, fill="#ffffff", font=("Helvetica", font_sz, "italic"), width=bar_width + gap, justify="center")

        self.create_text(size_w/2, size_h * 0.90, text=title, fill="#6fd8ff", font=("Impact", int(size_h/15)))

class HorizontalBarChart(ctk.CTkCanvas):
    def __init__(self, master, data, width=420, min_height=520, bar_color="#FFA211", bg="#0b1d2f", **kwargs):
        self.data = {k: v for k, v in data.items() if v is not None}
        self.bar_color = bar_color
        
        self.bar_height = 24
        self.gap = 28  
        self.top_margin = 50
        self.bottom_margin = 40
        
        items_count = len(self.data)
        required_height = self.top_margin + self.bottom_margin + (items_count * (self.bar_height + self.gap))
        actual_height = max(min_height, required_height)
        
        super().__init__(master, width=width, height=actual_height, bg=bg, highlightthickness=0, **kwargs)
        self.draw_chart()

    def draw_chart(self):
        self.delete("all")
        if not self.data:
            self.create_text(self.winfo_reqwidth() / 2, self.winfo_reqheight() / 2,
                             text="No package data available", fill="#cfe0ff",
                             font=("Arial", 14, "bold"), width=360, justify="center")
            return

        items = sorted(self.data.items(), key=lambda x: x[1], reverse=True)
        max_value = max(value for _, value in items) or 1
        
        left_margin = 150 
        right_margin = 40
        y = self.top_margin

        self.create_text(self.winfo_reqwidth() / 2, 24, text="Package-wise VDR Count", fill="#6fd8ff", font=("Impact", 18))
                         
        line_bottom = self.top_margin + len(items) * (self.bar_height + self.gap)
        self.create_line(left_margin, self.top_margin - 10, left_margin, line_bottom, fill="#1f2d3d")

        for label, value in items:
            normalized = value / max_value
            bar_length = max(20, normalized * (self.winfo_reqwidth() - left_margin - right_margin - 20))
            
            self.create_text(12, y + self.bar_height / 2, text=label, anchor="w", fill="#ffffff",
                             font=("Arial", 11, "bold"), width=left_margin - 20)
                             
            self.draw_gradient_bar(left_margin, y, left_margin + bar_length, y + self.bar_height,
                                   start_color="#FFA211", end_color="#F84018")
            
            self.create_text(left_margin + bar_length + 10, y + self.bar_height / 2, text=str(value), anchor="w",
                             fill="#cfe0ff", font=("Arial", 11, "bold"))
            y += self.bar_height + self.gap

    def draw_gradient_bar(self, x1, y1, x2, y2, start_color, end_color, steps=24):
        start_rgb = self.hex_to_rgb(start_color)
        end_rgb = self.hex_to_rgb(end_color)
        width = x2 - x1
        if width <= 0:
            return
        for i in range(steps):
            frac = i / max(steps - 1, 1)
            color = self.rgb_to_hex(self.interpolate_color(start_rgb, end_rgb, frac))
            xa = x1 + (width * i / steps)
            xb = x1 + (width * (i + 1) / steps)
            self.create_rectangle(xa, y1, xb, y2, fill=color, outline="")

    def interpolate_color(self, start_rgb, end_rgb, t):
        return (
            int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * t),
            int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * t),
            int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * t)
        )

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb_tuple):
        return "#%02x%02x%02x" % rgb_tuple

class Dashboard(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Aptiv ACS-India Executive Analytics")
        self.geometry("1500x950")
        self.configure(fg_color="#07131f")
        self.attributes("-topmost", True)
        self._active_drilldown_popup = None
        self._active_enlarge_popup = None
        
        header = ctk.CTkFrame(self, fg_color="#0b1d2e", corner_radius=22)
        header.pack(fill="x", padx=24, pady=20)
        ctk.CTkLabel(header, text="EXECUTIVE INVENTORY OVERVIEW", font=("Impact", 34, "bold"), text_color="#ffffff").pack(pady=24)
        
        self.content_frame = ctk.CTkScrollableFrame(self, fg_color="#081327")
        self.content_frame.pack(expand=True, fill="both", padx=24, pady=(0, 20))
        
        # --- MULTI-THREADED LOADING BAR LOGIC ---
        self.loading_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.loading_frame.pack(pady=100)
        self.loading_label = ctk.CTkLabel(self.loading_frame, text="Aggregating Inventory Data...", font=("Arial", 20, "bold"), text_color="#7f9fc7")
        self.loading_label.pack(pady=(0, 20))
        
        self.progress_bar = ctk.CTkProgressBar(self.loading_frame, width=400, mode="indeterminate", progress_color="#6fd8ff")
        self.progress_bar.pack()
        self.progress_bar.start()
        
        self.fetched_data = None
        
        # Start fetching data in the background
        self.data_thread = threading.Thread(target=self.fetch_data_in_background, daemon=True)
        self.data_thread.start()
        
        # Start checking if the thread is done
        self.check_queue()

    def fetch_data_in_background(self):
        try:
            self.fetched_data = get_aptiv_data()
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

    def show_custodian_drilldown(self, oem):
        data = self.oem_cust_map.get(oem, {})
        self.close_drilldown_popup()
        pop = ctk.CTkToplevel(self)
        pop.geometry("1400x850")
        pop.title(f"Custodian Breakdown: {oem}")
        pop.configure(fg_color="#07131f")
        pop.attributes("-topmost", True)
        self._active_drilldown_popup = pop
        
        ctk.CTkLabel(pop, text=f"CUSTODIAN BREAKDOWN: {oem}", font=("Impact", 32, "bold"), text_color="#6fd8ff").pack(pady=20)
        ctk.CTkButton(pop, text="← BACK", fg_color="#e74c3c", text_color="white", hover_color="#c0392b", font=("Arial", 12, "bold"), command=self.close_drilldown_popup).pack(pady=(0, 10))
        
        scroll = ctk.CTkScrollableFrame(pop, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        for i, (cust, types) in enumerate(data.items()):
            row, col = i // 4, i % 4
            EnhancedMetricCard(scroll, cust, types, on_enlarge=lambda c=cust, d=types: self.show_enlarged_popup(c, d, "bar", TYPE_COLORS)).grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    def show_package_drilldown(self, oem):
        packages = self.oem_package_type_map.get(oem, {})
        if not packages:
            messagebox.showinfo("No Package Data", f"No package data available for {oem}.")
            return

        self.close_drilldown_popup()
        pop = ctk.CTkToplevel(self)
        pop.title(f"Package Breakdown: {oem}")
        pop.geometry("1400x900")
        pop.configure(fg_color="#07131f")
        pop.attributes("-topmost", True)
        self._active_drilldown_popup = pop

        ctk.CTkLabel(pop, text=f"PACKAGE BREAKDOWN: {oem}", font=("Impact", 34, "bold"), text_color="#6fd8ff").pack(pady=20)
        ctk.CTkButton(pop, text="← BACK", fg_color="#e74c3c", text_color="white", hover_color="#c0392b", font=("Arial", 12, "bold"), command=self.close_drilldown_popup).pack(pady=(0, 10))

        content_frame = ctk.CTkFrame(pop, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        left_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True)

        right_frame = ctk.CTkFrame(content_frame, fg_color="#07131f", corner_radius=18, border_width=1, border_color="#1d334c")
        right_frame.pack(side="right", fill="y", padx=(15, 0), pady=0)
        right_frame.pack_propagate(False)
        right_frame.configure(width=420)

        ctk.CTkLabel(right_frame, text="Package Count Overview", font=("Arial Bold", 18), text_color="#ffffff").pack(pady=(20, 10))
        ctk.CTkLabel(right_frame, text="Sorted by total VDR count", font=("Arial", 11), text_color="#a8bfda").pack(pady=(0, 10))

        chart_scroll = ctk.CTkScrollableFrame(right_frame, fg_color="transparent")
        chart_scroll.pack(fill="both", expand=True, padx=5, pady=10)

        package_totals = {package: sum(types.values()) for package, types in packages.items()}
        chart = HorizontalBarChart(chart_scroll, package_totals, width=370, min_height=520, bg="#07131f", bar_color="#FFA211")
        chart.pack(padx=5, pady=5)
        
        def _on_mousewheel(event):
            try:
                chart_scroll._parent_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except: pass
            
        chart.bind("<MouseWheel>", _on_mousewheel)

        scroll = ctk.CTkScrollableFrame(left_frame, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        for i, (package, types) in enumerate(sorted(packages.items(), key=lambda x: -sum(x[1].values()))):
            row, col = i // 3, i % 3
            card = EnhancedMetricCard(scroll, package, types, accent=OEM_COLORS[i % len(OEM_COLORS)], on_enlarge=lambda p=package, t=types: self.show_enlarged_popup(p, t, "bar", TYPE_COLORS))
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            ctk.CTkButton(card, text="VIEW DETAILS ◤", font=("Arial", 10, "bold"), fg_color="transparent", text_color="#cfe0ff", command=lambda p=package, o=oem: self.show_package_custodian_drilldown(o, p)).pack(pady=8)

    def show_package_custodian_drilldown(self, oem, package):
        cust_data = self.oem_package_cust_map.get(oem, {}).get(package, {})
        if not cust_data:
            messagebox.showinfo("No Custodian Data", f"No custodian data available for {package}.")
            return

        self.close_drilldown_popup()
        pop = ctk.CTkToplevel(self)
        pop.title(f"Custodian Breakdown: {package}")
        pop.geometry("1400x900")
        pop.configure(fg_color="#07131f")
        pop.attributes("-topmost", True)
        self._active_drilldown_popup = pop

        ctk.CTkLabel(pop, text=f"CUSTODIAN BREAKDOWN: {package}", font=("Impact", 34, "bold"), text_color="#6fd8ff").pack(pady=20)
        ctk.CTkButton(pop, text="← BACK", fg_color="#e74c3c", text_color="white", hover_color="#c0392b", font=("Arial", 12, "bold"), command=lambda: self.show_package_drilldown(oem)).pack(pady=(0, 10))
        
        scroll = ctk.CTkScrollableFrame(pop, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        for i, (cust, types) in enumerate(sorted(cust_data.items(), key=lambda x: -sum(x[1].values()))):
            row, col = i // 4, i % 4
            EnhancedMetricCard(scroll, cust, types, on_enlarge=lambda c=cust, d=types: self.show_enlarged_popup(c, d, "bar", TYPE_COLORS)).grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    def render_ui(self, g_data, e_data, stats, oem_cust_map, oem_package_type_map, oem_package_cust_map):
        self.oem_cust_map = oem_cust_map
        self.oem_package_type_map = oem_package_type_map
        self.oem_package_cust_map = oem_package_cust_map

        # --- TOTAL ASSETS SECTION ---
        ctk.CTkLabel(self.content_frame, text="TOTAL ASSETS (ACS-INDIA)", font=("Impact", 22), text_color="#cfe0ff").pack(anchor="w", padx=30, pady=(10, 14))
        g_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        g_frame.pack(fill="x", padx=20)
        
        fixed_g_cols = 5
        for col in range(fixed_g_cols):
            g_frame.columnconfigure(col, weight=1)
            
        for i, (vdr, count) in enumerate(g_data.items()):
            card_cont = ctk.CTkFrame(g_frame, fg_color="transparent")
            card_cont.grid(row=i // fixed_g_cols, column=i % fixed_g_cols, padx=6, pady=6, sticky="nsew")
            EnhancedMetricCard(card_cont, vdr, {"Total": count}, accent=get_type_color(vdr), on_enlarge=lambda v=vdr, c=count: self.show_enlarged_popup(v, c, "gauge")).pack(fill="both", expand=True)

        # --- OEM DEPLOYMENT SECTION ---
        ctk.CTkLabel(self.content_frame, text="OEM DEPLOYMENT METRICS", font=("Impact", 22), text_color="#cfe0ff").pack(anchor="w", padx=30, pady=(28, 14))
        o_grid = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        o_grid.pack(fill="x", padx=20)
        
        fixed_oem_cols = 4 
        for col in range(fixed_oem_cols):
            o_grid.columnconfigure(col, weight=1)
            
        for i, (oem, types) in enumerate(stats["oem"].items()):
            clr = OEM_COLORS[i % len(OEM_COLORS)]
            card_cont = ctk.CTkFrame(o_grid, fg_color="transparent")
            card_cont.grid(row=i // fixed_oem_cols, column=i % fixed_oem_cols, padx=6, pady=6, sticky="nsew")
            EnhancedMetricCard(card_cont, oem, types, accent=clr, on_enlarge=lambda o=oem, t=types: self.show_enlarged_popup(o, t, "bar", TYPE_COLORS)).pack(fill="both", expand=True)
            ctk.CTkButton(card_cont, text="VIEW DETAILS ◤", font=("Arial", 10, "bold"), fg_color="transparent", text_color=clr, command=lambda o=oem: self.show_package_drilldown(o)).pack(pady=4)

        # --- HARDWARE HEALTH SECTION ---
        ctk.CTkLabel(self.content_frame, text="HARDWARE HEALTH BY TYPE", font=("Impact", 22), text_color="#cfe0ff").pack(anchor="w", padx=30, pady=(34, 10))
        h_grid = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        h_grid.pack(fill="x", padx=20)
        
        fixed_hw_cols = 5 
        for col in range(fixed_hw_cols):
            h_grid.columnconfigure(col, weight=1)
            
        for i, (v_type, h_data) in enumerate(stats["hw_breakdown"].items()):
            card_cont = ctk.CTkFrame(h_grid, fg_color="transparent")
            card_cont.grid(row=i // fixed_hw_cols, column=i % fixed_hw_cols, padx=6, pady=6, sticky="nsew")
            EnhancedMetricCard(card_cont, v_type, h_data, accent=HARDWARE_STATUS_COLORS.get("OK", "#00AC9E"), on_enlarge=lambda t=v_type, d=h_data: self.show_enlarged_popup(t, d, "bar", HARDWARE_STATUS_COLORS)).pack(fill="both", expand=True)

        # --- ENTITY STATUS SECTION ---
        ctk.CTkLabel(self.content_frame, text="ENTITY STATUS BREAKDOWN", font=("Impact", 22), text_color="#cfe0ff").pack(anchor="w", padx=30, pady=(34, 10))
        for ent, vdr_data in e_data.items():
            cont = ctk.CTkFrame(self.content_frame, fg_color="#091a2a", border_width=1, border_color="#1f3345")
            cont.pack(fill="x", padx=20, pady=10)
            hdr_row = ctk.CTkFrame(cont, fg_color="transparent")
            hdr_row.pack(fill="x", padx=20, pady=12)
            ctk.CTkLabel(hdr_row, text=ent, font=("Arial", 20, "bold"), text_color="#6fd8ff").pack(side="left")
            
            cards = ctk.CTkFrame(cont, fg_color="transparent")
            cards.pack(fill="x", padx=20, pady=(0, 18))
            
            fixed_entity_cols = 5 
            for col in range(fixed_entity_cols):
                cards.columnconfigure(col, weight=1)
                
            for i, (v_type, s_data) in enumerate(vdr_data.items()):
                card_cont = ctk.CTkFrame(cards, fg_color="transparent")
                card_cont.grid(row=i // fixed_entity_cols, column=i % fixed_entity_cols, padx=6, pady=6, sticky="nsew")
                EnhancedMetricCard(card_cont, v_type, s_data, accent=get_type_color(v_type), on_enlarge=lambda t=v_type, d=s_data, e=ent: self.show_enlarged_popup(f"{e} - {t}", d, "bar", APTIV_STATUS_MAP)).pack(fill="both", expand=True)

def show_dashboard(parent):
    return Dashboard(parent)