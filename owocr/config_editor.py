import configparser
import os
import inspect
import sys
import time
import importlib.resources

from .ocr import *
from .config import Config

if sys.platform == 'win32':
    import ctypes

try:
    import tkinter as tk
    from tkinter import PhotoImage, ttk, messagebox, filedialog
    editor_available = True
except:
    editor_available = False


class GlobalImport:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        caller_frame = inspect.getouterframes(inspect.currentframe())[1].frame
        collector = inspect.getargvalues(caller_frame).locals
        caller_frame.f_globals.update(collector)

class HotkeyRecorder:
    def __init__(self):
        with GlobalImport():
            from pynputfix import keyboard
        self.listener = None
        self.recording = False
        self.current_keys = set()
        self.current_pynput_keys = set()
        self.window_scale = 1
        self.popup = None
        self.on_hotkey_recorded = None
        self.cancelled = False

    def start_listener(self):
        def on_press(key):
            if not self._should_handle_event():
                return

            key_str = None
            try:
                key_str = self.listener.canonical(key).char
            except AttributeError:
                pass
            if not key_str:
                key_str = str(key)[4:]
                if key_str.endswith('_l') or key_str.endswith('_r'):
                    key_str = key_str[:-2]
                key_str = f'<{key_str}>'

            self.current_pynput_keys.add(key_str)
            self.current_keys.add(key_str)
            self._update_popup_label()

        def on_release(key):
            if not self._should_handle_event():
                return

            key_str = None
            try:
                key_str = self.listener.canonical(key).char
            except AttributeError:
                pass
            if not key_str:
                key_str = str(key)[4:]
                if key_str.endswith('_l') or key_str.endswith('_r'):
                    key_str = key_str[:-2]
                key_str = f'<{key_str}>'

            self.current_pynput_keys.discard(key_str)

            if not self.current_pynput_keys:
                self.finish_recording()

        self.listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        self.listener.start()
        if sys.platform != 'linux':
            self.listener.wait()

    def stop_listener(self):
        self.listener.stop()
        if sys.platform != 'linux':
            self.listener.join()

    def _should_handle_event(self):
        if not self.recording:
            return False
        if not self.popup or not self.popup.winfo_exists():
            self.stop_recording()
            return False
        return True

    def start_recording(self, parent_widget):
        if self.recording:
            if self.popup:
                self.popup.focus_force()
            return

        self.recording = True
        self.current_keys = set()
        self.current_pynput_keys = set()
        self.cancelled = False

        self._create_popup_window(parent_widget)
        self._update_popup_label()
        self.popup.focus_force()

    def _create_popup_window(self, parent_widget):
        self.popup = tk.Toplevel(parent_widget)
        self.popup.title('Record Hotkey')

        width = int(300 * self.window_scale)
        height = int(100 * self.window_scale)
        self.popup.geometry(f'{width}x{height}')
        self.popup.resizable(False, False)

        self._center_popup(parent_widget, width, height)
        self._make_popup_modal(parent_widget)
        self._create_popup_content()

    def _center_popup(self, parent_widget, width, height):
        popup_x = parent_widget.winfo_rootx() + parent_widget.winfo_width() // 2 - width // 2
        popup_y = parent_widget.winfo_rooty() + parent_widget.winfo_height() // 2 - height // 2
        self.popup.geometry(f'+{popup_x}+{popup_y}')

    def _make_popup_modal(self, parent_widget):
        self.popup.transient(parent_widget)
        self.popup.grab_set()

    def _create_popup_content(self):
        self.label_var = tk.StringVar(value='Press any key combination...\n(Click to cancel)')
        self.label = ttk.Label(self.popup, textvariable=self.label_var, justify=tk.CENTER, anchor=tk.CENTER)
        self.label.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        for widget in [self.popup, self.label]:
            widget.bind('<Button-1>', lambda _: self.cancel_recording())

    def _update_popup_label(self):
        if self.current_keys:
            keys = sorted(self.current_keys)
            hotkey_str = '+'.join(keys)
            text = f'Current: {hotkey_str}\n(Release all keys to finish)'
        else:
            text = 'Press any key combination...\n(Click to cancel)'

        self.label_var.set(text)

    def finish_recording(self):
        if self.current_keys and not self.cancelled and self.on_hotkey_recorded:
            keys = sorted(self.current_keys)
            hotkey_str = '+'.join(keys)
            self.on_hotkey_recorded(hotkey_str)

        self.stop_recording()

    def cancel_recording(self):
        self.cancelled = True
        self.stop_recording()

    def stop_recording(self):
        self.recording = False
        self.current_keys.clear()
        self.current_pynput_keys.clear()
        if self.popup and self.popup.winfo_exists():
            self.popup.grab_release()
            self.popup.destroy()
            self.popup = None


class ConfigGUI:
    def __init__(self, root):
        self.root = root
        self.config_path = Config.config_path
        self.is_bundled = getattr(sys, 'frozen', False)

        self._setup_window()
        self._initialize_styles()

        self.categories = {}
        self.widgets = {}
        self.default_values = {}
        self.engine_config_widgets = {}
        self.tab_canvases = {}
        self.tab_scrollable_frames = {}
        self.tab_scrollbars = {}

        self._load_categories_and_defaults()
        self._get_engine_info()
        self._create_widgets()
        self._load_config()

    def _setup_window(self):
        self.root.title('owocr Configuration Editor')
        icon_path = importlib.resources.files(__name__).joinpath('data', 'icon.png')
        icon = PhotoImage(file=icon_path)
        self.root.iconphoto(True, icon)

        width, height = 750, 750
        window_scale = 1.0
        if sys.platform == 'win32':
            hwnd = self.root.winfo_id()
            dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
            window_scale = dpi / 96.0
            hotkey_recorder.window_scale = window_scale

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = int(width * window_scale)
        height = int(height * window_scale)
        x = screen_width // 2 - width // 2
        y = screen_height // 2 - height // 2

        self.root.geometry(f'{width}x{height}+{x}+{y}')
        self.root.resizable(False, False)

    def _initialize_styles(self):
        style = ttk.Style()

        if sys.platform == 'linux':
            style.theme_use('alt')
        font_family = 'Segoe UI' if sys.platform == 'win32' else 'TkTextFont'
        style.configure('Category.TLabelframe', font=(font_family, 11, 'bold'))
        style.configure('Help.TLabel', font=(font_family, 9), foreground='gray')
        style.configure('TNotebook.Tab', padding=(10, 3))

    def _load_categories_and_defaults(self):
        self.default_values = Config.default_config
        self.general_config_options = {
            'General': [
                ('read_from', 'dropdown', 'Input source', ['clipboard', 'websocket', 'unixsocket', 'screencapture', 'obs']),
                ('read_from_secondary', 'dropdown', 'Optional secondary input source', ['', 'clipboard', 'websocket', 'unixsocket', 'screencapture', 'obs']),
                ('write_to', 'dropdown', 'Output destination', ['clipboard', 'websocket']),
                ('websocket_port', 'int', 'Websocket port'),
                ('delay_seconds', 'float', 'Check the clipboard/directory every X seconds (ignored on Windows/Wayland)'),
                ('delete_images', 'bool', 'Delete images from the folder after processing'),
                ('skip_existing_images', 'bool', 'Ignore images already in the folder when owocr starts'),
                ('pause_at_startup', 'bool', 'Pause when owocr starts'),
                ('notifications', 'bool', 'Show OS notifications with the detected text'),
                ('tray_icon', 'bool', 'Show an OS tray icon to change the engine, pause/unpause,\nchange the screen capture area selection, take a screenshot\nand launch this configuration'),
                ('show_log_at_startup', 'bool', 'Show the log viewer window when owocr starts'),
                ('auto_pause', 'float', 'Automatically pause after X seconds of inactivity (0 to disable)'),
                ('language', 'dropdown', 'Language code, used for some engines and to cleanup screen capture text', ['ja', 'en', 'zh', 'ko', 'ar', 'ru', 'el', 'he', 'th']),
                ('output_format', 'dropdown', 'Output format', ['text', 'json']),
                ('verbosity', 'int', 'Terminal/log window verbosity level:\n-2: show everything\n-1: only timestamps\n0: only errors\nGreater than 0: maximum amount of characters'),
            ],
            'Engines': [
                ('engines', 'multicheckbox', 'List of enabled OCR engines'),
                ('engine', 'dropdown', 'Primary OCR engine'),
                ('engine_secondary', 'dropdown', 'Optional secondary OCR engine for screen capture'),
            ],
            'Screen capture': [
                ('screen_capture_area', 'special_screen_capture_area', 'Area to capture'),
                ('screen_capture_window_area', 'special_screen_capture_window_area', 'Window subsection to capture'),
                ('screen_capture_only_active_windows', 'bool', "Only capture a window while it's not in the background"),
                ('screen_capture_delay_seconds', 'float', 'Capture every X seconds (-1 to disable continuous capture)'),
                ('screen_capture_frame_stabilization', 'float', 'Wait X seconds until text is stable:\n-1: wait for two frames\n0: disable (faster, only works when text is shown all at once)'),
                ('screen_capture_line_recovery', 'bool', 'Try to recover lines missed by frame stabilization (can increase glitches)'),
                ('screen_capture_regex_filter', 'str', 'Regex filter for unwanted text'),
                ('screen_capture_wayland_persistence', 'bool', 'On Wayland, persist the session when owocr is restarted (ignored on other platforms)'),
            ],
            'OBS': [
                ('obs_host', 'str', 'OBS websocket host'),
                ('obs_port', 'int', 'OBS websocket port'),
                ('obs_password', 'str', 'OBS password (leave blank if authentication is disabled)'),
                ('obs_quality', 'int', 'JPEG quality for captured images (-1 for lossless PNG)'),
                ('obs_source_override', 'str', 'Source name to capture from (leave blank for current scene, "preview" for preview scene)'),
            ],
            'Hotkeys': [
                ('combo_pause', 'str', 'Pause/resume hotkey'),
                ('combo_engine_switch', 'str', 'OCR engine switch hotkey'),
                ('screen_capture_combo', 'str', 'Capture hotkey'),
                ('coordinate_selector_combo', 'str', 'Screen capture area selection hotkey'),
            ],
            'Processing': [
                ('join_lines', 'bool', 'Join lines without separators'),
                ('join_paragraphs', 'bool', 'Join paragraphs without separators'),
                ('line_separator', 'str', 'Custom line separator (supports special characters like \\n for a newline)'),
                ('paragraph_separator', 'str', 'Custom paragraph separator (supports special characters like \\n for a newline)'),
                ('reorder_text', 'bool', 'Regroup and reorder text. If disabled, text is shown as-is from the OCR engine'),
                ('furigana_filter', 'bool', 'Filter out furigana lines for Japanese if reorder_text is enabled'),
                ('merge_close_paragraphs', 'bool', 'If reorder_text is enabled, merge paragraphs that are close to each other in\nthe reading direction. Can be useful if there are gaps in the middle of lines,\nbut cause glitches in others'),
                ('support_center_aligned_text', 'bool', 'If reorder_text is enabled, support horizontal text that is center-aligned')
            ],
            'Advanced': [
                ('screen_capture_old_macos_api', 'bool', 'Use old macOS window screen capture API (faster, recommended for now)'),
                ('wayland_use_wlclipboard', 'bool', 'Use wl-clipboard on Wayland instead of the built-in clipboard code.\nUses more resources and steals focus. Only needed on e.g. GNOME'),
            ]
        }
        self.engine_config_options = {
            'winrtocr': [
                ('url', 'str', 'URL for WinRT OCR service (ignored on Windows)', 'http://aaa.xxx.yyy.zzz:8000'),
            ],
            'oneocr': [
                ('url', 'str', 'URL for OneOCR service (ignored on Windows)', 'http://aaa.xxx.yyy.zzz:8001'),
            ],
            'azure': [
                ('api_key', 'str', 'Azure API key', 'api_key_here'),
                ('endpoint', 'str', 'Azure endpoint', 'https://YOURPROJECT.cognitiveservices.azure.com/'),
            ],
            'mangaocr': [
                ('pretrained_model_name_or_path', 'str', 'Model name or path', 'kha-white/manga-ocr-base'),
                ('force_cpu', 'bool', 'Force CPU usage', False),
            ],
            'hayaiocr': [
                ('hayainova_path', 'str', 'Hayai v2.5-nova model name or path', 'JustANormalTinkerer/hayai-ocr-v2.5-nova'),
                ('hayaiv2_path', 'str', 'Hayai v2 model name or path', 'JustANormalTinkerer/hayai-ocr-v2'),
                ('hayaiv1_path', 'str', 'Hayai v1 model name or path', 'JustANormalTinkerer/hayai-ocr'),
                ('use_v2', 'bool', 'Use the previous Hayai v2 model instead of v2.5-nova', False),
                ('use_v1', 'bool', 'Use the legacy Hayai v1 model', False),
                ('backend', 'dropdown', 'Backend', ['torch', 'litert']),
                ('force_cpu', 'bool', 'Force CPU usage', False),
                ('quantize', 'str', 'Torch quantization: int4, int8, or blank', ''),
                ('litert_quant', 'str', 'LiteRT quantization (wi4, wi8_afp32, dynamic_wi4, dynamic_wi8)', 'wi4'),
                ('litert_model_path', 'str', 'Local LiteRT model directory (blank = download)', ''),
                ('litert_threads', 'int', 'LiteRT threads (0 = automatic)', 0),
                ('compile', 'bool', 'Use torch.compile for the torch backend', True),
                ('max_num_patches', 'int', 'Torch NaFlex patch budget (0 = Hayai default)', 0),
            ],
            'easyocr': [
                ('gpu', 'bool', 'Use GPU if available', True),
            ],
            'ocrspace': [
                ('api_key', 'str', 'OCR.space API key', 'api_key_here'),
                ('engine_version', 'int', 'Engine version (1 or 2)', 2),
            ],
            'rapidocr': [
                ('high_accuracy_detection', 'bool', 'Use high accuracy detection', False),
                ('high_accuracy_recognition', 'bool', 'Use high accuracy recognition', True),
            ],
            'avision': [
                ('fast_mode', 'bool', 'Use fast mode', False),
                ('language_correction', 'bool', 'Enable language correction', True),
            ]
        }

    def _get_engine_info(self):
        self.all_engines = []
        self.secondary_engines = []
        self.engine_name_to_class = {}
        self.engine_class_to_display = {}
        self.config_entry_to_engines = {}
        for _, engine_class in inspect.getmembers(sys.modules[__name__], self._is_engine_class):
            self._process_engine_class(engine_class)

    def _is_engine_class(self, obj):
        return inspect.isclass(obj) and hasattr(obj, '__module__') and obj.__module__ and __package__ + '.ocr' in obj.__module__ and hasattr(obj, 'name')

    def _process_engine_class(self, engine_class):
        internal_name = engine_class.name
        display_name = engine_class.readable_name

        self.all_engines.append(display_name)
        self.engine_name_to_class[display_name] = engine_class
        self.engine_class_to_display[internal_name] = display_name

        config_entry = engine_class.config_entry

        if config_entry is not None:
            if config_entry not in self.config_entry_to_engines:
                self.config_entry_to_engines[config_entry] = []
            self.config_entry_to_engines[config_entry].append(display_name)

        if engine_class.local and engine_class.coordinate_support:
            self.secondary_engines.append(display_name)

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        if sys.platform == 'darwin':
            notebook_padding = 0
            status_bar_padding = 20
        else:
            notebook_padding = 10
            status_bar_padding = 10

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, notebook_padding))

        self._create_category_tabs()
        self._create_buttons(main_frame)

        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var,relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(status_bar_padding, 0))

        self._configure_grid_weights(main_frame)

    def _create_category_tabs(self):
        self.tabs = {}
        for category, options in self.general_config_options.items():
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=category)
            self.tabs[category] = tab
            self._create_scrollable_tab(tab, category, options)

    def _create_scrollable_tab(self, parent, category, options):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        self.tab_canvases[category] = canvas
        self.tab_scrollable_frames[category] = scrollable_frame
        self.tab_scrollbars[category] = scrollbar

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor=tk.NW, tags='scrollable_frame')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        self._configure_canvas_scrolling(canvas, scrollbar, scrollable_frame, canvas_window)

        row = 0
        for option_data in options:
            row = self._create_option_widget(scrollable_frame, option_data, row, category)

        if category == 'Engines':
            row = self._add_engine_configuration_sections(scrollable_frame, row)

        scrollable_frame.columnconfigure(1, weight=1)

        return canvas

    def _configure_canvas_scrolling(self, canvas, scrollbar, scrollable_frame, canvas_window):
        def update_scrollable_frame_height(event):
            canvas_height = event.height
            canvas_width = event.width

            scrollable_frame.update_idletasks()
            frame_height = scrollable_frame.winfo_reqheight()

            if frame_height <= canvas_height:
                scrollbar.grid_remove()
            else:
                scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S), padx=(5, 0))

            canvas.itemconfig(canvas_window, width=canvas_width, height=max(frame_height, canvas_height))
            canvas.configure(scrollregion=canvas.bbox('all'))

        def _on_mousewheel(event):
            if scrollbar.winfo_ismapped():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        def _on_scroll(event):
            def precise_scroll_deltas(dxdy):
                deltaX = dxdy >> 16
                low = dxdy & 0xFFFF
                deltaY = low if low < 0x8000 else low - 0x10000
                return deltaX, deltaY

            if scrollbar.winfo_ismapped():
                _, delta_y = precise_scroll_deltas(event.delta)
                canvas.yview_scroll(int(-1 * (delta_y / 5)), 'units')

        def _on_enter(event):
            canvas.bind_all('<MouseWheel>', _on_mousewheel)
            if sys.platform == 'darwin':
                canvas.bind_all('<TouchpadScroll>', _on_scroll)

        def _on_leave(event):
            canvas.unbind_all('<MouseWheel>')
            if sys.platform == 'darwin':
                canvas.unbind_all('<TouchpadScroll>')

        canvas.bind('<Configure>', update_scrollable_frame_height)
        canvas.bind('<Enter>', _on_enter)
        canvas.bind('<Leave>', _on_leave)

    def _create_buttons(self, parent):
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=2, column=0, columnspan=2)

        ttk.Button(button_frame, text='Save', command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text='Reset to Defaults', command=self.reset_to_defaults).pack(side=tk.LEFT, padx=5)

    def _configure_grid_weights(self, main_frame):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

    def _create_option_widget(self, parent, option_data, row, category):
        if len(option_data) == 4:
            option, opt_type, help_text, dropdown_values = option_data
        else:
            option, opt_type, help_text = option_data
            dropdown_values = None

        if option == 'tray_icon' and self.is_bundled:
            return row
        if option == 'show_log_at_startup' and not self.is_bundled:
            return row

        if 'special_screen_capture' in opt_type:
            is_window_area = 'window_area' in opt_type
            return self._create_screen_capture_widget(parent, option, help_text, row, is_window_area)

        frame = self._create_option_frame(parent, row)

        ttk.Label(frame, text=f'{option}:').grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        input_frame = ttk.Frame(frame)
        input_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))

        var, widget = self._create_widget_by_type(opt_type, input_frame, option, dropdown_values)

        ttk.Label(frame, text=help_text, style='Help.TLabel').grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))

        self.widgets[option] = {
            'var': var,
            'widget': widget,
            'type': opt_type,
            'frame': frame
        }

        if option in ['read_from', 'read_from_secondary', 'write_to']:
            var.trace_add('write', lambda *_: self._update_general_state())

        self._add_option_buttons(input_frame, option, var, widget, category)

        frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(0, weight=1)

        return row + 1

    def _create_option_frame(self, parent, row):
        frame = ttk.Frame(parent, padding=5)
        frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=2)
        return frame

    def _create_widget_by_type(self, widget_type, parent, option, dropdown_values):
        widget_creators = {
            'bool': self._create_bool_widget,
            'int': self._create_int_widget,
            'float': self._create_float_widget,
            'dropdown': self._create_dropdown_widget,
            'multicheckbox': self._create_multicheckbox_widget,
            'str': self._create_string_widget
        }

        creator = widget_creators[widget_type]
        return creator(parent, option, dropdown_values)

    def _create_bool_widget(self, parent, option, dropdown_values):
        var = tk.BooleanVar()
        widget = ttk.Checkbutton(parent, variable=var)
        widget.pack(side=tk.LEFT, fill=tk.X)
        return var, widget

    def _create_int_widget(self, parent, option, dropdown_values):
        var = tk.StringVar()
        widget = ttk.Spinbox(parent, textvariable=var, from_=-2, to=1000)
        widget.pack(side=tk.LEFT, fill=tk.X)
        return var, widget

    def _create_float_widget(self, parent, option, dropdown_values):
        var = tk.StringVar()
        widget = ttk.Spinbox(parent, textvariable=var, from_=-1.0, to=1000.0, increment=0.1, format='%.1f')
        widget.pack(side=tk.LEFT, fill=tk.X)
        return var, widget

    def _create_dropdown_widget(self, parent, option, dropdown_values):
        var = tk.StringVar()

        if option == 'engine':
            dropdown_values = [''] + self.all_engines
        elif option == 'engine_secondary':
            dropdown_values = [''] + self.secondary_engines

        widget = ttk.Combobox(parent, textvariable=var, values=dropdown_values, state='readonly')
        widget.pack(side=tk.LEFT, fill=tk.X)
        return var, widget

    def _create_multicheckbox_widget(self, parent, option, dropdown_values):
        checkbox_frame = ttk.Frame(parent)
        checkbox_frame.pack(side=tk.LEFT, fill=tk.X)

        vars_dict = {}
        for i, display_name in enumerate(self.all_engines):
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(checkbox_frame, text=display_name, variable=var)
            row_pos = i // 3
            col_pos = i % 3
            cb.grid(row=row_pos, column=col_pos, sticky=tk.W, padx=10, pady=2)
            vars_dict[display_name] = var

            var.trace_add('write', lambda *_: self._update_engine_state())

        return vars_dict, checkbox_frame

    def _create_string_widget(self, parent, option, dropdown_values):
        var = tk.StringVar()
        widget = ttk.Entry(parent, textvariable=var)
        widget.pack(side=tk.LEFT, fill=tk.X)
        return var, widget

    def _add_option_buttons(self, input_frame, option, var, widget, category):
        if option in ['read_from', 'read_from_secondary', 'write_to']:
            ttk.Button(input_frame, text='...', width=2, command=lambda: self._open_picker(option, var)).pack(side=tk.LEFT, padx=(5, 0))
            widget.pack(expand=True)

        if category == 'Hotkeys':
            ttk.Button(input_frame, text='...', width=2, command=lambda: self._start_hotkey_recording(option)).pack(side=tk.LEFT, padx=(5, 0))
            widget.pack(expand=True)

    def _create_screen_capture_widget(self, parent, option, help_text, row, is_window_area=False):
        frame = self._create_option_frame(parent, row)

        ttk.Label(frame, text=f'{option}:').grid(row=0, column=0, sticky=tk.W, padx=(0, 10))

        input_frame = ttk.Frame(frame)
        input_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))

        if is_window_area:
            dropdown_values = ['automatic selection', 'coordinates', 'entire window']
            placeholder_texts = {'coordinates': 'x1,y1,x2,y2'}
        else:
            dropdown_values = ['automatic selection', 'coordinates', 'entire screen', 'window']
            placeholder_texts = {
                'coordinates': 'x1,y1,x2,y2',
                'entire screen': '1',
                'window': 'window name'
            }

        dropdown_var = tk.StringVar()
        dropdown = ttk.Combobox(input_frame, textvariable=dropdown_var, values=dropdown_values, state='readonly')
        dropdown.pack(side=tk.LEFT, fill=tk.X)

        text_var = tk.StringVar()
        textbox = ttk.Entry(input_frame, textvariable=text_var, width=20)

        def update_textbox_visibility():
            mode = dropdown_var.get()
            if mode in placeholder_texts:
                textbox.pack(side=tk.LEFT, fill=tk.X, padx=(5, 0))
                textbox.delete(0, tk.END)
                textbox.insert(0, placeholder_texts[mode])
            else:
                textbox.pack_forget()
                text_var.set('')

        dropdown_var.trace_add('write', lambda *_: update_textbox_visibility())

        ttk.Label(frame, text=help_text, style='Help.TLabel').grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))

        widget_type = 'special_screen_capture_window_area' if is_window_area else 'special_screen_capture_area'
        self.widgets[option] = {
            'type': widget_type,
            'dropdown_var': dropdown_var,
            'text_var': text_var,
            'frame': frame
        }

        if not is_window_area:
            dropdown_var.trace_add('write', lambda *_: self._update_screen_capture_state())

        frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(0, weight=1)

        return row + 1

    def _add_engine_configuration_sections(self, parent, start_row):
        row = start_row

        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        row += 1

        self.engine_config_container = ttk.Frame(parent)
        self.engine_config_container.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E))
        self.engine_config_container.columnconfigure(1, weight=1)

        container_row = 0
        for config_entry, engine_names in self.config_entry_to_engines.items():
            self._create_engine_config_frame(config_entry, engine_names, container_row)
            container_row += 1

        return row + 1

    def _create_engine_config_frame(self, config_entry, engine_names, row):
        label_text = engine_names[0] if len(engine_names) == 1 else ', '.join(engine_names)

        frame = ttk.LabelFrame(self.engine_config_container, text=label_text, padding=10)
        frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 10), ipadx=5)
        frame.columnconfigure(1, weight=1)

        self.engine_config_widgets[config_entry] = {
            'frame': frame,
            'engine_names': engine_names,
            'widgets': {}
        }