import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import Counter
import xml.etree.ElementTree as ET
import customtkinter as ctk
import csv

# Set appearance mode to System to automatically adapt to macOS Light/Dark mode
ctk.set_appearance_mode("System")

# Define the custom orange theme colors
ACCENT_COLOR = "#E67E22"
ACCENT_HOVER = "#D35400"

class ModernViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("XML || LAB Parameter Studio")
        self.root.geometry("1400x850")
        self.root.minsize(1150, 700)
        self.root.configure(fg_color=("#F6F8FC", "#0A111B"))

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.parameters_data = []
        self.unique_rasters = set()
        self.current_filter = "All"
        self.param_tree_sort_state = {"ParamName": False, "Raster": False}

        # ==================== SIDEBAR ====================
        self.sidebar_frame = ctk.CTkFrame(
            self.root,
            width=260,
            corner_radius=20,
            fg_color=("#FFFFFF", "#111B2A"),
            border_width=1,
            border_color=("#E7EBF3", "#1F2A38")
        )
        self.sidebar_frame.grid(row=0, column=0, padx=(18, 12), pady=18, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_container = ctk.CTkFrame(
            self.sidebar_frame,
            corner_radius=18,
            fg_color=("#F4F7FF", "#182434"),
            border_width=1,
            border_color=("#DDE4F2", "#2B3949")
        )
        self.logo_container.grid(row=0, column=0, padx=18, pady=(18, 14), sticky="ew")

        self.logo_label = ctk.CTkLabel(
            self.logo_container,
            text="XML || LAB\nStudio",
            font=ctk.CTkFont(family="Helvetica", size=28, weight="bold"),
            justify="center",
            text_color=("#1E293B", "#E9EEF8")
        )
        self.logo_label.pack(padx=16, pady=18)

        self.btn_open = ctk.CTkButton(
            self.sidebar_frame,
            text="Browse File...",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.open_file,
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            corner_radius=12,
            height=44
        )
        self.btn_open.grid(row=1, column=0, padx=18, pady=(8, 8), sticky="ew")

        self.btn_clear = ctk.CTkButton(
            self.sidebar_frame,
            text="Clear File",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.clear_file,
            fg_color=("#DF6B5B", "#E76F51"),
            hover_color=("#C95A4A", "#C75D45"),
            corner_radius=12,
            height=42
        )
        self.btn_clear.grid(row=2, column=0, padx=18, pady=(0, 14), sticky="ew")

        self.info_card = ctk.CTkFrame(
            self.sidebar_frame,
            corner_radius=16,
            fg_color=("#F5F7FB", "#121E2D"),
            border_width=1,
            border_color=("#E7ECF5", "#1E2B39")
        )
        self.info_card.grid(row=3, column=0, padx=18, pady=(0, 18), sticky="ew")

        self.lbl_file_title = ctk.CTkLabel(
            self.info_card,
            text="Loaded File",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#64748B", "#94A3B8")
        )
        self.lbl_file_title.pack(anchor="w", padx=16, pady=(14, 4))

        self.lbl_file = ctk.CTkLabel(
            self.info_card,
            text="No file selected",
            text_color=("#475569", "#D7E3EF"),
            wraplength=200,
            justify="left",
            font=ctk.CTkFont(size=13)
        )
        self.lbl_file.pack(anchor="w", padx=16, pady=(0, 10))

        self.meta_frame = ctk.CTkFrame(
            self.info_card,
            corner_radius=12,
            fg_color=("#EEF3F9", "#0E1B2A"),
            border_width=1,
            border_color=("#D9E2F0", "#1E2D3D")
        )
        self.meta_frame.pack(anchor="w", fill="x", padx=16, pady=(0, 14))

        self.lbl_total_params = ctk.CTkLabel(
            self.meta_frame,
            text="Total Parameters: 0",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#1E293B", "#E2E8F0"),
            justify="left"
        )
        self.lbl_total_params.pack(anchor="w", padx=12, pady=(12, 6))

        self.lbl_raster_counts = ctk.CTkLabel(
            self.meta_frame,
            text="Raster counts:\n-",
            font=ctk.CTkFont(size=11),
            text_color=("#475569", "#D7E3EF"),
            justify="left",
            wraplength=180
        )
        self.lbl_raster_counts.pack(anchor="w", padx=12, pady=(0, 12))

        self.sidebar_footer = ctk.CTkLabel(
            self.sidebar_frame,
            text="Structured XML & LAB\ninspection workspace",
            text_color=("#7A8AA4", "#8EA1B8"),
            font=ctk.CTkFont(size=11),
            justify="center"
        )
        self.sidebar_footer.grid(row=5, column=0, padx=18, pady=(0, 18), sticky="s")

        # ==================== MAIN AREA (Tabs) ====================
        self.tabview = ctk.CTkTabview(
            self.root,
            segmented_button_selected_color=ACCENT_COLOR,
            segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_hover_color=("#B6C2D3", "#2D3D4D"),
            border_color=("#DDE5F0", "#1E2A37"),
            fg_color=("#F8FAFC", "#0E1725"),
            corner_radius=20
        )
        self.tabview.grid(row=0, column=1, padx=(0, 18), pady=18, sticky="nsew")

        self.tabview._segmented_button.configure(
            font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"),
            fg_color=("#EEF2F7", "#162332"),
            text_color=("#475569", "#E2E8F0"),
            selected_color=ACCENT_COLOR,
            selected_hover_color=ACCENT_HOVER
        )

        self.tabview.add("Tree View")
        self.tabview.add("Parameters List")

        self.setup_tree_tab()
        self.setup_params_tab()

        self.current_theme = None
        self.check_appearance_mode()

    def check_appearance_mode(self):
        """Continuously polls the OS theme to dynamically update the ttk.Treeview styling."""
        system_mode = ctk.get_appearance_mode()
        if self.current_theme != system_mode:
            self.current_theme = system_mode
            self.apply_treeview_style(system_mode)
        
        # Check again every 1000ms
        self.root.after(1000, self.check_appearance_mode)

    def apply_treeview_style(self, mode):
        """Applies dynamic Light or Dark mode colors to the standard ttk widgets."""
        style = ttk.Style(self.root)
        style.theme_use("default")

        if mode == "Dark":
            bg_color = "#101B29"
            fg_color = "#E5F0FF"
            head_bg = "#1A2635"
            sel_bg = ACCENT_COLOR
            even_row = "#111F2F"
            odd_row = "#152334"
            border_color = "#233446"
        else:
            bg_color = "#F8FAFC"
            fg_color = "#0F172A"
            head_bg = "#EDF2F7"
            sel_bg = ACCENT_COLOR
            even_row = "#FFFFFF"
            odd_row = "#F8FAFC"
            border_color = "#DDE5F0"

        style.configure(
            "Treeview",
            background=bg_color,
            foreground=fg_color,
            rowheight=34,
            fieldbackground=bg_color,
            bordercolor=border_color,
            borderwidth=0,
            font=("Helvetica", 11)
        )
        style.map('Treeview', background=[('selected', sel_bg)])

        style.configure(
            "Treeview.Heading",
            background=head_bg,
            foreground=fg_color,
            relief="flat",
            font=("Helvetica", 16, "bold italic"),
            padding=(12, 12)
        )
        style.map("Treeview.Heading", background=[('active', head_bg)])

        if hasattr(self, 'param_tree'):
            self.param_tree.tag_configure('evenrow', background=even_row, foreground=fg_color)
            self.param_tree.tag_configure('oddrow', background=odd_row, foreground=fg_color)

        if hasattr(self, 'tree'):
            self.tree.tag_configure('Treeview', background=bg_color, foreground=fg_color)

    def setup_tree_tab(self):
        tab = self.tabview.tab("Tree View")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        container = ctk.CTkFrame(
            tab,
            corner_radius=18,
            fg_color=("#FFFFFF", "#0F1C2B"),
            border_width=1,
            border_color=("#E3EAF3", "#1D2B3A")
        )
        container.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(container, columns=("Attributes", "Text"), show="tree headings")

        self.tree.heading("#0", text="Node / Tag")
        self.tree.heading("Attributes", text="Raw Attributes")
        self.tree.heading("Text", text="Text Content")
        self.tree.heading("#0", command=lambda: None)
        self.tree.heading("Attributes", command=lambda: None)
        self.tree.heading("Text", command=lambda: None)

        self.tree.column("#0", width=350, anchor='w')
        self.tree.column("Attributes", width=500, anchor='w')
        self.tree.column("Text", width=300, anchor='w')

        vsb = ctk.CTkScrollbar(
            container, orientation="vertical", command=self.tree.yview,
            button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER
        )
        hsb = ctk.CTkScrollbar(
            container, orientation="horizontal", command=self.tree.xview,
            button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER
        )
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')

    def setup_params_tab(self):
        tab = self.tabview.tab("Parameters List")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        ctrl_frame = ctk.CTkFrame(
            tab,
            fg_color="transparent"
        )
        ctrl_frame.grid(row=0, column=0, sticky="ew", pady=(8, 12))

        ctk.CTkLabel(
            ctrl_frame, text="Filter by Raster:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#334155", "#E2E8F0")
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.opt_filter = ctk.CTkOptionMenu(
            ctrl_frame, values=["All"], command=self.apply_filter,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=ACCENT_COLOR, button_color=ACCENT_COLOR,
            button_hover_color=ACCENT_HOVER, dropdown_hover_color=ACCENT_HOVER,
            dropdown_font=ctk.CTkFont(size=12), width=320,
            corner_radius=10
        )
        self.opt_filter.pack(side=tk.LEFT)

        self.btn_copy = ctk.CTkButton(
            ctrl_frame, text="Copy Parameters", command=self.copy_parameters,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, width=150,
            corner_radius=10
        )
        self.btn_copy.pack(side=tk.RIGHT, padx=5)

        self.btn_export = ctk.CTkButton(
            ctrl_frame, text="Export to Excel", command=self.export_to_excel,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, width=150,
            corner_radius=10
        )
        self.btn_export.pack(side=tk.RIGHT, padx=5)

        tree_frame = ctk.CTkFrame(
            tab,
            corner_radius=18,
            fg_color=("#FFFFFF", "#0F1C2B"),
            border_width=1,
            border_color=("#E3EAF3", "#1D2B3A")
        )
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 0))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        self.param_tree = ttk.Treeview(tree_frame, columns=("ParamName", "Raster"), show="headings")
        self.param_tree.heading("ParamName", text="Parameter Name", command=lambda: self.sort_param_tree("ParamName"))
        self.param_tree.heading("Raster", text="Raster / Group", command=lambda: self.sort_param_tree("Raster"))

        self.param_tree.column("ParamName", width=600, anchor='w')
        self.param_tree.column("Raster", width=300, anchor='w')

        vsb_param = ctk.CTkScrollbar(
            tree_frame, orientation="vertical", command=self.param_tree.yview,
            button_color=ACCENT_COLOR, button_hover_color=ACCENT_HOVER
        )
        self.param_tree.configure(yscrollcommand=vsb_param.set)

        self.param_tree.grid(column=0, row=0, sticky="nsew")
        vsb_param.grid(column=1, row=0, sticky="ns")

    def open_file(self):
        filepath = filedialog.askopenfilename(
            title="Select File",
            filetypes=[
                ("Supported Files", "*.xml *.lab"), 
                ("XML Files", "*.xml"), 
                ("LAB Files", "*.lab"), 
                ("All Files", "*.*")
            ]
        )
        
        if filepath:
            self.process_file(filepath)

    def update_metadata_summary(self):
        total_count = len(self.parameters_data)
        raster_counts = Counter(
            raster if raster else "[No Raster]"
            for _, raster in self.parameters_data
        )

        self.lbl_total_params.configure(text=f"Total Parameters: {total_count}")

        if raster_counts:
            lines = ["Raster counts:"]
            for raster_name, count in sorted(raster_counts.items()):
                lines.append(f"• {raster_name}: {count}")
            self.lbl_raster_counts.configure(text="\n".join(lines))
        else:
            self.lbl_raster_counts.configure(text="Raster counts:\n• None")

    def clear_file(self):
        self.lbl_file.configure(text="No file selected", text_color=("gray50", "gray70"))

        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self.param_tree.get_children():
            self.param_tree.delete(item)

        self.parameters_data.clear()
        self.unique_rasters.clear()

        self.opt_filter.configure(values=["All"])
        self.opt_filter.set("All")
        self.update_metadata_summary()

    def process_file(self, filepath):
        self.clear_file()
        filename_only = filepath.split("/")[-1].split("\\")[-1]
        self.lbl_file.configure(text=f"Loaded:\n{filename_only}", text_color=("black", "white"))

        try:
            if filepath.lower().endswith(".lab"):
                self.parse_lab(filepath)
            else:
                self.parse_xml(filepath)
            
            raster_list = ["All"] + sorted(list(self.unique_rasters))
            self.opt_filter.configure(values=raster_list)
            self.opt_filter.set("All")
            self.update_metadata_summary()
            self.apply_filter("All")

        except ET.ParseError as e:
            messagebox.showerror("XML Parse Error", f"The file is not a valid XML.\nDetails: {e}")
            self.clear_file()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process file:\n{e}")
            self.clear_file()

    def parse_xml(self, filepath):
        tree = ET.parse(filepath)
        root = tree.getroot()
        self.populate_xml_tree("", root)

    def populate_xml_tree(self, parent_node_id, element):
        param_name = element.attrib.get('Name', '') if element.attrib else ""
        raster = element.attrib.get('Raster', '') if element.attrib else ""
        attrs = str(element.attrib) if element.attrib else ""
        text = element.text.strip() if element.text and element.text.strip() else ""
        
        node_id = self.tree.insert(parent_node_id, "end", text=element.tag, values=(attrs, text))
        
        if parent_node_id == "":
            self.tree.item(node_id, open=True)

        if param_name:
            self.parameters_data.append((param_name, raster))
            if raster:
                self.unique_rasters.add(raster)
            else:
                self.unique_rasters.add("[No Raster]")
        
        for child in element:
            self.populate_xml_tree(node_id, child)

    def parse_lab(self, filepath):
        current_group = "[Root Data]"
        parent_node_id = self.tree.insert("", "end", text="Group", values=("", ""))
        self.tree.item(parent_node_id, open=True)
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
            for line in file:
                line = line.strip()
                
                if not line or line.startswith('//'):
                    continue
                
                if line.startswith('[') and line.endswith(']'):
                    current_group = line[1:-1]
                    parent_node_id = self.tree.insert("", "end", text="Group", values=("", ""))
                    self.tree.item(parent_node_id, open=True)
                else:
                    parts = line.split(';')
                    
                    param_name = parts[0].strip()
                    raster = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "[No Raster]"
                    attrs = ";".join(parts[2:]).strip() if len(parts) > 2 else ""
                    
                    self.tree.insert(parent_node_id, "end", text="Parameter", values=(attrs, current_group))
                    
                    self.parameters_data.append((param_name, raster))
                    self.unique_rasters.add(raster)

    def sort_param_tree(self, column):
        reverse = self.param_tree_sort_state.get(column, False)
        visible_rows = []

        for item in self.param_tree.get_children():
            values = self.param_tree.item(item)["values"]
            if values:
                visible_rows.append((values[0], values[1]))

        if column == "ParamName":
            visible_rows.sort(key=lambda row: str(row[0]).lower(), reverse=reverse)
        else:
            visible_rows.sort(key=lambda row: str(row[1]).lower(), reverse=reverse)

        self.param_tree.delete(*self.param_tree.get_children())
        for index, (param_name, raster) in enumerate(visible_rows):
            tag = 'evenrow' if index % 2 == 0 else 'oddrow'
            self.param_tree.insert("", "end", values=(param_name, raster), tags=(tag,))

        self.param_tree_sort_state[column] = not reverse
        for key in self.param_tree_sort_state:
            if key != column:
                self.param_tree_sort_state[key] = False

    def apply_filter(self, selected_raster):
        self.current_filter = selected_raster
        for item in self.param_tree.get_children():
            self.param_tree.delete(item)

        filtered_rows = []
        for param_name, raster in self.parameters_data:
            display_raster = raster if raster else "[No Raster]"
            if selected_raster == "All" or display_raster == selected_raster:
                filtered_rows.append((param_name, raster))

        for index, (param_name, raster) in enumerate(filtered_rows):
            tag = 'evenrow' if index % 2 == 0 else 'oddrow'
            self.param_tree.insert("", "end", values=(param_name, raster), tags=(tag,))

        if self.param_tree_sort_state.get("ParamName", False) or self.param_tree_sort_state.get("Raster", False):
            for column in ["ParamName", "Raster"]:
                if self.param_tree_sort_state.get(column, False):
                    self.sort_param_tree(column)
                    break

    def copy_parameters(self):
        visible_items = self.param_tree.get_children()
        params_to_copy = []
        
        for item in visible_items:
            item_values = self.param_tree.item(item)['values']
            if item_values:
                params_to_copy.append(str(item_values[0]))
                
        if not params_to_copy:
            messagebox.showinfo("Copy", "No parameters to copy.")
            return
            
        clipboard_text = "\n".join(params_to_copy)
        self.root.clipboard_clear()
        self.root.clipboard_append(clipboard_text)
        
        messagebox.showinfo("Success", f"Copied {len(params_to_copy)} parameters to clipboard.")

    def export_to_excel(self):
        visible_items = self.param_tree.get_children()
        
        if not visible_items:
            messagebox.showinfo("Export", "No parameters available to export.")
            return
            
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Excel CSV File", "*.csv"), ("All Files", "*.*")],
            title="Save as Excel File"
        )
        
        if not filepath:
            return
            
        try:
            with open(filepath, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["Parameter Name", "Raster"])
                
                for item in visible_items:
                    item_values = self.param_tree.item(item)['values']
                    if item_values:
                        writer.writerow([str(item_values[0]), str(item_values[1])])
                        
            messagebox.showinfo("Success", f"Successfully exported to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export file:\n{e}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = ModernViewerApp(root)
    root.mainloop()