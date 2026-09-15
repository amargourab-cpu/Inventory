import os
import sys
import csv
from collections import Counter
import xml.etree.ElementTree as ET

from kivy.app import App
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.treeview import TreeView, TreeViewLabel
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.properties import StringProperty, NumericProperty, ListProperty, BooleanProperty
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.clock import Clock

# Set initial window dimensions and modern dark background
Window.size = (1300, 820)
Window.minimum_width = 1050
Window.minimum_height = 680
Window.clearcolor = (0.043, 0.063, 0.106, 1)  # #0B101B Dark Slate

KV_STYLE = """
#:import dp kivy.metrics.dp

# ==================== REUSABLE MODERN COMPONENTS ====================
<ModernCard@BoxLayout>:
    bg_color: app.card_bg
    border_color: app.card_border
    canvas.before:
        Color:
            rgba: self.border_color if self.border_color else (0.173, 0.224, 0.322, 0.8)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]
        Color:
            rgba: self.bg_color if self.bg_color else (0.082, 0.118, 0.184, 1)
        RoundedRectangle:
            pos: self.x + dp(1), self.y + dp(1)
            size: self.width - dp(2), self.height - dp(2)
            radius: [dp(13)]

# default label color follows app theme unless overridden
<Label>:
    color: app.text_primary

<AccentButton@Button>:
    background_color: 0, 0, 0, 0
    bg_normal: app.accent_normal
    bg_down: app.accent_down
    bold: True
    font_size: '13sp'
    color: 1, 1, 1, 1
    canvas.before:
        Color:
            rgba: (self.bg_down if self.state == 'down' else self.bg_normal) if (self.bg_down if self.state == 'down' else self.bg_normal) else app.accent_normal
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]

<IconButton@ButtonBehavior+BoxLayout>:
    icon: ''
    text: ''
    padding: [dp(10), dp(6)]
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: app.card_bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]
    Image:
        source: root.icon
        size_hint_x: None
        width: dp(20)
        allow_stretch: True
    Label:
        text: root.text
        valign: 'middle'
        halign: 'left'
        text_size: self.size

<IconAccentButton@ButtonBehavior+BoxLayout>:
    icon: ''
    icon_source: ''
    text: ''
    theme_button: False
    padding: [dp(12), dp(8)]
    spacing: dp(10)
    canvas.before:
        Color:
            rgba: ((0.10, 0.10, 0.10, 1) if app.theme == 'dark' else (0.93, 0.92, 0.91, 1)) if root.theme_button else (app.accent_down if self.state == 'down' else app.accent_normal)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]
    Image:
        source: root.icon_source
        size_hint_x: None
        width: dp(20)
        allow_stretch: True
        opacity: 1 if root.icon_source else 0
    Label:
        text: root.icon if not root.icon_source else ''
        size_hint_x: None
        width: dp(22) if not root.icon_source else 0
        valign: 'middle'
        halign: 'center'
        text_size: self.size
        font_size: '18sp'
    Label:
        text: root.text
        valign: 'middle'
        halign: 'left'
        text_size: self.size

<ExportCsvButton@ButtonBehavior+BoxLayout>:
    orientation: 'horizontal'
    size_hint_x: None
    width: dp(150)
    height: dp(42)
    padding: [dp(10), dp(6)]
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: app.accent_normal
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]
    Image:
        source: app.asset_path('Asset/xls.icns')
        size_hint: None, None
        size: dp(22), dp(22)
        allow_stretch: True
        keep_ratio: True
    Label:
        text: 'Export\\nCSV'
        color: 1, 1, 1, 1
        font_size: '12sp'
        bold: True
        valign: 'middle'
        halign: 'center'
        text_size: self.size
        line_height: 1.0

<SpinnerOption@Label>:
    size_hint_y: None
    height: dp(36)
    padding: [dp(10), dp(8)]
    color: app.text_primary
    canvas.before:
        Color:
            rgba: app.card_bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(6)]

<DangerButton@AccentButton>:
    bg_normal: 0.957, 0.247, 0.369, 1      # Crimson Rose
    bg_down: 0.780, 0.180, 0.280, 1

<EmeraldButton@AccentButton>:
    bg_normal: 0.063, 0.725, 0.506, 1      # Emerald
    bg_down: 0.040, 0.580, 0.400, 1

<CyanButton@AccentButton>:
    bg_normal: 0.024, 0.714, 0.831, 1      # Electric Cyan
    bg_down: 0.015, 0.560, 0.650, 1

<TabButton@ButtonBehavior+BoxLayout>:
    icon_source: ''
    tab_label: ''
    selected: False
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(58)
    padding: [dp(18), dp(12)]
    spacing: dp(14)
    canvas.before:
        Color:
            rgba: (app.accent_down if root.selected else app.card_border)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(18)]
    Image:
        source: root.icon_source
        size_hint: None, None
        size: dp(30), dp(30)
        allow_stretch: True
        keep_ratio: True
        opacity: 1 if root.icon_source else 0
    Label:
        text: root.tab_label
        color: (1, 1, 1, 1) if root.selected else app.text_secondary
        font_size: '17sp'
        bold: True
        valign: 'middle'
        halign: 'center'
        text_size: self.size
        shorten: True
        shorten_from: 'right'

# ==================== TABLE ROW COMPONENT ====================
<ParamRow>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(38)
    padding: [dp(14), 0]
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: app.row_bg_even if root.index % 2 == 0 else app.row_bg_odd
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(6)]
    Label:
        text: root.param_name
        text_size: self.size
        halign: 'left'
        valign: 'middle'
        color: app.text_primary
        font_size: '13sp'
    Label:
        text: root.raster
        size_hint_x: 0.45
        text_size: self.size
        halign: 'left'
        valign: 'middle'
        color: app.accent_normal
        font_size: '13sp'
        bold: True

<ModernTreeNode>:
    color: 0.90, 0.94, 1.0, 1
    font_size: '13sp'
    height: dp(28)

# ==================== MAIN ROOT VIEW ====================
<RootStudioLayout>:
    orientation: 'vertical'
    padding: dp(14)
    spacing: dp(12)

    # Top Navigation Header
    ModernCard:
        size_hint_y: None
        height: dp(64)
        padding: [dp(18), dp(10)]
        spacing: dp(14)
        
        Label:
            text: "◈  XML || LAB PARAMETER STUDIO"
            font_size: '18sp'
            bold: True
            color: 0.024, 0.714, 0.831, 1
            size_hint_x: None
            width: self.texture_size[0]
            valign: 'middle'

        Widget:
        
        Label:
            id: header_status
            text: "Ready (Drag & Drop .xml / .lab file directly)"
            color: 0.58, 0.64, 0.72, 1
            font_size: '12sp'
            size_hint_x: None
            width: self.texture_size[0]
            valign: 'middle'

        IconAccentButton:
            icon_source: app.asset_path('Asset/brightness-and-contrast.icns')
            text: ''
            theme_button: True
            size_hint_x: None
            width: dp(46)
            height: dp(36)
            padding: [dp(10), dp(8)]
            on_release: app.toggle_theme()

    # Content Area (Sidebar + Main Tab View)
    BoxLayout:
        spacing: dp(14)

        # ----------------- SIDEBAR -----------------
        ModernCard:
            size_hint_x: None
            width: dp(310)
            orientation: 'vertical'
            padding: dp(16)
            spacing: dp(12)

            Label:
                text: "WORKSPACE ACTIONS"
                font_size: '11sp'
                bold: True
                color: 0.45, 0.52, 0.62, 1
                size_hint_y: None
                height: dp(18)
                halign: 'left'
                text_size: self.size

            IconAccentButton:
                icon_source: app.asset_path('Asset/arrow.icns')
                text: 'Browse File...'
                size_hint_y: None
                height: dp(42)
                on_release: root.open_file_dialog()

            IconAccentButton:
                icon_source: app.asset_path('Asset/recycle-bin.icns')
                text: 'Clear File'
                size_hint_y: None
                height: dp(40)
                on_release: root.clear_file()

            # Metadata Info Card
            ModernCard:
                bg_color: app.card_bg
                border_color: app.card_border
                orientation: 'vertical'
                padding: dp(12)
                spacing: dp(8)

                Label:
                    text: "LOADED FILE"
                    font_size: '10sp'
                    bold: True
                    color: 0.024, 0.714, 0.831, 1
                    size_hint_y: None
                    height: dp(16)
                    halign: 'left'
                    text_size: self.size

                Label:
                    id: lbl_filename
                    text: "No file selected"
                    font_size: '12sp'
                    bold: True
                    color: 0.94, 0.96, 0.98, 1
                    size_hint_y: None
                    height: dp(32)
                    halign: 'left'
                    text_size: self.size

                Label:
                    id: lbl_total_count
                    text: "Total Parameters: 0"
                    font_size: '12sp'
                    bold: True
                    color: 0.388, 0.400, 0.945, 1
                    size_hint_y: None
                    height: dp(20)
                    halign: 'left'
                    text_size: self.size

                # Scrollable Raster Breakdown List
                Label:
                    text: "RASTER BREAKDOWN:"
                    font_size: '10sp'
                    bold: True
                    color: 0.45, 0.52, 0.62, 1
                    size_hint_y: None
                    height: dp(16)
                    halign: 'left'
                    text_size: self.size

                ScrollView:
                    do_scroll_x: False
                    bar_width: dp(4)
                    bar_color: 0.024, 0.714, 0.831, 0.8
                    Label:
                        id: lbl_rasters
                        text: "• None"
                        font_size: '11sp'
                        color: 0.75, 0.80, 0.88, 1
                        size_hint_y: None
                        height: self.texture_size[1]
                        text_size: (self.width, None)
                        valign: 'top'

            Label:
                text: "Supports XML & LAB files\\nKivy Modern Studio"
                font_size: '11sp'
                color: 0.4, 0.46, 0.56, 1
                halign: 'center'
                size_hint_y: None
                height: dp(36)

        # ----------------- MAIN VIEW -----------------
        ModernCard:
            orientation: 'vertical'
            padding: dp(16)
            spacing: dp(12)

            # Tab Selection Bar
            BoxLayout:
                size_hint_y: None
                height: dp(42)
                spacing: dp(10)

                TabButton:
                    id: tab_btn_tree
                    icon_source: app.asset_path('Asset/taxonomy.icns')
                    tab_label: "Hierarchy Tree View"
                    selected: True
                    on_release: root.switch_tab('tree')

                TabButton:
                    id: tab_btn_table
                    icon_source: app.asset_path('Asset/search-list.icns')
                    tab_label: "Parameters List"
                    selected: False
                    on_release: root.switch_tab('table')

            # Screen Switcher Container
            ScreenManager:
                id: tab_manager

                # View 1: Tree View
                Screen:
                    name: 'tree_screen'
                    ModernCard:
                        bg_color: app.card_bg
                        border_color: app.card_border
                        padding: dp(10)

                        ScrollView:
                            id: tree_scroll
                            do_scroll_x: True
                            do_scroll_y: True
                            bar_width: dp(8)
                            bar_color: 0.024, 0.714, 0.831, 0.6
                            bar_inactive_color: 0.14, 0.18, 0.27, 0.5

                            BoxLayout:
                                id: tree_container
                                orientation: 'vertical'
                                size_hint: 1, None
                                height: dp(200)

                # View 2: Parameters List
                Screen:
                    name: 'table_screen'
                    BoxLayout:
                        orientation: 'vertical'
                        spacing: dp(10)

                        # Filter & Action Control Bar
                        BoxLayout:
                            size_hint_y: None
                            height: dp(38)
                            spacing: dp(10)

                            Label:
                                text: "Filter Raster:"
                                size_hint_x: None
                                width: dp(90)
                                color: 0.8, 0.85, 0.92, 1
                                bold: True
                                font_size: '12sp'

                            Spinner:
                                id: raster_spinner
                                text: 'All'
                                values: ['All']
                                size_hint_x: None
                                width: dp(120)
                                background_color: 0, 0, 0, 0
                                color: app.text_primary
                                bold: True
                                font_size: '12sp'
                                on_text: root.apply_filter()
                                canvas.before:
                                    Color:
                                        rgba: app.card_border
                                    RoundedRectangle:
                                        pos: self.pos
                                        size: self.size
                                        radius: [dp(8)]

                            BoxLayout:
                                size_hint_x: 1
                                spacing: dp(10)
                                padding: [dp(12), dp(8)]
                                canvas.before:
                                    Color:
                                        rgba: 0.06, 0.09, 0.15, 1
                                    RoundedRectangle:
                                        pos: self.pos
                                        size: self.size
                                        radius: [dp(10)]
                                Image:
                                    source: app.asset_path('Asset/search.icns')
                                    size_hint_x: None
                                    width: dp(18)
                                    allow_stretch: True
                                    keep_ratio: True
                                TextInput:
                                    id: search_box
                                    hint_text: "Search parameter name..."
                                    multiline: False
                                    background_color: 0, 0, 0, 0
                                    foreground_color: 1, 1, 1, 1
                                    cursor_color: 0.024, 0.714, 0.831, 1
                                    font_size: '13sp'
                                    padding: [dp(8), dp(0)]
                                    on_text: root.apply_filter()

                            IconAccentButton:
                                icon_source: app.asset_path('Asset/copy.icns')
                                text: 'Copy'
                                size_hint_x: None
                                width: dp(110)
                                on_release: root.copy_parameters()

                            ExportCsvButton:
                                on_release: root.export_to_csv()

                        # Table Header
                        BoxLayout:
                            size_hint_y: None
                            height: dp(38)
                            padding: [dp(14), 0]
                            canvas.before:
                                Color:
                                    rgba: app.row_header
                                RoundedRectangle:
                                    pos: self.pos
                                    size: self.size
                                    radius: [dp(6)]
                            Button:
                                text: "PARAMETER NAME"
                                background_color: 0, 0, 0, 0
                                color: app.text_secondary
                                bold: True
                                halign: 'left'
                                valign: 'middle'
                                text_size: self.size
                                font_size: '12sp'
                                on_release: root.sort_table('param_name')
                            Button:
                                text: "RASTER / GROUP"
                                size_hint_x: 0.45
                                background_color: 0, 0, 0, 0
                                color: app.text_secondary
                                bold: True
                                halign: 'left'
                                valign: 'middle'
                                text_size: self.size
                                font_size: '12sp'
                                on_release: root.sort_table('raster')

                        # High-Performance Virtualized Table
                        RecycleView:
                            id: params_table
                            viewclass: 'ParamRow'
                            bar_width: dp(6)
                            bar_color: 0.388, 0.400, 0.945, 0.8
                            RecycleBoxLayout:
                                default_size: None, dp(38)
                                default_size_hint: 1, None
                                size_hint_y: None
                                height: self.minimum_height
                                orientation: 'vertical'
                                spacing: dp(4)

# ==================== FILE CHOOSER MODAL DIALOG ====================
<FileSelectModal>:
    size_hint: 0.85, 0.85
    auto_dismiss: False
    background_color: 0, 0, 0, 0.6

    ModernCard:
        orientation: 'vertical'
        padding: dp(18)
        spacing: dp(12)

        BoxLayout:
            orientation: 'vertical'

            BoxLayout:
                size_hint_y: None
                height: dp(36)
                padding: [dp(6), 0]
                Label:
                    text: "📂 Select XML or LAB File"
                    font_size: '16sp'
                    bold: True
                    color: app.accent_normal
                    halign: 'left'
                    text_size: self.size

            BoxLayout:
                size_hint_y: None
                height: dp(36)
                spacing: dp(8)
                padding: [dp(8), 0]
                Button:
                    text: 'Home'
                    size_hint_x: None
                    width: dp(90)
                    on_release: root.go_home()
                Button:
                    text: 'Up'
                    size_hint_x: None
                    width: dp(90)
                    on_release: root.go_up()
                Label:
                    text: root.start_path
                    halign: 'left'
                    text_size: self.size

            FileChooserListView:
                id: file_chooser
                filters: ['*.xml', '*.lab', '*.XML', '*.LAB']
                path: root.start_path
                size_hint: 1, 1
                multiselect: False

            BoxLayout:
                size_hint_y: None
                height: dp(46)
                spacing: dp(12)
                padding: [dp(12), dp(8)]
                Widget:
                DangerButton:
                    text: "Cancel"
                    size_hint_x: None
                    width: dp(110)
                    on_release: root.dismiss()
                EmeraldButton:
                    text: "Open Selected"
                    size_hint_x: None
                    width: dp(140)
                    on_release: root.confirm_selection()

<FileSaveModal>:
    size_hint: 0.75, 0.48
    auto_dismiss: False
    background_color: 0, 0, 0, 0.6

    ModernCard:
        orientation: 'vertical'
        padding: dp(18)
        spacing: dp(12)

        Label:
            text: "💾 Save CSV As"
            font_size: '18sp'
            bold: True
            color: app.accent_normal
            size_hint_y: None
            height: dp(24)
            halign: 'left'
            text_size: self.size

        BoxLayout:
            size_hint_y: None
            height: dp(36)
            spacing: dp(8)
            padding: [dp(8), 0]
            Button:
                text: 'Home'
                size_hint_x: None
                width: dp(90)
                on_release: root.go_home()
            Button:
                text: 'Up'
                size_hint_x: None
                width: dp(90)
                on_release: root.go_up()
            Label:
                text: root.start_path
                halign: 'left'
                text_size: self.size

        FileChooserListView:
            id: file_chooser
            path: root.start_path
            size_hint: 1, 1
            multiselect: False

        BoxLayout:
            size_hint_y: None
            height: dp(42)
            spacing: dp(10)
            Label:
                text: "File name:"
                size_hint_x: None
                width: dp(80)
                bold: True
            TextInput:
                id: save_name
                text: root.default_name
                multiline: False
                background_color: 0.08, 0.12, 0.18, 1
                foreground_color: 1, 1, 1, 1
                cursor_color: app.accent_normal
                padding: [dp(10), dp(8)]

        BoxLayout:
            size_hint_y: None
            height: dp(46)
            spacing: dp(12)
            padding: [dp(12), dp(8)]
            Widget:
            DangerButton:
                text: "Cancel"
                size_hint_x: None
                width: dp(110)
                on_release: root.dismiss()
            EmeraldButton:
                text: "Save CSV"
                size_hint_x: None
                width: dp(140)
                on_release: root.confirm_selection()
"""

Builder.load_string(KV_STYLE)

class ParamRow(RecycleDataViewBehavior, BoxLayout):
    param_name = StringProperty('')
    raster = StringProperty('')
    index = NumericProperty(0)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

class ModernTreeNode(TreeViewLabel):
    pass

class FileSelectModal(ModalView):
    start_path = StringProperty(os.path.expanduser('~'))

    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback

    def go_home(self):
        try:
            self.ids.file_chooser.path = self.start_path
        except Exception:
            pass

    def go_up(self):
        try:
            current = self.ids.file_chooser.path
            parent = os.path.dirname(current)
            if parent and parent != current:
                self.ids.file_chooser.path = parent
        except Exception:
            pass

    def confirm_selection(self):
        selection = self.ids.file_chooser.selection
        if selection:
            self.callback(selection[0])
            self.dismiss()

class FileSaveModal(ModalView):
    start_path = StringProperty(os.path.expanduser('~'))
    default_name = StringProperty('parameters_export.csv')

    def __init__(self, callback, default_name='parameters_export.csv', **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.default_name = default_name

    def go_home(self):
        try:
            self.ids.file_chooser.path = self.start_path
        except Exception:
            pass

    def go_up(self):
        try:
            current = self.ids.file_chooser.path
            parent = os.path.dirname(current)
            if parent and parent != current:
                self.ids.file_chooser.path = parent
        except Exception:
            pass

    def confirm_selection(self):
        selected_dir = self.ids.file_chooser.path
        filename = self.ids.save_name.text.strip() or self.default_name
        if not filename.lower().endswith('.csv'):
            filename = f"{filename}.csv"

        full_path = os.path.join(selected_dir, filename)
        self.callback(full_path)
        self.dismiss()

class RootStudioLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parameters_data = []
        self.unique_rasters = set()
        self.sort_key = 'param_name'
        self.sort_desc = False
        
        # Setup TreeView widget inside the tree tab container
        # Use size_hint_y=None so ScrollView can scroll; bind minimum_height to height
        self.tree_view = TreeView(hide_root=True, indent_level=dp(20), size_hint=(1, None))
        # update tree height automatically when content changes
        self.tree_view.bind(minimum_height=self.tree_view.setter('height'))
        # keep the surrounding container height in sync
        self.tree_view.bind(height=lambda inst, val: setattr(self.ids.tree_container, 'height', val))
        self.ids.tree_container.add_widget(self.tree_view)
        
        # Bind native OS Drag and Drop
        Window.bind(on_drop_file=self.on_window_drop_file)

    def on_window_drop_file(self, window, file_path, x, y):
        decoded_path = file_path.decode('utf-8')
        if decoded_path.lower().endswith(('.xml', '.lab')):
            self.process_file(decoded_path)
            self.ids.header_status.text = f"Dropped: {os.path.basename(decoded_path)}"

    def switch_tab(self, tab_name):
        if tab_name == 'tree':
            self.ids.tab_btn_tree.selected = True
            self.ids.tab_btn_table.selected = False
            self.ids.tab_manager.current = 'tree_screen'
        else:
            self.ids.tab_btn_table.selected = True
            self.ids.tab_btn_tree.selected = False
            self.ids.tab_manager.current = 'table_screen'

    def open_file_dialog(self):
        modal = FileSelectModal(callback=self.process_file)
        modal.open()

    def clear_file(self):
        self.parameters_data.clear()
        self.unique_rasters.clear()
        self.sort_key = 'param_name'
        self.sort_desc = False
        
        # Clear TreeView
        for node in list(self.tree_view.iterate_all_nodes()):
            try:
                self.tree_view.remove_node(node)
            except Exception:
                pass

        # Clear Table and Controls
        self.ids.params_table.data = []
        self.ids.raster_spinner.values = ['All']
        self.ids.raster_spinner.text = 'All'
        self.ids.search_box.text = ''
        self.ids.lbl_filename.text = "No file selected"
        self.ids.lbl_total_count.text = "Total Parameters: 0"
        self.ids.lbl_rasters.text = "• None"
        self.ids.header_status.text = "File cleared"

    def process_file(self, filepath):
        self.clear_file()
        file_name = os.path.basename(filepath)
        self.ids.lbl_filename.text = file_name

        try:
            if filepath.lower().endswith(".lab"):
                self.parse_lab(filepath)
            else:
                self.parse_xml(filepath)

            # Populate Rasters dropdown
            raster_list = ["All"] + sorted(list(self.unique_rasters))
            self.ids.raster_spinner.values = raster_list
            self.ids.raster_spinner.text = "All"
            
            self.update_metadata_summary()
            self.apply_filter()
            self.ids.header_status.text = f"Successfully loaded {file_name}"

        except Exception as e:
            self.ids.header_status.text = f"Error: {str(e)}"
            self.clear_file()

    def parse_xml(self, filepath):
        tree = ET.parse(filepath)
        root = tree.getroot()
        self._populate_xml_tree(None, root)

    def _populate_xml_tree(self, parent_node, element):
        param_name = element.attrib.get('Name', '')
        raster = element.attrib.get('Raster', '')
        attrs = str(element.attrib) if element.attrib else ""
        text = element.text.strip() if element.text and element.text.strip() else ""

        label_parts = [f"<{element.tag}>"]
        if attrs:
            label_parts.append(f"Attrs: {attrs}")
        if text:
            label_parts.append(f"Text: {text}")
        node_text = " | ".join(label_parts)

        node = ModernTreeNode(text=node_text, is_open=(parent_node is None))
        self.tree_view.add_node(node, parent_node)

        if param_name:
            r_val = raster if raster else "[No Raster]"
            self.parameters_data.append((param_name, r_val))
            self.unique_rasters.add(r_val)

        for child in element:
            self._populate_xml_tree(node, child)

    def parse_lab(self, filepath):
        current_group = "[Root Data]"
        current_group_node = ModernTreeNode(text=f"Group: {current_group}", is_open=True)
        self.tree_view.add_node(current_group_node)

        with open(filepath, 'r', encoding='utf-8', errors='replace') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('//'):
                    continue

                if line.startswith('[') and line.endswith(']'):
                    current_group = line[1:-1]
                    current_group_node = ModernTreeNode(text=f"Group: {current_group}", is_open=True)
                    self.tree_view.add_node(current_group_node)
                else:
                    parts = line.split(';')
                    param_name = parts[0].strip()
                    raster = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "[No Raster]"
                    attrs = ";".join(parts[2:]).strip() if len(parts) > 2 else ""

                    label = f"Param: {param_name} | Raster: {raster}"
                    if attrs:
                        label += f" | {attrs}"

                    node = ModernTreeNode(text=label)
                    self.tree_view.add_node(node, current_group_node)

                    self.parameters_data.append((param_name, raster))
                    self.unique_rasters.add(raster)

    def update_metadata_summary(self):
        total_count = len(self.parameters_data)
        self.ids.lbl_total_count.text = f"Total Parameters: {total_count}"

        raster_counts = Counter(raster for _, raster in self.parameters_data)
        if raster_counts:
            lines = [f"• {raster}: {count}" for raster, count in sorted(raster_counts.items())]
            self.ids.lbl_rasters.text = "\n".join(lines)
        else:
            self.ids.lbl_rasters.text = "• None"

    def sort_table(self, key):
        if self.sort_key == key:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_key = key
            self.sort_desc = False
        self.apply_filter()

    def apply_filter(self):
        selected_raster = self.ids.raster_spinner.text
        search_query = self.ids.search_box.text.lower().strip()

        filtered_rows = []
        for param, raster in self.parameters_data:
            raster_match = (selected_raster == "All" or raster == selected_raster)
            search_match = (not search_query or search_query in param.lower())
            if raster_match and search_match:
                filtered_rows.append({'param_name': param, 'raster': raster})

        if self.sort_key == 'param_name':
            filtered_rows.sort(key=lambda item: item['param_name'].lower(), reverse=self.sort_desc)
        else:
            filtered_rows.sort(key=lambda item: item['raster'].lower(), reverse=self.sort_desc)

        self.ids.params_table.data = filtered_rows

    def copy_parameters(self):
        visible_rows = self.ids.params_table.data
        if not visible_rows:
            self.ids.header_status.text = "Nothing to copy."
            return

        param_names = [item['param_name'] for item in visible_rows]
        Clipboard.copy("\n".join(param_names))
        self.ids.header_status.text = f"Copied {len(param_names)} parameters to clipboard!"

    def export_to_csv(self):
        visible_rows = self.ids.params_table.data
        if not visible_rows:
            self.ids.header_status.text = "No parameters available to export."
            return

        modal = FileSaveModal(callback=lambda out_path: self.save_csv_data(out_path, visible_rows))
        modal.open()

    def save_csv_data(self, out_path, visible_rows):
        if not out_path:
            self.ids.header_status.text = "Export cancelled."
            return

        try:
            with open(out_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Parameter Name", "Raster"])
                for item in visible_rows:
                    writer.writerow([item['param_name'], item['raster']])

            self.ids.header_status.text = f"Saved: {out_path}"
        except Exception as e:
            self.ids.header_status.text = f"Export failed: {str(e)}"

class XMLStudioApp(App):
    theme = StringProperty('light')
    # color properties are ListProperty so KV can read them for dynamic theming
    card_bg = ListProperty([0.88, 0.91, 0.90, 1])
    card_border = ListProperty([0.66, 0.78, 0.76, 1])
    accent_normal = ListProperty([0.18, 0.48, 0.86, 1])
    accent_down = ListProperty([0.12, 0.39, 0.72, 1])
    bg_main = ListProperty([0.718, 0.820, 0.811, 1])  # #B7D1CF
    text_primary = ListProperty([0.08, 0.12, 0.14, 1])
    text_secondary = ListProperty([0.28, 0.33, 0.39, 1])
    # row and header colors
    row_bg_even = ListProperty([0.90, 0.93, 0.92, 1])
    row_bg_odd = ListProperty([0.86, 0.90, 0.89, 1])
    row_header = ListProperty([0.80, 0.86, 0.85, 1])

    def asset_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)

    def build(self):
        self.title = "XML || LAB Parameter Studio"
        Window.clearcolor = self.bg_main
        Window.set_icon(self.asset_path('Asset/documentation.icns'))
        return RootStudioLayout()

    def toggle_theme(self):
        # switch between dark and light themes; user-specified palette
        if self.theme == 'dark':
            self.theme = 'light'
            self.bg_main = [0.718, 0.820, 0.811, 1]  # #B7D1CF
            self.card_bg = [0.88, 0.91, 0.90, 1]
            self.card_border = [0.66, 0.78, 0.76, 1]
            self.accent_normal = [0.18, 0.48, 0.86, 1]
            self.accent_down = [0.12, 0.39, 0.72, 1]
            self.text_primary = [0.08, 0.12, 0.14, 1]
            self.text_secondary = [0.28, 0.33, 0.39, 1]
            self.row_bg_even = [0.90, 0.93, 0.92, 1]
            self.row_bg_odd = [0.86, 0.90, 0.89, 1]
            self.row_header = [0.80, 0.86, 0.85, 1]
        else:
            self.theme = 'dark'
            self.bg_main = [0.0, 0.0, 0.0, 1]  # #000000
            self.card_bg = [0.08, 0.08, 0.08, 1]
            self.card_border = [0.18, 0.18, 0.18, 1]
            self.accent_normal = [0.388, 0.400, 0.945, 1]
            self.accent_down = [0.290, 0.300, 0.780, 1]
            self.text_primary = [1, 1, 1, 1]
            self.text_secondary = [0.75, 0.75, 0.75, 1]
            self.row_bg_even = [0.12, 0.12, 0.12, 1]
            self.row_bg_odd = [0.08, 0.08, 0.08, 1]
            self.row_header = [0.16, 0.16, 0.16, 1]
        Window.clearcolor = self.bg_main

if __name__ == "__main__":
    XMLStudioApp().run()