import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import os
import json
import logging
from datetime import datetime
import pyperclip
import re
import webbrowser
from urllib.parse import urlparse, parse_qs

class FocusManager:
    def __init__(self, root):
        self.root = root
        self.setup_focus_management()
    
    def setup_focus_management(self):
        self.root.bind('<Button-1>', self.on_click)
        self.focusable_widgets = (
            ttk.Entry, ttk.Combobox, ttk.Spinbox, 
            scrolledtext.ScrolledText, tk.Text,
            ttk.Button, ttk.Checkbutton, ttk.Radiobutton
        )
    
    def on_click(self, event):
        widget = event.widget
        is_focusable = isinstance(widget, self.focusable_widgets)
        if not is_focusable:
            self.root.focus_set()
            
    def add_focusable_widget(self, widget):
        if hasattr(widget, 'bind'):
            widget.bind('<Button-1>', lambda e: None)

class LogPanel:
    def __init__(self, parent, focus_manager):
        self.parent = parent
        self.focus_manager = focus_manager
        self.auto_scroll = True
        self.user_scrolled = False
        self.create_widgets()
        
    def create_widgets(self):
        title_label = ttk.Label(self.parent, text="Application Log", font=('Arial', 10, 'bold'))
        title_label.pack(anchor='w', pady=(5, 3))
        
        self.log_text = scrolledtext.ScrolledText(self.parent, 
                                                font=('Consolas', 8), 
                                                wrap=tk.WORD,
                                                state='disabled',
                                                bg='#f8f9fa',
                                                height=12)
        self.log_text.pack(fill='both', expand=True, padx=5, pady=(0, 5))

        self.log_text.bind('<MouseWheel>', self.on_scroll)
        self.log_text.bind('<Button-4>', self.on_scroll)
        self.log_text.bind('<Button-5>', self.on_scroll)
        
        button_frame = ttk.Frame(self.parent)
        button_frame.pack(fill='x', padx=5, pady=(0, 5))
        
        self.clear_log_btn = ttk.Button(button_frame, text="Clear Log", command=self.clear_log)
        self.clear_log_btn.pack(side='left', padx=(0, 5))
        
        self.copy_log_btn = ttk.Button(button_frame, text="Copy Log", command=self.copy_log)
        self.copy_log_btn.pack(side='left')
        
        self.focus_manager.add_focusable_widget(self.log_text)
        self.focus_manager.add_focusable_widget(self.clear_log_btn)
        self.focus_manager.add_focusable_widget(self.copy_log_btn)
    
    def on_scroll(self, event):
        if event.delta > 0 or event.num == 4:
            self.user_scrolled = True
        elif self.is_at_bottom():
            self.user_scrolled = False
    
    def is_at_bottom(self):
        self.log_text.update_idletasks()
        return self.log_text.yview()[1] >= 0.99
    
    def add_log(self, message: str):
        try:
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, f"{message}\n")

            if not self.user_scrolled or self.is_at_bottom():
                self.log_text.see(tk.END)
                self.user_scrolled = False
            
            self.log_text.config(state='disabled')
        except Exception as e:
            print(f"Error adding log to GUI: {e}")
    
    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.user_scrolled = False
        log_manager.info("Log cleared")
    
    def copy_log(self):
        try:
            log_content = self.log_text.get(1.0, tk.END)
            if log_content.strip():
                pyperclip.copy(log_content)
                log_manager.info("Log copied to clipboard")
        except Exception as e:
            log_manager.error(f"Error copying log: {e}")

class Logger:
    def __init__(self, app_name="RobloxLinkConverter"):
        self.app_name = app_name
        self.gui_callback = None
        self.log_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'Roblox Link Converter', 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
        current_date = datetime.now().strftime('%Y%m%d')
        log_file = os.path.join(self.log_dir, f"{current_date}.log")
        
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'
        
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.INFO)
        
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(log_format, date_format)
        file_handler.setFormatter(file_formatter)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(log_format, date_format)
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"=== {app_name} Started ===")
        self.logger.info(f"Log file: {log_file}")
    
    def set_gui_callback(self, callback):
        self.gui_callback = callback
    
    def info(self, message: str):
        self.logger.info(message)
        self._update_gui(f"INFO - {message}")
    
    def warning(self, message: str):
        self.logger.warning(message)
        self._update_gui(f"WARNING - {message}")
    
    def error(self, message: str):
        self.logger.error(message)
        self._update_gui(f"ERROR - {message}")
    
    def _update_gui(self, message: str):
        if self.gui_callback:
            try:
                timestamp = datetime.now().strftime('%H:%M:%S')
                formatted_message = f"[{timestamp}] {message}"
                self.gui_callback(formatted_message)
            except Exception as e:
                print(f"Failed to update GUI log: {e}")

log_manager = Logger()

class ConfigManager:
    def __init__(self):
        self.app_data_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'Roblox Link Converter')
        self.config_file = os.path.join(self.app_data_dir, 'config.json')
        self.config = {}
        self.ensure_directories()
        self.load_or_create_config()
    
    def ensure_directories(self):
        os.makedirs(self.app_data_dir, exist_ok=True)
    
    def load_or_create_config(self):
        if not os.path.exists(self.config_file):
            self.create_default_config()
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except:
            self.create_default_config()
    
    def create_default_config(self):
        self.config = {
            "auto_execute": False
        }
        self.save_config()
    
    def get_value(self, key: str, default=None):
        return self.config.get(key, default)
    
    def set_value(self, key: str, value):
        self.config[key] = value
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {str(e)}")

class LinkConverter:
    def __init__(self, parent, config_manager, log_panel, main_gui, focus_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.log_panel = log_panel
        self.main_gui = main_gui
        self.focus_manager = focus_manager
        self.last_processed_link = ""
        self.create_widgets()
        self.setup_bindings()
        
    def setup_bindings(self):
        self.input_var.trace_add('write', self.on_input_changed)
        self.input_entry.bind('<FocusOut>', self.on_input_focus_out)
        self.input_entry.bind('<Return>', lambda e: self.convert_and_open())
        self.input_entry.bind('<KeyPress>', self.validate_input_length)
        
    def validate_input_length(self, event):
        current_text = self.input_var.get()
        if len(current_text) >= 200 and event.keysym not in ['BackSpace', 'Delete', 'Left', 'Right', 'Up', 'Down', 'Home', 'End']:
            return "break"
            
    def on_input_changed(self, *args):
        if self.auto_execute_var.get():
            self.parent.after(500, self.check_and_auto_convert)
            
    def on_input_focus_out(self, event):
        if self.auto_execute_var.get():
            self.check_and_auto_convert()
            
    def check_and_auto_convert(self):
        input_text = self.input_var.get().strip()
        
        if not input_text:
            return
            
        if input_text == self.last_processed_link:
            return
            
        if self.is_valid_link(input_text):
            self.last_processed_link = input_text
            self.convert_and_open_auto()
            
    def convert_and_open_auto(self):
        input_text = self.input_var.get().strip()
        
        if not input_text:
            self.status_var.set("No input provided")
            log_manager.warning("Auto convert failed: No input")
            return
            
        if not self.is_valid_link(input_text):
            self.status_var.set("Auto: Invalid link format")
            log_manager.warning("Auto convert failed: Invalid link format")
            return
            
        result = self.process_link(input_text)
        
        if result:
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(1.0, result)
            self.status_var.set("Auto: Link converted and opening...")
            log_manager.info("Auto: Roblox link converted successfully")
            
            self.open_deep_link(result)
        else:
            self.status_var.set("Auto: Failed to process link")
            log_manager.error("Auto convert failed: Failed to process link")
        
    def create_widgets(self):
        title_label = ttk.Label(self.parent, text="Roblox Link Converter", font=('Arial', 14, 'bold'))
        title_label.pack(anchor='w', pady=(5, 3))
        
        input_label = ttk.Label(self.parent, text="Input Roblox Link:", font=('Arial', 9))
        input_label.pack(anchor='w', padx=5, pady=(5, 0))
        
        input_frame = ttk.Frame(self.parent)
        input_frame.pack(fill='x', padx=5, pady=3)
        
        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_var, font=('Arial', 9))
        self.input_entry.pack(side='left', fill='x', expand=True)
        
        self.paste_btn = ttk.Button(input_frame, text="Paste", command=self.paste_from_clipboard, width=8)
        self.paste_btn.pack(side='right', padx=(5, 0))
        
        button_frame = ttk.Frame(self.parent)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        self.convert_open_btn = ttk.Button(button_frame, text="Convert & Open", 
                                         command=self.convert_and_open, width=15)
        self.convert_open_btn.pack(side='left', padx=(0, 5))
        
        self.convert_only_btn = ttk.Button(button_frame, text="Convert Only", 
                                         command=self.convert_only, width=12)
        self.convert_only_btn.pack(side='left', padx=(0, 5))
        
        self.auto_execute_var = tk.BooleanVar(value=self.config_manager.get_value("auto_execute", False))
        self.auto_execute_check = ttk.Checkbutton(button_frame, text="Auto Execute", 
                                                variable=self.auto_execute_var,
                                                command=self.on_auto_execute_changed)
        self.auto_execute_check.pack(side='left')
        
        output_label = ttk.Label(self.parent, text="DeepLink Output:", font=('Arial', 9))
        output_label.pack(anchor='w', padx=5, pady=(10, 0))
        
        output_frame = ttk.Frame(self.parent)
        output_frame.pack(fill='x', padx=5, pady=3)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=3, font=('Arial', 9), wrap=tk.WORD)
        self.output_text.pack(fill='x')
        
        output_buttons = ttk.Frame(self.parent)
        output_buttons.pack(fill='x', padx=5, pady=5)
        
        self.copy_btn = ttk.Button(output_buttons, text="Copy", command=self.copy_to_clipboard, width=8)
        self.copy_btn.pack(side='left', padx=(0, 5))
        
        self.clear_btn = ttk.Button(output_buttons, text="Clear", command=self.clear_all, width=8)
        self.clear_btn.pack(side='left')
        
        self.status_var = tk.StringVar()
        self.status_var.set("Enter Roblox link to convert")
        status_label = ttk.Label(self.parent, textvariable=self.status_var, 
                               font=('Arial', 8), foreground='gray')
        status_label.pack(fill='x', padx=5, pady=(5, 0))
        
        self.focus_manager.add_focusable_widget(self.input_entry)
        self.focus_manager.add_focusable_widget(self.paste_btn)
        self.focus_manager.add_focusable_widget(self.convert_open_btn)
        self.focus_manager.add_focusable_widget(self.convert_only_btn)
        self.focus_manager.add_focusable_widget(self.auto_execute_check)
        self.focus_manager.add_focusable_widget(self.output_text)
        self.focus_manager.add_focusable_widget(self.copy_btn)
        self.focus_manager.add_focusable_widget(self.clear_btn)
    
    def on_auto_execute_changed(self):
        self.config_manager.set_value("auto_execute", self.auto_execute_var.get())
        self.config_manager.save_config()
        
        if self.auto_execute_var.get():
            self.status_var.set("Auto execute enabled - will automatically convert and open valid links")
            log_manager.info("Auto execute enabled")
            self.check_and_auto_convert()
        else:
            self.status_var.set("Auto execute disabled")
            log_manager.info("Auto execute disabled")

    def paste_from_clipboard(self):
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content:
                cleaned_content = clipboard_content.strip()
                if len(cleaned_content) > 200:
                    cleaned_content = cleaned_content[:200]
                self.input_var.set(cleaned_content)
                self.status_var.set("Pasted from clipboard")
                log_manager.info("Pasted Roblox link from clipboard")
                
                if self.auto_execute_var.get():
                    if self.is_valid_link(cleaned_content):
                        self.convert_and_open_auto()
                    else:
                        self.status_var.set("Auto: Invalid link format")
                        log_manager.warning("Auto execute skipped: Invalid link format")
        except Exception as e:
            self.status_var.set("Clipboard access error")
            log_manager.error("Failed to paste from clipboard")

    def clean_input(self, text: str) -> str:
        return text.strip().strip('"').strip("'")

    def is_valid_link(self, url: str) -> bool:
        cleaned_url = self.clean_input(url)
        
        # Check for share link format
        share_patterns = [
            r'^https://(?:www|web)\.roblox\.com/share\?code=[a-fA-F0-9]+&type=Server$',
        ]
        
        # Check for private server link format
        private_server_patterns = [
            r'^https://(?:www|web)\.roblox\.com/games/\d+/[^?]+\?privateServerLinkCode=[^&]+$',
            r'^https://(?:www|web)\.roblox\.com/games/\d+\?privateServerLinkCode=[^&]+$',
        ]
        
        for pattern in share_patterns:
            if re.match(pattern, cleaned_url):
                return True
        
        for pattern in private_server_patterns:
            if re.match(pattern, cleaned_url):
                return True
        
        return False

    def extract_share_link_params(self, url: str):
        cleaned_url = self.clean_input(url)
        code_match = re.search(r'code=([a-fA-F0-9]+)', cleaned_url)
        type_match = re.search(r'type=([^&]+)', cleaned_url)
        code = code_match.group(1) if code_match else None
        link_type = type_match.group(1) if type_match else None
        return code, link_type

    def extract_private_server_params(self, url: str):
        cleaned_url = self.clean_input(url)
        
        # Extract place ID
        place_id_match = re.search(r'/games/(\d+)', cleaned_url)
        place_id = place_id_match.group(1) if place_id_match else None
        
        # Extract link code
        link_code_match = re.search(r'privateServerLinkCode=([^&]+)', cleaned_url)
        link_code = link_code_match.group(1) if link_code_match else None
        
        return place_id, link_code

    def determine_link_type(self, url: str) -> str:
        cleaned_url = self.clean_input(url)
        
        if '/share?' in cleaned_url:
            return 'share'
        elif 'privateServerLinkCode=' in cleaned_url:
            return 'private_server'
        else:
            return 'unknown'

    def process_link(self, url: str) -> str:
        link_type = self.determine_link_type(url)
        
        if link_type == 'share':
            code, link_type_param = self.extract_share_link_params(url)
            if code and link_type_param:
                return f"roblox://navigation/share_links?code={code}&type={link_type_param}"
        
        elif link_type == 'private_server':
            place_id, link_code = self.extract_private_server_params(url)
            if place_id and link_code:
                return f"roblox://placeId={place_id}&linkCode={link_code}"
        
        return None

    def convert_only(self):
        self.convert_link(open_link=False)

    def convert_and_open(self):
        self.convert_link(open_link=True)

    def convert_link(self, open_link: bool = True):
        input_text = self.input_var.get().strip()
        
        if not input_text:
            if not open_link or not self.auto_execute_var.get():
                messagebox.showwarning("Warning", "Please enter a Roblox link")
            self.status_var.set("Please enter a Roblox link")
            log_manager.warning("Convert failed: No input provided")
            return
        
        if not self.is_valid_link(input_text):
            if not open_link or not self.auto_execute_var.get():
                messagebox.showerror("Error", "Invalid Roblox link format!")
            self.status_var.set("Invalid Roblox link format")
            log_manager.error("Convert failed: Invalid Roblox link format")
            return
        
        result = self.process_link(input_text)
        
        if result:
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(1.0, result)
            self.status_var.set("Link converted successfully")
            
            link_type = self.determine_link_type(input_text)
            if link_type == 'share':
                log_manager.info("Roblox share link converted successfully")
            elif link_type == 'private_server':
                log_manager.info("Roblox private server link converted successfully")
            
            if open_link:
                self.open_deep_link(result)
        else:
            if not open_link or not self.auto_execute_var.get():
                messagebox.showerror("Error", "Failed to process link")
            self.status_var.set("Failed to process link")
            log_manager.error("Convert failed: Failed to process link")

    def open_deep_link(self, deep_link: str):
        def open_link_thread():
            try:
                self.status_var.set("Opening DeepLink in Roblox...")
                log_manager.info("Opening DeepLink in Roblox...")
                os.startfile(deep_link)
                time.sleep(0.5)
                self.status_var.set("DeepLink opened successfully - check Roblox client")
                log_manager.info("DeepLink opened successfully")
            except Exception as e:
                self.status_var.set(f"Failed to open link: {str(e)}")
                log_manager.error(f"Failed to open DeepLink: {e}")
        
        thread = threading.Thread(target=open_link_thread, daemon=True)
        thread.start()

    def copy_to_clipboard(self):
        try:
            output_text = self.output_text.get(1.0, tk.END).strip()
            if output_text:
                pyperclip.copy(output_text)
                self.status_var.set("Copied to clipboard")
                log_manager.info("DeepLink copied to clipboard")
            else:
                self.status_var.set("No output to copy")
                log_manager.warning("Copy failed: No output to copy")
        except Exception as e:
            self.status_var.set(f"Copy failed: {str(e)}")
            log_manager.error(f"Copy failed: {e}")

    def clear_all(self):
        self.input_var.set("")
        self.output_text.delete(1.0, tk.END)
        self.last_processed_link = ""
        self.status_var.set("Enter Roblox link to convert")
        log_manager.info("Link converter cleared")

class ControlPanel:
    def __init__(self, parent, config_manager, log_panel, main_gui, focus_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.log_panel = log_panel
        self.main_gui = main_gui
        self.focus_manager = focus_manager
        self.create_widgets()
    
    def create_widgets(self):
        self.converter = LinkConverter(self.parent, self.config_manager, self.log_panel, self.main_gui, self.focus_manager)

class MainGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox Link Converter")
        self.root.geometry("700x400")
        self.root.resizable(False, False)
        
        self.focus_manager = FocusManager(root)
        self.config_manager = ConfigManager()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.create_main_layout()
        log_manager.set_gui_callback(self.add_log)

        self.display_startup_info()
    
    def display_startup_info(self):
        log_manager.info("=== Roblox Link Converter Started ===")
        
        auto_execute = self.config_manager.get_value("auto_execute", False)
        if auto_execute:
            log_manager.info("Auto execute enabled")
        else:
            log_manager.info("Auto execute disabled")
        
        log_manager.info("Lets Get Oppressions OvO")
        log_manager.info("GG")
    
    def create_main_layout(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        main_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill='both', expand=True)
        
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=2)
        
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        
        main_paned.sashpos(0, 400)
        
        self.log_panel = LogPanel(right_frame, self.focus_manager)
        self.control_panel = ControlPanel(left_frame, self.config_manager, self.log_panel, self, self.focus_manager)
    
    def add_log(self, message: str):
        self.log_panel.add_log(message)
    
    def save_all_data(self):
        try:
            auto_execute = self.control_panel.converter.auto_execute_var.get()
            self.config_manager.set_value("auto_execute", auto_execute)
            self.config_manager.save_config()
            
            log_manager.info("Settings saved successfully")
        except Exception as e:
            log_manager.error(f"Error saving data: {e}")
    
    def on_closing(self):
        try:
            self.save_all_data()
            log_manager.info("Application closed successfully")
        except Exception as e:
            log_manager.error(f"Error during shutdown: {e}")

        self.root.destroy()
    
    def run(self):
        self.root.mainloop()

def main():
    root = tk.Tk()
    root.eval('tk::PlaceWindow . center')
    
    app = MainGUI(root)
    app.run()

if __name__ == "__main__":
    main()