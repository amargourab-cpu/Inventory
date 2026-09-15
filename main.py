import customtkinter as ctk
from PIL import Image, ImageTk
import os
import sys
import json
import textwrap
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import getpass
from datetime import datetime, timedelta

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

# --- 1. BUNDLING & PATH LOGIC ---
def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            executable_dir = os.path.dirname(sys.executable)
            if os.path.basename(executable_dir) == 'MacOS':
                base_path = os.path.join(os.path.dirname(executable_dir), 'Resources')
            else:
                base_path = executable_dir
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))

    candidate = os.path.join(base_path, relative_path)
    if getattr(sys, 'frozen', False) and not os.path.exists(candidate):
        alt_base = os.path.join(os.path.dirname(base_path), 'Resources')
        alt_candidate = os.path.join(alt_base, relative_path)
        if os.path.exists(alt_candidate):
            return alt_candidate
    return candidate

sys.path.append(get_resource_path("."))

# Safer Imports for Analytics
try:
    from Dash import show_dashboard as show_aptiv_dashboard
except ImportError:
    def show_aptiv_dashboard(parent): messagebox.showerror("Module Error", "Dash.py not found.")

try:
    from Custdash import show_dashboard as show_customer_dashboard
except ImportError:
    def show_customer_dashboard(parent): messagebox.showerror("Module Error", "Custdash.py not found.")

# --- 2. CONFIGURATION & PATHS ---
LAUNCH_PAGE_PATH = get_resource_path("Asset/Launchpage.jpg")
CONFIG_FILE = os.path.expanduser("~/.aptiv_config.txt")

# Activity Logging Configuration
LOG_DIR = "/Users/gourab.palui/Library/CloudStorage/OneDrive-SharedLibraries-Aptiv/ACS-India - Common Folder/Inventory Database/Logs"
LOG_FILE = os.path.join(LOG_DIR, "activity_logs.json")

def get_database_path():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            p = f.read().strip()
            if os.path.exists(p) and p != "": return p
    sel = filedialog.askdirectory(title="Select OneDrive Database Root Folder")
    if sel:
        with open(CONFIG_FILE, "w") as f: f.write(sel)
        return sel
    sys.exit()

DB_ROOT = get_database_path()
MOD2_BASE_PATH = os.path.join(DB_ROOT, "Customer Owned VDR")
MOD3_BASE_DIR = os.path.join(DB_ROOT, "Aptiv Inventory")
MOD3_DATA_FILE = os.path.join(MOD3_BASE_DIR, "inventory_data.json")
MASTER_DB_FILE = os.path.join(DB_ROOT, "master_items.json")
FILTERS_DB_FILE = os.path.join(MOD3_BASE_DIR, "filter_options.json")

# --- 3. ACTIVITY LOGGING SYSTEM ---
def log_activity(window_name, action):
    if not os.path.exists(LOG_DIR):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
        except Exception as e:
            print(f"Failed to create log directory: {e}")
            return
            
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_name": getpass.getuser(),
        "window": window_name,
        "action": action
    }
    
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    logs = json.loads(content)
        except Exception:
            pass
            
    logs.append(log_entry)
    
    # Retention Policy: Delete logs older than 365 days
    one_year_ago = datetime.now() - timedelta(days=365)
    filtered_logs = []
    for log in logs:
        try:
            log_date = datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S")
            if log_date >= one_year_ago:
                filtered_logs.append(log)
        except ValueError:
            filtered_logs.append(log)
            
    try:
        with open(LOG_FILE, "w") as f:
            json.dump(filtered_logs, f, indent=4)
    except Exception as e:
        print(f"Failed to write log: {e}")

def load_saved_filter_options():
    try:
        if os.path.exists(FILTERS_DB_FILE):
            with open(FILTERS_DB_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_filter_option(key, val):
    if not key or not val:
        return
    data = load_saved_filter_options()
    lst = data.get(key, [])
    if val not in lst:
        lst.append(val)
        data[key] = lst
        try:
            with open(FILTERS_DB_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

# --- 4. UI UTILITIES ---
def get_master_instrument_types():
    defaults = ["CT1000", "CT600", "EP2000", "EP800", "EP2500", "RAD IO-temp", "RAD IO- ANA", "AT-48", "CAN HUB"]
    if os.path.exists(MASTER_DB_FILE):
        try:
            with open(MASTER_DB_FILE, "r") as f:
                custom = json.load(f)
                return sorted(list(set(defaults + custom)))
        except: return defaults
    return defaults

def enable_smooth_scrolling(scroll_frame):
    canvas = getattr(scroll_frame, "_canvas", None)
    if not canvas: return
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    scroll_frame.bind("<Enter>", lambda _: scroll_frame.bind_all("<MouseWheel>", _on_mousewheel))
    scroll_frame.bind("<Leave>", lambda _: scroll_frame.unbind_all("<MouseWheel>"))


# --- 5. CUSTOM WIDGETS ---
class MultiSelectDropdown(ctk.CTkFrame):
    def __init__(self, master, title, width=140, command=None, persist_key=None):
        super().__init__(master, width=width, height=30, fg_color="transparent")
        self.pack_propagate(False)
        self.title = title
        self.command = command
        self.persist_key = persist_key
        self.all_options = []
        self.selected_options = set()
        self.is_open = False

        self.main_btn = ctk.CTkButton(self, text=f"All {self.title}", width=width, height=30,
                                      border_width=1, border_color=("#999999", "#333333"),
                                      command=self.toggle_menu)
        self.main_btn.pack(fill="both", expand=True)
        self.menu_window = None

    def configure_options(self, options):
        was_all_selected = len(self.selected_options) == len(self.all_options) and len(self.all_options) > 0
        self.all_options = options
        if was_all_selected or not self.selected_options:
            self.selected_options = set(options)
        else:
            self.selected_options = {opt for opt in self.selected_options if opt in options}
        self.update_btn_text()

    def reset(self):
        self.selected_options = set(self.all_options)
        self.update_btn_text()

    def update_btn_text(self):
        if len(self.selected_options) == len(self.all_options) and self.all_options:
            self.main_btn.configure(text=f"All {self.title}")
        elif len(self.selected_options) == 0:
            self.main_btn.configure(text=f"None Selected")
        elif len(self.selected_options) == 1:
            self.main_btn.configure(text=list(self.selected_options)[0][:12] + "..")
        else:
            self.main_btn.configure(text=f"{len(self.selected_options)} Selected")

    def toggle_menu(self):
        if self.is_open:
            self.close_menu()
        else:
            self.open_menu()

    def open_menu(self):
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()

        self.menu_window = ctk.CTkToplevel(self)
        self.menu_window.geometry(f"{self.winfo_width() + 80}x260+{x}+{y}")
        self.menu_window.overrideredirect(True)
        self.menu_window.attributes("-topmost", True)
        
        scroll = ctk.CTkScrollableFrame(self.menu_window, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=2, pady=2)

        self.all_var = ctk.StringVar(value="on" if len(self.selected_options) == len(self.all_options) else "off")
        cb_all = ctk.CTkCheckBox(scroll, text=f"All {self.title}", variable=self.all_var, onvalue="on", offvalue="off", command=self.toggle_all)
        cb_all.pack(anchor="w", padx=5, pady=5)

        ctk.CTkFrame(scroll, height=2, fg_color=("#cccccc", "#444444")).pack(fill="x", padx=5, pady=2)

        self.item_vars = {}
        for opt in self.all_options:
            var = ctk.StringVar(value="on" if opt in self.selected_options else "off")
            self.item_vars[opt] = var
            cb = ctk.CTkCheckBox(scroll, text=str(opt), variable=var, onvalue="on", offvalue="off", command=lambda o=opt: self.toggle_item(o))
            cb.pack(anchor="w", padx=15, pady=3)

        btn_frame = ctk.CTkFrame(self.menu_window, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=5, padx=5)
        ctk.CTkButton(btn_frame, text="Apply Filter", height=28, fg_color="#2D74BC", hover_color="#215993", command=self.close_menu).pack(fill="x")
        
        self.is_open = True

    def toggle_all(self):
        if self.all_var.get() == "on":
            self.selected_options = set(self.all_options)
            for var in self.item_vars.values(): var.set("on")
        else:
            self.selected_options.clear()
            for var in self.item_vars.values(): var.set("off")

    def toggle_item(self, opt):
        if self.item_vars[opt].get() == "on":
            self.selected_options.add(opt)
        else:
            self.selected_options.discard(opt)

        if len(self.selected_options) == len(self.all_options) and self.all_options:
            self.all_var.set("on")
        else:
            self.all_var.set("off")

    def close_menu(self):
        if self.menu_window:
            self.menu_window.destroy()
            self.menu_window = None
        self.is_open = False
        self.update_btn_text()
        if self.command:
            self.command()

    def get(self):
        return self.selected_options


# --- 6. MODULE CLASSES ---

class CustomerOwnedVDR(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Customer Owned VDR Management")
        self.geometry("1300x850")
        self.data_list = self.load_all_data()
        self.selected_index = None
        self.visible_indices = []
        self.col_pos = {"vdr": 0.125, "package": 0.375, "status": 0.625, "customer": 0.875}
        self.setup_ui()
        self.update_filter_options()
        self.refresh_table()

    def load_all_data(self):
        all_data = []
        if not os.path.exists(MOD2_BASE_PATH): os.makedirs(MOD2_BASE_PATH, exist_ok=True)
        for folder in os.listdir(MOD2_BASE_PATH):
            path = os.path.join(MOD2_BASE_PATH, folder, "vdr_data.json")
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                        if isinstance(data, list): all_data.extend(data)
                except: pass
        return all_data

    def get_customer_folder(self, customer):
        customer_name = str(customer).strip() or "Unknown Customer"
        sanitized = customer_name.replace("/", "_").replace("\\", "_")
        return os.path.join(MOD2_BASE_PATH, sanitized)

    def save_all_data(self):
        if not os.path.exists(MOD2_BASE_PATH):
            os.makedirs(MOD2_BASE_PATH, exist_ok=True)

        grouped = {}
        for item in self.data_list:
            cust = str(item.get("customer", "")).strip() or "Unknown Customer"
            grouped.setdefault(cust, []).append(item)

        for cust, items in grouped.items():
            folder = self.get_customer_folder(cust)
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, "vdr_data.json")
            try:
                with open(path, "w") as f:
                    json.dump(items, f, indent=4)
            except Exception:
                pass

    def change_text_size(self, choice):
        if choice == "Small Text":
            size = 11
            row_h = 30
        elif choice == "Large Text":
            size = 18
            row_h = 48
        else: # Medium Text
            size = 14
            row_h = 38
            
        style = ttk.Style(self)
        style.configure("Cust.Treeview", rowheight=row_h, font=("Helvetica", size, "italic"))
        style.configure("Cust.Treeview.Heading", font=("Helvetica", size + 1, "bold"))
        self.tree.tag_configure("OK", font=("Helvetica", size, "italic"))
        self.tree.tag_configure("NOK", font=("Helvetica", size, "italic"))

    def setup_ui(self):
        ctk.CTkLabel(self, text="Customer Inventory Management", font=("Arial Bold", 32)).pack(pady=(20, 15))
        
        # --- NEW HEADER: Data Entry/Update/Delete ---
        ctk.CTkLabel(self, text="Data Entry/Update/Delete", font=("Arial Bold", 18), text_color="#6579E2").pack(pady=(5, 0))

        input_container = ctk.CTkFrame(self, fg_color="transparent")
        input_container.pack(fill="x", padx=40, pady=5)
        entry_style = {"height": 35}
        
        self.vdr_e = ctk.CTkEntry(input_container, placeholder_text="VDR sl no", width=160, **entry_style)
        self.vdr_e.grid(row=0, column=0, padx=5)
        self.pkg_e = ctk.CTkEntry(input_container, placeholder_text="Package", width=160, **entry_style)
        self.pkg_e.grid(row=0, column=1, padx=5)
        self.st_e = ctk.CTkComboBox(input_container, values=["OK", "NOK"], width=120, height=35)
        self.st_e.grid(row=0, column=2, padx=5)
        self.cust_e = ctk.CTkEntry(input_container, placeholder_text="Customer Name", width=160, **entry_style)
        self.cust_e.grid(row=0, column=3, padx=5)
        
        ctk.CTkButton(input_container, text="Add", width=85, height=35, fg_color="#2D74BC", command=self.add_item).grid(row=0, column=4, padx=5)
        ctk.CTkButton(input_container, text="Edit", width=85, height=35, fg_color="#E67E22", command=self.update_item).grid(row=0, column=5, padx=5)
        ctk.CTkButton(input_container, text="Delete", width=85, height=35, fg_color="#CF3335", command=self.delete_item).grid(row=0, column=6, padx=5)
        ctk.CTkButton(input_container, text="Clear", width=85, height=35, fg_color=("#999999", "#555555"), command=self.clear_fields).grid(row=0, column=7, padx=5)
        
        # --- NEW HEADER: Filters ---
        ctk.CTkLabel(self, text="Filters", font=("Arial Bold", 18), text_color="#6579E2").pack(pady=(15, 0))

        filter_container = ctk.CTkFrame(self, fg_color="transparent")
        filter_container.pack(fill="x", padx=40, pady=10)
        
        self.search_e = ctk.CTkEntry(filter_container, placeholder_text="🔍 Search Serial...", width=240, height=35)
        self.search_e.grid(row=0, column=0, padx=(0, 10))
        self.search_e.bind("<KeyRelease>", lambda e: self.refresh_table())
        
        self.pkg_filter = MultiSelectDropdown(filter_container, title="Package", width=180, command=self.refresh_table)
        self.pkg_filter.grid(row=0, column=1, padx=5)
        
        self.st_filter = MultiSelectDropdown(filter_container, title="Status", width=140, command=self.refresh_table)
        self.st_filter.grid(row=0, column=2, padx=5)
        
        self.cust_filter = MultiSelectDropdown(filter_container, title="Customer", width=180, command=self.refresh_table)
        self.cust_filter.grid(row=0, column=3, padx=5)
        
        ctk.CTkButton(filter_container, text="📊 Export Excel", fg_color="#218c53", width=140, height=35, command=self.export_excel).grid(row=0, column=4, padx=(120, 10))
        
        # Font size adjustment menu
        self.font_menu = ctk.CTkOptionMenu(filter_container, values=["Small Text", "Medium Text", "Large Text"], width=130, height=35, command=self.change_text_size)
        self.font_menu.set("Medium Text")
        self.font_menu.grid(row=0, column=5, padx=5)
        
        content_container = ctk.CTkFrame(self, fg_color="transparent")
        content_container.pack(fill="both", expand=True, padx=40)
        
        table_container = ctk.CTkFrame(content_container, fg_color="transparent")
        table_container.pack(fill="both", expand=True)
        
        mode = ctk.get_appearance_mode().lower()
        bg_col = "#ffffff" if "light" in mode else "#1a1a1a"
        fg_col = "#000000" if "light" in mode else "#e1e1e1"
        hd_bg = "#e2e8f0" if "light" in mode else "#2d3748"
        hd_fg = "#1a202c" if "light" in mode else "#dbe7ff"

        style = ttk.Style(self)
        style.configure("Cust.Treeview", rowheight=38, font=("Helvetica", 14, "italic"), foreground=fg_col, background=bg_col, fieldbackground=bg_col)
        style.configure("Cust.Treeview.Heading", font=("Helvetica", 15, "bold"), background=hd_bg, foreground=hd_fg)
        
        self.tree = ttk.Treeview(table_container, columns=["vdr", "package", "status", "customer"], show="headings", selectmode="browse", style="Cust.Treeview")
        self.tree.heading("vdr", text="VDR sl no")
        self.tree.heading("package", text="Package")
        self.tree.heading("status", text="VDR Status")
        self.tree.heading("customer", text="Customer Name")
        
        self.tree.column("vdr", width=220, anchor="center")
        self.tree.column("package", width=220, anchor="center")
        self.tree.column("status", width=140, anchor="center")
        self.tree.column("customer", width=220, anchor="center")
        
        self.tree.tag_configure("OK", foreground="#276749" if "light" in mode else "#38A169", font=("Helvetica", 14, "italic"))
        self.tree.tag_configure("NOK", foreground="#9b2c2c" if "light" in mode else "#E53E3E", font=("Helvetica", 14, "italic"))
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        self.tree_scroll = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree_scroll.pack(side="right", fill="y")

        ctk.CTkButton(self, text="Close View", width=150, height=35, fg_color="#2D74BC", command=self.destroy).pack(pady=15)

    def export_excel(self):
        if not self.data_list: return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if path: pd.DataFrame(self.data_list).to_excel(path, index=False); messagebox.showinfo("Success", "Exported Successfully")

    def update_filter_options(self):
        pkgs = sorted(list(set(str(i.get("package", "")) for i in self.data_list if i.get("package"))))
        sts = sorted(list(set(str(i.get("status", "")) for i in self.data_list if i.get("status"))))
        custs = sorted(list(set(str(i.get("customer", "")) for i in self.data_list if i.get("customer"))))
        
        self.pkg_filter.configure_options(pkgs)
        self.st_filter.configure_options(sts)
        self.cust_filter.configure_options(custs)

    def select_row(self, index):
        self.selected_index = index
        item = self.data_list[index]
        self.vdr_e.delete(0, 'end'); self.vdr_e.insert(0, str(item["vdr"]))
        self.pkg_e.delete(0, 'end'); self.pkg_e.insert(0, str(item.get("package", "")))
        self.st_e.set(item["status"])
        self.cust_e.delete(0, 'end'); self.cust_e.insert(0, str(item.get("customer", "")))

    def on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        visible_index = self.tree.index(selection[0])
        if visible_index < len(self.visible_indices):
            self.select_row(self.visible_indices[visible_index])

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        self.visible_indices = []
        search_q = self.search_e.get().lower()
        
        sel_pkgs = self.pkg_filter.get()
        sel_sts = self.st_filter.get()
        sel_custs = self.cust_filter.get()

        for index, item in enumerate(self.data_list):
            if search_q and search_q not in str(item["vdr"]).lower():
                continue
            
            pkg = str(item.get("package", ""))
            if len(sel_pkgs) < len(self.pkg_filter.all_options) and pkg not in sel_pkgs:
                continue
            
            st = str(item.get("status", ""))
            if len(sel_sts) < len(self.st_filter.all_options) and st not in sel_sts:
                continue
                
            cust = str(item.get("customer", ""))
            if len(sel_custs) < len(self.cust_filter.all_options) and cust not in sel_custs:
                continue

            status_tag = str(item["status"]).strip().upper()
            self.tree.insert("", "end", values=(item["vdr"], item.get("package", ""), item["status"], item.get("customer", "")), tags=(status_tag,))
            self.visible_indices.append(index)

    def add_item(self):
        new = {"vdr": self.vdr_e.get().strip(), "package": self.pkg_e.get().strip(), "status": self.st_e.get().strip(), "customer": self.cust_e.get().strip()}
        if not new["vdr"] or not new["customer"]:
            messagebox.showwarning("Missing Data", "Please enter both VDR sl no and Customer Name.")
            return
        self.data_list.append(new)
        self.save_all_data()
        self.update_filter_options()
        self.clear_fields()
        log_activity("Customer Owned VDR", f"Added VDR sl no: {new['vdr']}")

    def update_item(self):
        if self.selected_index is not None:
            updated_vdr = self.vdr_e.get().strip()
            self.data_list[self.selected_index] = {"vdr": updated_vdr, "package": self.pkg_e.get().strip(), "status": self.st_e.get().strip(), "customer": self.cust_e.get().strip()}
            self.save_all_data()
            self.update_filter_options()
            self.clear_fields()
            log_activity("Customer Owned VDR", f"Updated VDR sl no: {updated_vdr}")

    def delete_item(self):
        if self.selected_index is not None:
            deleted_vdr = self.data_list[self.selected_index].get("vdr", "Unknown")
            self.data_list.pop(self.selected_index)
            self.selected_index = None
            self.save_all_data()
            self.update_filter_options()
            self.clear_fields()
            log_activity("Customer Owned VDR", f"Deleted VDR sl no: {deleted_vdr}")

    def clear_fields(self):
        self.vdr_e.delete(0, 'end')
        self.pkg_e.delete(0, 'end')
        self.st_e.set("")
        self.cust_e.delete(0, 'end')
        self.selected_index = None
        self.refresh_table()


class AptivInventory(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Aptiv Inventory Management"); self.geometry("1550x950")
        self.col_keys = ["type", "vdr", "status", "oem", "custodian", "package", "hw_status", "remarks"]
        self.col_pos = {"sl": 0.04, "type": 0.12, "vdr": 0.24, "status": 0.36, "oem": 0.48, "custodian": 0.62, "package": 0.70, "hw_status": 0.79, "remarks": 0.90}
        self.data_list = self.load_data(); self.filters = {}; self.selected_index = None
        self.current_child_popup = None
        self.setup_ui()
        self.after(100, self.refresh_table)

    def close_current_child_popup(self):
        if getattr(self, "current_child_popup", None) and self.current_child_popup.winfo_exists():
            try:
                self.current_child_popup.destroy()
            except Exception:
                pass
        self.current_child_popup = None

    def _clear_child_popup_reference(self, popup):
        if getattr(self, "current_child_popup", None) is popup:
            self.current_child_popup = None
        popup.destroy()

    def load_data(self):
        if os.path.exists(MOD3_DATA_FILE):
            try:
                if os.path.getsize(MOD3_DATA_FILE) == 0:
                    return []
                with open(MOD3_DATA_FILE, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def change_text_size(self, choice):
        if choice == "Small Text":
            size = 11
            row_h = 30
        elif choice == "Large Text":
            size = 18
            row_h = 48
        else: # Medium Text
            size = 14
            row_h = 38
            
        style = ttk.Style(self)
        style.configure("Aptiv.Treeview", rowheight=row_h, font=("Helvetica", size, "italic"))
        style.configure("Aptiv.Treeview.Heading", font=("Helvetica", size + 1, "bold"))
        self.tree.tag_configure("OK", font=("Helvetica", size, "italic"))
        self.tree.tag_configure("NOK", font=("Helvetica", size, "italic"))

    def setup_ui(self):
        ctk.CTkLabel(self, text="Aptiv Inventory Management", font=("Arial Bold", 24)).pack(pady=(10, 5))
        top_btn_f = ctk.CTkFrame(self, fg_color="transparent"); top_btn_f.pack(fill="x", padx=40)
        ctk.CTkButton(top_btn_f, text="+ Add Item to DB", fg_color="#8e44ad", width=160, command=self.open_master_item_manager).pack(side="left")
        self.sync_status = ctk.CTkLabel(top_btn_f, text="", text_color="#f1c40f", font=("Arial", 12), fg_color="transparent")
        self.sync_status.pack(side="right", padx=10)
        
        # --- Filters Header & Container ---
        ctk.CTkLabel(self, text="Filters", font=("Arial Bold", 18), text_color="#6579E2").pack(pady=(15, 0))

        f_container = ctk.CTkFrame(self, corner_radius=12, border_width=1); f_container.pack(fill="x", padx=40, pady=5)
        
        top_row = ctk.CTkFrame(f_container, fg_color="transparent")
        top_row.pack(fill="x", padx=5, pady=5)
        
        search_frame = ctk.CTkFrame(top_row, fg_color="transparent")
        search_frame.pack(side="left", padx=5, pady=5)
        self.search_btn = ctk.CTkButton(search_frame, text="🔎", width=36, height=30, fg_color=("#cccccc", "#2b2b2b"), command=self.refresh_table)
        self.search_btn.pack(side="left", padx=(0,6))
        self.global_search = ctk.CTkEntry(search_frame, placeholder_text="Global search...", width=240, height=30)
        self.global_search.pack(side="left")
        self.global_search.bind("<KeyRelease>", lambda e: self.refresh_table())
        self.global_search.bind("<Return>", lambda e: self.refresh_table())
        
        ctk.CTkButton(top_row, text="Clear Filters", width=100, fg_color="#e74c3c", command=self.reset_filters).pack(side="right", padx=5)
        
        # Font size adjustment menu
        self.font_menu = ctk.CTkOptionMenu(top_row, values=["Small Text", "Medium Text", "Large Text"], width=130, command=self.change_text_size)
        self.font_menu.set("Medium Text")
        self.font_menu.pack(side="right", padx=10)
        
        filter_row = ctk.CTkFrame(f_container, fg_color="transparent")
        filter_row.pack(fill="x", padx=5, pady=5)
        
        f_names = ["Inst Type", "VDR Sl no", "Status", "OEM Name", "Custodian", "Package/Team", "Hardware Status", "CSE Remarks"]
        self.filter_labels = {}
        
        for i, key in enumerate(self.col_keys):
            dd = MultiSelectDropdown(filter_row, title=f_names[i], width=140, command=self.refresh_table, persist_key=key)
            dd.pack(side="left", padx=3)
            self.filters[key] = dd
            self.filter_labels[key] = f_names[i]
            
        self.update_filter_options()
        
        # --- Data Entry Header & Container ---
        ctk.CTkLabel(self, text="Data Entry/Update/Delete", font=("Arial Bold", 18), text_color="#6579E2").pack(pady=(15, 0))

        input_row = ctk.CTkFrame(self, fg_color="transparent")
        input_row.pack(fill="x", padx=40, pady=5)
        
        self.inputs = {}
        for i, key in enumerate(self.col_keys):
            if key in ["type", "status", "hw_status"]:
                v = get_master_instrument_types() if key == "type" else ["OK", "NOK"] if key == "hw_status" else ["In inventory", "Deployed", "Demo", "Employee Use", "Not Deployable", "Saleable"]
                self.inputs[key] = ctk.CTkComboBox(input_row, values=v, width=135, state="readonly")
                self.inputs[key].set(f_names[i])
                self.inputs[key].grid(row=0, column=i, padx=2)
                
            elif key in ["oem", "custodian"]:
                available = sorted(list(set(str(item.get(key, "")) for item in self.data_list if item.get(key))))
                self.inputs[key] = ctk.CTkComboBox(input_row, values=available, width=135)
                self.inputs[key].set(f_names[i])
                self.inputs[key].grid(row=0, column=i, padx=2)
                
            elif key == "package":
                available = sorted(list(set(str(item.get(key, "")) for item in self.data_list if item.get(key))))
                self.inputs[key] = ctk.CTkComboBox(input_row, values=available, width=135)
                self.inputs[key].set(f_names[i])
                self.inputs[key].grid(row=0, column=i, padx=2)
                
            elif key == "remarks":
                self.inputs[key] = ctk.CTkEntry(input_row, placeholder_text=f_names[i])
                self.inputs[key].grid(row=0, column=i, padx=(2, 0), sticky="ew")
                input_row.grid_columnconfigure(i, weight=1)
                
            else:
                self.inputs[key] = ctk.CTkEntry(input_row, placeholder_text=f_names[i], width=135)
                self.inputs[key].grid(row=0, column=i, padx=2)
            
        btn_bar = ctk.CTkFrame(self, fg_color="transparent"); btn_bar.pack(fill="x", padx=40)
        ctk.CTkButton(btn_bar, text="Add Entry", fg_color="#1f6aa5", width=90, command=self.add_entry).pack(side="left", padx=2)
        ctk.CTkButton(btn_bar, text="Update", fg_color="#e67e22", width=90, command=self.update_entry).pack(side="left", padx=2)
        ctk.CTkButton(btn_bar, text="Delete", fg_color="#e74c3c", width=90, command=self.delete_entry).pack(side="left", padx=2)
        ctk.CTkButton(btn_bar, text="Clear", fg_color="#E21957", width=90, command=self.clear_inputs).pack(side="left", padx=2)
        ctk.CTkButton(btn_bar, text="📊 Export Excel", fg_color="#218c53", width=110, command=self.export_excel).pack(side="right", padx=2)
        
        # --- BOTTOM FIXED SECTION (Packed first to guarantee visibility) ---
        bottom_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        bottom_wrapper.pack(side="bottom", fill="x", padx=40, pady=(0, 15))

        ctk.CTkButton(bottom_wrapper, text="Close View", width=180, height=40, border_width=1, command=self.destroy).pack(side="bottom", pady=(10, 0))

        self.details_frame = ctk.CTkFrame(bottom_wrapper, corner_radius=10)
        self.details_frame.pack(side="bottom", fill="x")

        row_count_bar = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        row_count_bar.pack(fill="x", padx=10, pady=(10, 0))
        self.row_count_label = ctk.CTkLabel(row_count_bar, text="Total rows: 0", font=("Arial Bold", 14), width=320, anchor="e")
        self.row_count_label.pack(side="right", padx=(0, 10))

        ctk.CTkLabel(self.details_frame, text="Selected CSE Remarks:", font=("Arial Bold", 14)).pack(anchor="w", pady=(5, 0), padx=10)
        if hasattr(ctk, "CTkTextbox"):
            self.remarks_box = ctk.CTkTextbox(self.details_frame, width=1480, height=75, state="disabled", corner_radius=8, font=("Arial", 14))
        else:
            self.remarks_box = tk.Text(self.details_frame, width=180, height=4, wrap="word", bd=0, highlightthickness=0, font=("Arial", 14))
            self.remarks_box.configure(state="disabled")
        self.remarks_box.pack(fill="x", padx=10, pady=(5, 10))

        # --- MIDDLE EXPANDING SECTION (Table Container) ---
        table_container = ctk.CTkFrame(self, fg_color="transparent")
        table_container.pack(side="top", fill="both", expand=True, padx=40, pady=(10, 10))
        
        mode = ctk.get_appearance_mode().lower()
        bg_col = "#ffffff" if "light" in mode else "#1a1a1a"
        fg_col = "#000000" if "light" in mode else "#e1e1e1"
        hd_bg = "#e2e8f0" if "light" in mode else "#2d3748"
        hd_fg = "#1a202c" if "light" in mode else "#dbe7ff"

        style = ttk.Style(self)
        style.configure("Aptiv.Treeview", rowheight=38, font=("Helvetica", 14, "italic"), foreground=fg_col, background=bg_col, fieldbackground=bg_col)
        style.configure("Aptiv.Treeview.Heading", font=("Helvetica", 15, "bold"), background=hd_bg, foreground=hd_fg)
        columns = ["sl"] + self.col_keys

        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="browse", style="Aptiv.Treeview")
        self.tree.heading("sl", text="SI No")
        self.tree.column("sl", width=50, minwidth=50, anchor="center", stretch=False)
        col_defs = [("type", "Inst Type", 140), ("vdr", "VDR SI no", 140), ("status", "Status", 110), ("oem", "OEM Name", 150), ("custodian", "Custodian", 150), ("package", "Package/Team", 130), ("hw_status", "Hardware Status", 130), ("remarks", "CSE Remarks", 280)]
        
        for key, label, width in col_defs:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, minwidth=width, anchor="center", stretch=False)
            
        self.tree.tag_configure("OK", foreground="#276749" if "light" in mode else "#38A169", font=("Helvetica", 14, "italic"))
        self.tree.tag_configure("NOK", foreground="#9b2c2c" if "light" in mode else "#E53E3E", font=("Helvetica", 14, "italic"))
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # --- HORIZONTAL AND VERTICAL SCROLLBARS ---
        self.tree_scroll_y = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree_scroll_x = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        
        self.tree.configure(yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set)
        
        # Packing order is critical: Bottom first, then Right, then Left (fill remaining)
        self.tree_scroll_x.pack(side="bottom", fill="x")
        self.tree_scroll_y.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

    def get_visible_data(self):
        visible = []
        search_q = self.global_search.get().lower()
        for item in self.data_list:
            if search_q and not any(search_q in str(v).lower() for v in item.values()):
                continue
            match = True
            for key, multi_select in self.filters.items():
                selected = multi_select.get()
                item_val = str(item.get(key, ""))
                if len(selected) < len(multi_select.all_options) and item_val not in selected:
                    match = False
                    break
            if match:
                visible.append(item)
        return visible

    def export_excel(self):
        visible = self.get_visible_data()
        if not visible:
            messagebox.showinfo("No Data", "No visible rows to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if path:
            pd.DataFrame(visible).to_excel(path, index=False)
            messagebox.showinfo("Success", f"Exported visible rows to {path}")

    def set_syncing(self, active: bool):
        if active:
            self.sync_status.configure(text="🔄 Syncing JSON...")
        else:
            self.sync_status.configure(text="")
        self.sync_status.update_idletasks()

    def update_filter_options(self):
        saved = load_saved_filter_options()
        for key in self.col_keys:
            vals = sorted(list(set(str(i.get(key, "")) for i in self.data_list if i.get(key))))
            vals += saved.get(key, [])
            merged = sorted(list(dict.fromkeys(vals)))
            widget = self.filters.get(key)
            if widget:
                try:
                    widget.configure_options(merged)
                except Exception:
                    try:
                        widget.configure(values=merged)
                    except Exception:
                        pass

    def refresh_oem_custodian_options(self):
        for key in ["oem", "custodian", "package"]:
            if key in self.inputs and hasattr(self.inputs[key], 'configure'):
                available = sorted(list(set(str(item.get(key, "")) for item in self.data_list if item.get(key))))
                self.inputs[key].configure(values=available)

    def refresh_type_options(self):
        if "type" in self.inputs:
            current_value = self.inputs["type"].get()
            types = get_master_instrument_types()
            self.inputs["type"].configure(values=types)
            if current_value and current_value != "Inst Type":
                if current_value in types:
                    self.inputs["type"].set(current_value)
                elif types:
                    self.inputs["type"].set(types[0])

    def open_master_item_manager(self):
        self.close_current_child_popup()
        self.current_child_popup = MasterItemManager(self)
        self.current_child_popup.protocol("WM_DELETE_WINDOW", lambda: self._clear_child_popup_reference(self.current_child_popup))
        return self.current_child_popup

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        self.visible_indices = []
        search_q = self.global_search.get().lower()
        for idx, item in enumerate(self.data_list):
            if search_q and not any(search_q in str(v).lower() for v in item.values()):
                continue
            
            match = True
            for key, multi_select in self.filters.items():
                selected = multi_select.get()
                item_val = str(item.get(key, ""))
                if len(selected) < len(multi_select.all_options) and item_val not in selected:
                    match = False
                    break
                        
            if not match:
                continue
                
            remarks = str(item.get("remarks", ""))
            if remarks:
                remarks = "\n".join(textwrap.wrap(remarks, width=35))
            status_tag = str(item.get("hw_status", "")).strip().upper()
            self.tree.insert("", "end", values=(idx + 1,
                                                str(item.get("type", "")),
                                                str(item.get("vdr", "")),
                                                str(item.get("status", "")),
                                                str(item.get("oem", "")),
                                                str(item.get("custodian", "")),
                                                str(item.get("package", "")),
                                                str(item.get("hw_status", "")),
                                                remarks), tags=(status_tag,))
            self.visible_indices.append(idx)
            
        total_rows = len(self.data_list)
        visible_rows = len(self.visible_indices)
        self.row_count_label.configure(text=f"Total rows: {total_rows} | Visible rows: {visible_rows}")

    def select_row(self, index):
        self.selected_index = index
        item = self.data_list[index]
        for key, widget in self.inputs.items():
            if hasattr(widget, 'delete'):
                widget.delete(0, 'end')
                widget.insert(0, str(item.get(key, "")))
            else:
                widget.set(str(item.get(key, "")))

    def on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        visible_index = self.tree.index(selection[0])
        if visible_index < len(self.visible_indices):
            self.select_row(self.visible_indices[visible_index])
            item = self.data_list[self.visible_indices[visible_index]]
            remarks = str(item.get("remarks", ""))
            if hasattr(self, "remarks_box"):
                if isinstance(self.remarks_box, tk.Text):
                    self.remarks_box.configure(state="normal")
                    self.remarks_box.delete("1.0", tk.END)
                    self.remarks_box.insert(tk.END, remarks)
                    self.remarks_box.configure(state="disabled")
                else:
                    self.remarks_box.configure(state="normal")
                    self.remarks_box.delete("0.0", "end")
                    self.remarks_box.insert("0.0", remarks)
                    self.remarks_box.configure(state="disabled")

    def clear_inputs(self):
        self.selected_index = None
        f_names = ["Inst Type", "VDR Sl no", "Status", "OEM Name", "Custodian", "Package/Team", "Hardware Status", "CSE Remarks"]
        for i, (key, widget) in enumerate(self.inputs.items()):
            if hasattr(widget, 'delete'):
                widget.delete(0, 'end')
            else:
                widget.set(f_names[i])
        if hasattr(self, "remarks_box"):
            if isinstance(self.remarks_box, tk.Text):
                self.remarks_box.configure(state="normal")
                self.remarks_box.delete("1.0", tk.END)
                self.remarks_box.configure(state="disabled")
            else:
                self.remarks_box.configure(state="normal")
                self.remarks_box.delete("0.0", "end")
                self.remarks_box.configure(state="disabled")
        self.refresh_table()

    def add_entry(self):
        new_data = {k: v.get().strip() for k, v in self.inputs.items()}
        if not new_data["type"] or not new_data["vdr"] or new_data["type"] == "Inst Type" or new_data["vdr"] == "VDR Sl no":
            messagebox.showwarning("Missing Data", "Please enter both Instrument Type and VDR SI no.")
            return
        if any(str(i.get("type", "")).strip().lower() == new_data["type"].strip().lower() and str(i.get("vdr", "")).strip() == new_data["vdr"].strip() for i in self.data_list):
            messagebox.showwarning("Duplicate", "Entry already exists for this Inst Type and VDR SI no!")
            return
        self.data_list.append(new_data)
        self.set_syncing(True)
        with open(MOD3_DATA_FILE, "w") as f: json.dump(self.data_list, f, indent=4)
        self.set_syncing(False)
        self.update_filter_options()
        self.refresh_oem_custodian_options()
        self.clear_inputs()
        log_activity("Aptiv Inventory", f"Added Inst Type: {new_data['type']}, VDR sl no: {new_data['vdr']}")

    def update_entry(self):
        new_data = {k: v.get().strip() for k, v in self.inputs.items()}
        if not new_data["type"] or not new_data["vdr"] or new_data["type"] == "Inst Type" or new_data["vdr"] == "VDR Sl no":
            messagebox.showwarning("Missing Data", "Please enter both Instrument Type and VDR SI no.")
            return
        for idx, item in enumerate(self.data_list):
            if idx == self.selected_index:
                continue
            if (str(item.get("type", "")).strip().lower() == new_data["type"].strip().lower() and
                str(item.get("vdr", "")).strip() == new_data["vdr"].strip()):
                messagebox.showwarning("Duplicate", "Another entry with the same Inst Type and VDR SI no already exists!")
                return
        if self.selected_index is not None:
            self.data_list[self.selected_index] = new_data
        else:
            for i, item in enumerate(self.data_list):
                if str(item.get("vdr")) == new_data["vdr"]:
                    self.data_list[i] = new_data
                    break
        self.set_syncing(True)
        with open(MOD3_DATA_FILE, "w") as f: json.dump(self.data_list, f, indent=4)
        self.set_syncing(False)
        self.update_filter_options()
        self.refresh_oem_custodian_options()
        self.clear_inputs()
        log_activity("Aptiv Inventory", f"Updated VDR sl no: {new_data['vdr']}")

    def delete_entry(self):
        if self.selected_index is not None and 0 <= self.selected_index < len(self.data_list):
            deleted_vdr = self.data_list[self.selected_index].get("vdr", "Unknown")
            self.data_list.pop(self.selected_index)
        else:
            deleted_vdr = self.inputs["vdr"].get()
            self.data_list = [i for i in self.data_list if str(i.get("vdr")) != deleted_vdr]
        self.set_syncing(True)
        with open(MOD3_DATA_FILE, "w") as f: json.dump(self.data_list, f, indent=4)
        self.set_syncing(False)
        self.update_filter_options()
        self.refresh_oem_custodian_options()
        self.clear_inputs()
        log_activity("Aptiv Inventory", f"Deleted VDR sl no: {deleted_vdr}")

    def reset_filters(self):
        self.global_search.delete(0, 'end')
        for dropdown in self.filters.values():
            dropdown.reset()
        self.refresh_table()

class MasterItemManager(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Database Item Manager")
        self.geometry("450x600")
        self.attributes("-topmost", True)
        if hasattr(parent, "close_current_child_popup"):
            parent.close_current_child_popup()
            parent.current_child_popup = self
            self.protocol("WM_DELETE_WINDOW", lambda: parent._clear_child_popup_reference(self))
        self.defaults = ["CT1000", "CT600", "EP2000", "EP800", "EP2500", "RAD IO-temp", "RAD IO- ANA", "AT-48", "CAN HUB"]
        ctk.CTkLabel(self, text="Add New Item to Database", font=("Arial Bold", 20)).pack(pady=20)
        self.e = ctk.CTkEntry(self, width=320, height=40, placeholder_text="Enter Item Name"); self.e.pack(pady=5)
        ctk.CTkButton(self, text="Add to DB", width=200, height=40, command=self.add).pack(pady=20)
        self.f = ctk.CTkScrollableFrame(self, width=400, height=350, fg_color="transparent"); self.f.pack(fill="both", expand=True, padx=20, pady=10)
        self.refresh()

    def refresh(self):
        for w in self.f.winfo_children(): w.destroy()
        custom_items = []
        if os.path.exists(MASTER_DB_FILE):
            try: 
                with open(MASTER_DB_FILE, "r") as file: custom_items = json.load(file)
            except: pass
        all_items = sorted(list(set(self.defaults + custom_items)))
        for item in all_items:
            row = ctk.CTkFrame(self.f, fg_color="transparent"); row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=item, font=("Arial", 15), anchor="w").pack(side="left", padx=10)
            ctk.CTkButton(row, text="X", width=35, height=35, fg_color="#ef4444", command=lambda i=item: self.delete_item(i)).pack(side="right", padx=10)
            if item in self.defaults: ctk.CTkLabel(row, text="default", text_color=("#666666", "#4b5563"), font=("Arial Italic", 12)).pack(side="right", padx=10)

    def add(self):
        val = self.e.get().strip()
        if not val: return
        data = []
        if os.path.exists(MASTER_DB_FILE):
            with open(MASTER_DB_FILE, "r") as f: data = json.load(f)
        if val not in self.defaults and val not in data:
            data.append(val)
            with open(MASTER_DB_FILE, "w") as f: json.dump(data, f, indent=4)
            self.e.delete(0, 'end')
            self.refresh()
            if hasattr(self.parent, "refresh_type_options"):
                self.parent.refresh_type_options()
            log_activity("Master Item Manager", f"Added Master Item: {val}")

    def delete_item(self, item_name):
        if os.path.exists(MASTER_DB_FILE):
            with open(MASTER_DB_FILE, "r") as f: data = json.load(f)
            if item_name in data: 
                data.remove(item_name)
                with open(MASTER_DB_FILE, "w") as f: json.dump(data, f, indent=4)
        self.refresh()
        if hasattr(self.parent, "refresh_type_options"):
            self.parent.refresh_type_options()
        log_activity("Master Item Manager", f"Deleted Master Item: {item_name}")

# --- 7. MAIN LAUNCHER APP ---
class InventoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aptiv Inventory Management System")
        self.geometry("1100x700")
        self.image_path = LAUNCH_PAGE_PATH
        
        # FIX 1: Add fg_color="transparent" so it doesn't block the UI if the image path fails
        self.bg_label = ctk.CTkLabel(self, text="", fg_color="transparent")
        self.bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.bg_label.lower()
        
        self.current_popup = None
        
        # FIX 2: Place buttons inside a dedicated transparent frame to guarantee they stay on top
        self.main_ui_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_ui_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        self.setup_ui_buttons()
        self.current_width, self.current_height = 0, 0
        self.bind("<Configure>", self.resizer)

        # FIX 3: Force macOS to render the UI by triggering a micro-resize
        self.after(100, self._force_mac_render)

    def _force_mac_render(self):
        """Forces macOS window manager to paint the Tkinter canvas."""
        self.geometry("1100x701")
        self.update_idletasks()
        self.geometry("1100x700")

    def close_current_popup(self):
        if getattr(self, "current_popup", None) and self.current_popup.winfo_exists():
            try:
                self.current_popup.destroy()
            except Exception:
                pass
        self.current_popup = None

    def open_popup(self, popup_factory):
        self.close_current_popup()
        popup = popup_factory(self)
        self.current_popup = popup
        popup.protocol("WM_DELETE_WINDOW", lambda: self._clear_popup_reference(popup))
        return popup

    def _clear_popup_reference(self, popup):
        if getattr(self, "current_popup", None) is popup:
            self.current_popup = None
        popup.destroy()

    def resizer(self, event):
        if event.width == self.current_width and event.height == self.current_height: return
        self.current_width, self.current_height = event.width, event.height
        if os.path.exists(self.image_path):
            img = Image.open(self.image_path)
            win_w, win_h = event.width, event.height
            img_aspect, win_aspect = img.size[0]/img.size[1], win_w/win_h
            if win_aspect > img_aspect: 
                new_w, new_h = win_w, int(win_w/img_aspect)
            else: 
                new_h, new_w = win_h, int(win_h*img_aspect)
            
            resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            final = resized.crop(((new_w-win_w)//2, (new_h-win_h)//2, (new_w+win_w)//2, (new_h+win_h)//2))
            self.bg_photo = ctk.CTkImage(final, size=(win_w, win_h))
            self.bg_label.configure(image=self.bg_photo)

    def setup_ui_buttons(self):
        style = {"width": 320, "height": 55, "font": ("Arial Bold", 17), "fg_color": "#2D74BC", "hover_color": "#245D96", "corner_radius": 10}
        
        # Notice we are placing these on self.main_ui_frame now instead of self
        ctk.CTkButton(self.main_ui_frame, text="Show Analytics Dashboard", **style, command=self.open_analytics).place(relx=0.05, rely=0.30, anchor="nw")
        ctk.CTkButton(self.main_ui_frame, text="Customer Owned Devices", **style, command=lambda: self.open_popup(CustomerOwnedVDR)).place(relx=0.05, rely=0.41, anchor="nw")
        ctk.CTkButton(self.main_ui_frame, text="Aptiv Inventory", **style, command=lambda: self.open_popup(AptivInventory)).place(relx=0.05, rely=0.52, anchor="nw")

    def open_analytics(self):
        self.close_current_popup()
        sel = ctk.CTkToplevel(self)
        self.current_popup = sel
        sel.title("Dashboard Selector")
        sel.geometry("420x260")
        sel.attributes("-topmost", True)
        sel.protocol("WM_DELETE_WINDOW", lambda: self._clear_popup_reference(sel))

        ctk.CTkLabel(sel, text="Dashboard Selector", font=("Arial", 20, "bold")).pack(pady=(16, 10))
        ctk.CTkButton(sel, text="Aptiv Analytics", width=300, height=45, fg_color="#2D74BC", font=("Arial Bold", 16), command=lambda: [self._clear_popup_reference(sel), self.open_popup(show_aptiv_dashboard)]).pack(pady=20)
        ctk.CTkButton(sel, text="Customer Analytics", width=300, height=45, fg_color="#2D74BC", font=("Arial Bold", 16), command=lambda: [self._clear_popup_reference(sel), self.open_popup(show_customer_dashboard)]).pack(pady=20)

if __name__ == "__main__":
    InventoryApp().mainloop()