"""
Simplified GUI for Account Management Only (No Macros)
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
import time
import threading
import json
import requests
from account_manager import AccountManager
from game_launcher import GameLauncher

APP_VERSION = "1.0.0"
GITHUB_REPO = "VRHighLow/Creatures-Of-Sonaria-Account-Manager"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

class RobloxBotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Roblox Account Manager - Creatures of Sonaria (Lite)")
        self.root.geometry("1280x760")
        self.root.minsize(960, 600)
        self.colors = {
            "bg": "#0f1117",
            "panel": "#161b22",
            "panel_alt": "#1f2633",
            "input": "#0b1220",
            "text": "#e6edf3",
            "muted": "#8b949e",
            "accent": "#2f81f7",
            "accent_hover": "#58a6ff",
            "success": "#3fb950",
            "danger": "#f85149",
            "warning": "#e3b341",
            "stroke": "#30363d",
        }
        self.root.configure(bg=self.colors["bg"])
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Style configuration
        self.setup_styles()
        
        self.account_manager = AccountManager()
        self.join_username_var = tk.StringVar(value=self.account_manager.config.get("join_username", ""))
        self.join_username_var.trace_add("write", self._persist_join_username)
        self.search_var = tk.StringVar()
        self.game_launcher = GameLauncher(
            self.account_manager.config.get("game_url", ""),
            status_callback=self.on_game_status_update
        )
        
        # Track account display boxes
        self.account_boxes = {}
        self._account_box_min_width = 320
        self._account_grid_cols = 3
        
        self.init_ui()

    def _persist_join_username(self, *_args):
        try:
            self.account_manager.config["join_username"] = self.join_username_var.get().strip()
            self.account_manager.save_config()
        except Exception:
            pass
    
    def _parse_version(self, version_str):
        """Parse version string (e.g., '1.0.0') into tuple for comparison"""
        try:
            return tuple(map(int, version_str.strip('v').split('.')))
        except Exception:
            return (0, 0, 0)
    
    def check_for_updates(self):
        """Check GitHub releases for newer version (runs in background thread)"""
        try:
            response = requests.get(GITHUB_API_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get('tag_name', '').strip('v')
                
                if latest_version and self._parse_version(latest_version) > self._parse_version(APP_VERSION):
                    # New version available
                    self.root.after(0, lambda: self._show_update_prompt(latest_version, data.get('html_url', '')))
        except Exception as e:
            # Silently fail - don't interrupt user experience
            pass
    
    def _show_update_prompt(self, new_version, release_url):
        """Show update available dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Update Available")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["panel"])
        
        # Center on parent window
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Content
        frame = tk.Frame(dialog, bg=self.colors["panel"])
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(frame, text="Update Available!", bg=self.colors["panel"], fg=self.colors["accent"],
            font=('Segoe UI', 14, 'bold')).pack(pady=(0, 10))
        
        tk.Label(frame, text=f"A new version ({new_version}) is available.",
            bg=self.colors["panel"], fg=self.colors["text"], font=('Segoe UI', 10)).pack(pady=5)
        
        tk.Label(frame, text=f"Current version: {APP_VERSION}", bg=self.colors["panel"],
            fg=self.colors["muted"], font=('Segoe UI', 9)).pack(pady=5)
        
        # Buttons
        btn_frame = tk.Frame(frame, bg=self.colors["panel"])
        btn_frame.pack(fill='x', pady=(20, 0))
        
        tk.Button(btn_frame, text="Download", command=lambda: self._open_release(release_url),
            bg=self.colors["accent"], fg='white', font=('Segoe UI', 10), relief='flat',
            padx=20, pady=8, cursor='hand2').pack(side='left', padx=(0, 10))
        
        tk.Button(btn_frame, text="Remind Later", command=dialog.destroy,
            bg=self.colors["panel_alt"], fg=self.colors["text"], font=('Segoe UI', 10),
            relief='flat', padx=20, pady=8, cursor='hand2').pack(side='left')
    
    def _open_release(self, url):
        """Open release page in browser"""
        import webbrowser
        webbrowser.open(url)
    
    def _manual_check_updates(self):
        """Manual update check triggered by user button click"""
        # Show loading message
        messagebox.showinfo("Checking", "Checking for updates...")
        
        # Run check in background thread
        def check_thread():
            try:
                response = requests.get(GITHUB_API_URL, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    latest_version = data.get('tag_name', '').strip('v')
                    
                    if latest_version:
                        if self._parse_version(latest_version) > self._parse_version(APP_VERSION):
                            # New version available
                            self.root.after(0, lambda: self._show_update_prompt(latest_version, data.get('html_url', '')))
                        else:
                            # Already latest version
                            self.root.after(0, lambda: messagebox.showinfo("Up to Date", f"You're running the latest version ({APP_VERSION})"))
                    else:
                        self.root.after(0, lambda: messagebox.showwarning("Error", "Could not determine latest version"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed to check for updates"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Update check failed: {str(e)}"))
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        bg_dark = self.colors["bg"]
        bg_light = self.colors["input"]
        accent = self.colors["accent"]
        accent_hover = self.colors["accent_hover"]
        text_color = self.colors["text"]
        
        style.configure('TFrame', background=bg_dark)
        style.configure('TLabel', background=bg_dark, foreground=text_color, font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 15, 'bold'), foreground=accent)
        style.configure('TButton', font=('Segoe UI', 10), borderwidth=0)
        style.configure('Accent.TButton', background=accent, foreground='white')
        style.map('Accent.TButton', background=[('active', accent_hover)])
        style.configure('TEntry', fieldbackground=bg_light, foreground=text_color, borderwidth=1)
        style.configure('TCheckbutton', background=bg_dark, foreground=text_color)
    
    def init_ui(self):
        # Main container split into left (content) and right (side panel)
        main_container = tk.Frame(self.root, bg=self.colors["bg"])
        main_container.pack(fill='both', expand=True)
        
        # Left side: main content area
        self.main_content = tk.Frame(main_container, bg=self.colors["bg"])
        self.main_content.pack(side='left', fill='both', expand=True, padx=16, pady=14)
        
        # Right side: sliding panel (initially hidden)
        self.side_panel = tk.Frame(main_container, bg=self.colors["panel"])
        self.side_panel_visible = False
        
        # Header card
        header = tk.Frame(self.main_content, bg=self.colors["panel"], relief='flat', highlightthickness=1, highlightbackground=self.colors["stroke"])
        header.pack(fill='x', pady=(0, 15))
        header_inner = tk.Frame(header, bg=self.colors["panel"])
        header_inner.pack(fill='x', padx=18, pady=16)

        title = tk.Label(
            header_inner,
            text="🎮 Roblox Account Manager",
            bg=self.colors["panel"],
            fg=self.colors["accent"],
            font=('Segoe UI', 17, 'bold'),
        )
        title.pack(expand=True)

        subtitle = tk.Label(
            header_inner,
            text=f"Lite Edition v{APP_VERSION}",
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            font=('Segoe UI', 9),
        )
        subtitle.pack(pady=(8, 0))
        
        # Scrollable account view section
        self.create_scrollable_account_section(self.main_content)
        
        # Bottom section: Controls
        self.create_control_panel(self.main_content)
        
        # Load saved accounts into the UI
        self.update_account_boxes()

        # Responsive resize handling
        self.root.bind('<Configure>', self._on_root_resize)
    
    def create_scrollable_account_section(self, parent):
        """Create scrollable container for account boxes"""
        # Container frame
        container = tk.Frame(parent, bg=self.colors["bg"])
        container.pack(fill='both', expand=True, pady=(0, 15))
        
        # Canvas for scrolling
        self.accounts_canvas = tk.Canvas(container, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient='vertical', command=self.accounts_canvas.yview)
        scrollbar.config(bg=self.colors["panel"], troughcolor=self.colors["bg"], activebackground=self.colors["accent"])
        self.accounts_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Frame inside canvas to hold account boxes
        self.accounts_frame = tk.Frame(self.accounts_canvas, bg=self.colors["bg"])
        self.accounts_canvas_window = self.accounts_canvas.create_window((0, 0), window=self.accounts_frame, anchor='nw')
        
        # Pre-create 15 account boxes (max)
        self.account_boxes = {}
        for i in range(15):
            box = self.create_account_box(self.accounts_frame)
            self.account_boxes[i] = box

        # Initial layout
        self._reflow_account_boxes(self._account_grid_cols)
        
        # Pack canvas and scrollbar
        self.accounts_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind canvas resize
        self.accounts_frame.bind('<Configure>', lambda e: self.accounts_canvas.configure(scrollregion=self.accounts_canvas.bbox('all')))
        self.accounts_canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Mouse wheel scrolling (only on main canvas)
        def on_mousewheel(event):
            self.accounts_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        self.accounts_canvas.bind('<MouseWheel>', on_mousewheel)
    
    def _on_canvas_configure(self, event):
        """Update the canvas window width when canvas is resized"""
        self.accounts_canvas.itemconfig(self.accounts_canvas_window, width=event.width)
        # Responsive columns based on available width
        new_cols = self._compute_account_columns(event.width)
        if new_cols != self._account_grid_cols:
            self._reflow_account_boxes(new_cols)

    def _compute_account_columns(self, width):
        if width <= 0:
            return self._account_grid_cols
        cols = max(1, min(3, width // self._account_box_min_width))
        return cols

    def _reflow_account_boxes(self, cols):
        self._account_grid_cols = cols
        for col in range(cols):
            self.accounts_frame.grid_columnconfigure(col, weight=1, uniform='accounts')

        for i in range(15):
            box = self.account_boxes.get(i)
            if not box:
                continue
            row = i // cols
            col = i % cols
            box.grid(row=row, column=col, padx=8, pady=8, sticky='nsew')

    def _compute_side_panel_width(self, min_width=280, max_ratio=0.45, ratio=0.30):
        """Compute side panel width based on window size."""
        win_width = self.root.winfo_width() or 1280
        computed = int(win_width * ratio)
        max_width = int(win_width * max_ratio)
        return max(min_width, min(computed, max_width))

    def _on_root_resize(self, _event):
        """Keep side panel responsive on window resize."""
        if self.side_panel_visible:
            new_width = self._compute_side_panel_width(min_width=360)
            self.side_panel.config(width=new_width)
    
    def _count_creatures(self, account):
        """Count filled creature slots in account."""
        count = 0
        
        # First check saved creatures in account.creatures
        if hasattr(account, 'creatures') and account.creatures:
            for creature in account.creatures:
                if creature and isinstance(creature, dict) and creature.get('name', '').strip():
                    count += 1
        
        # Also check unsaved widget data if it exists
        if hasattr(account, '_creature_widgets') and account._creature_widgets:
            for i in range(17):
                widgets = account._creature_widgets.get(i)
                if widgets and i < len(account.creatures or []):
                    # Only count if not already saved
                    if not account.creatures or not account.creatures[i]:
                        name = widgets['name'].get().strip()
                        if name:
                            count += 1
        
        return count
    
    def show_side_panel(self, width=550):
        """Show the side panel by animating its width"""
        if not self.side_panel_visible:
            self.side_panel.pack(side='right', fill='both')
            computed_width = self._compute_side_panel_width(min_width=width)
            self.side_panel.config(width=computed_width)
            self.side_panel.pack_propagate(False)
            self.side_panel_visible = True
    
    def hide_side_panel(self):
        """Hide the side panel"""
        if self.side_panel_visible:
            # Clear panel content
            for widget in self.side_panel.winfo_children():
                widget.destroy()
            self.side_panel.pack_forget()
            self.side_panel_visible = False
    
    
    def create_account_box(self, parent):
        """Create a single account display box"""
        box_frame = tk.Frame(
            parent,
            bg=self.colors["panel"],
            relief='flat',
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.colors["stroke"],
            cursor='hand2'
        )
        
        # Make box clickable to open details
        box_frame.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        # Inner frame for padding
        inner = tk.Frame(box_frame, bg=self.colors["panel"], cursor='hand2')
        inner.pack(fill='both', expand=True, padx=15, pady=12)
        inner.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        # Username and creature count display
        header_row = tk.Frame(inner, bg=self.colors["panel"], cursor='hand2')
        header_row.pack(fill='x', pady=(0, 8))
        header_row.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        username_label = tk.Label(header_row, text="Account Name", bg=self.colors["panel"], fg=self.colors["text"],
                     font=('Segoe UI', 12, 'bold'), cursor='hand2')
        username_label.pack(side='left')
        username_label.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        creature_count_label = tk.Label(header_row, text="0 creatures", bg=self.colors["panel"], fg=self.colors["muted"],
                     font=('Segoe UI', 10), cursor='hand2')
        creature_count_label.pack(side='right')
        creature_count_label.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        # Status indicator
        status_frame = tk.Frame(inner, bg=self.colors["panel"], cursor='hand2')
        status_frame.pack(pady=(0, 12))
        status_frame.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        status_dot = tk.Label(status_frame, text="●", bg=self.colors["panel"], fg=self.colors["muted"], 
                     font=('Segoe UI', 14), cursor='hand2')
        status_dot.pack(side='left', padx=(0, 5))
        status_dot.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        status_label = tk.Label(status_frame, text="Offline", bg=self.colors["panel"], fg=self.colors["muted"],
                               font=('Segoe UI', 9), cursor='hand2')
        status_label.pack(side='left')
        status_label.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        # Buttons frame
        btn_frame = tk.Frame(inner, bg=self.colors["panel"])
        btn_frame.pack(fill='x', pady=(0, 8))
        
        # Launch button
        launch_btn = tk.Button(btn_frame, text="▶ Launch", command=lambda: self.launch_account_from_box(box_frame),
                  bg=self.colors["success"], fg='#0b0f14', font=('Segoe UI', 10, 'bold'),
                      relief='flat', padx=15, pady=9, cursor='hand2', state='disabled')
        launch_btn.pack(side='left', fill='x', expand=True, padx=(0, 4))
        
        # Stop button
        stop_btn = tk.Button(btn_frame, text="⏹ Stop", command=lambda: self.stop_account_from_box(box_frame),
                bg=self.colors["danger"], fg='white', font=('Segoe UI', 10, 'bold'),
                    relief='flat', padx=15, pady=9, cursor='hand2', state='disabled')
        stop_btn.pack(side='left', fill='x', expand=True)
        
        # Store references
        box_frame.username_label = username_label
        box_frame.creature_count_label = creature_count_label
        box_frame.status_label = status_label
        box_frame.status_dot = status_dot
        box_frame.launch_btn = launch_btn
        box_frame.stop_btn = stop_btn
        box_frame.account = None
        
        return box_frame
    
    def update_account_boxes(self):
        """Update pre-made account boxes with current account data"""
        accounts = self.account_manager.get_all_accounts()
        
        # Update each of the 15 boxes
        for i in range(15):
            box = self.account_boxes[i]
            
            if i < len(accounts):
                # Show box with account data
                account = accounts[i]
                box.account = account
                
                # Update display
                box.username_label.config(text=account.username, fg=self.colors["text"])
                
                # Update creature count
                creature_count = self._count_creatures(account)
                box.creature_count_label.config(text=f"{creature_count} creatures")
                
                # Update status
                status_colors = {
                    "offline": self.colors["muted"],
                    "launching": self.colors["warning"],
                    "joining user": self.colors["warning"],
                    "joining game": self.colors["warning"],
                    "online": self.colors["success"],
                    "error": self.colors["danger"]
                }
                color = status_colors.get(account.status, self.colors["muted"])
                box.status_dot.config(fg=color)
                box.status_label.config(text=account.status.capitalize(), fg=color)
                
                # Enable/disable buttons
                if account.status == "offline" or account.status == "error":
                    box.launch_btn.config(state='normal')
                    box.stop_btn.config(state='disabled')
                elif account.status == "online" or account.status == "launching":
                    box.launch_btn.config(state='disabled')
                    box.stop_btn.config(state='normal')
                
                box.grid()
            else:
                # Empty slot - hide box
                box.account = None
                box.username_label.config(text="Empty Slot", fg=self.colors["muted"])
                box.status_dot.config(fg=self.colors["muted"])
                box.status_label.config(text="Offline", fg=self.colors["muted"])
                box.launch_btn.config(state='disabled')
                box.stop_btn.config(state='disabled')
                box.grid()


    
    def create_control_panel(self, parent):
        """Create bottom control panel"""
        control_frame = tk.Frame(parent, bg=self.colors["panel"], relief='flat', highlightthickness=1, highlightbackground=self.colors["stroke"])
        control_frame.pack(fill='x', pady=(0, 10))
        
        inner = tk.Frame(control_frame, bg=self.colors["panel"])
        inner.pack(fill='x', padx=18, pady=16)
        
        # Left section: Add/Remove account
        left_section = tk.Frame(inner, bg=self.colors["panel"])
        left_section.pack(side='left', fill='x', expand=True)
        
        tk.Label(left_section, text="Account Management", bg=self.colors["panel"], fg=self.colors["accent"],
            font=('Segoe UI', 11, 'bold')).pack(side='left', padx=(0, 14))
        
        add_btn = tk.Button(left_section, text="➕ Add Account", command=self.show_add_account,
                   bg=self.colors["success"], fg='#0b0f14', font=('Segoe UI', 10, 'bold'),
                   relief='flat', padx=18, pady=10, cursor='hand2')
        add_btn.pack(side='left', padx=(0, 10))
        
        remove_btn = tk.Button(left_section, text="➖ Remove Account", command=self.show_remove_account,
                      bg=self.colors["danger"], fg='white', font=('Segoe UI', 10, 'bold'),
                      relief='flat', padx=18, pady=10, cursor='hand2')
        remove_btn.pack(side='left', padx=(0, 10))

        logs_btn = tk.Button(left_section, text="📋 View Logs", command=self.open_log_viewer,
                bg=self.colors["accent_hover"], fg='#0b0f14', font=('Segoe UI', 10, 'bold'),
                relief='flat', padx=18, pady=10, cursor='hand2')
        logs_btn.pack(side='left')
        
        # Right section: Launch/Stop all + Logs
        right_section = tk.Frame(inner, bg=self.colors["panel"])
        right_section.pack(side='right')

        tk.Label(right_section, text="Join Username:", bg=self.colors["panel"], fg=self.colors["text"],
                font=('Segoe UI', 10, 'bold')).pack(side='left', padx=(0, 8))

        join_entry = tk.Entry(
            right_section,
            textvariable=self.join_username_var,
            bg=self.colors["input"],
            fg=self.colors["text"],
            font=('Segoe UI', 10),
            relief='flat',
            insertbackground=self.colors["text"],
            width=18,
        )
        join_entry.pack(side='left', padx=(0, 12))

        tk.Label(right_section, text="Search Creature:", bg=self.colors["panel"], fg=self.colors["text"],
                font=('Segoe UI', 10, 'bold')).pack(side='left', padx=(4, 8))

        search_entry = tk.Entry(
            right_section,
            textvariable=self.search_var,
            bg=self.colors["input"],
            fg=self.colors["text"],
            font=('Segoe UI', 10),
            relief='flat',
            insertbackground=self.colors["text"],
            width=18,
        )
        search_entry.pack(side='left', padx=(0, 8))
        search_entry.bind('<Return>', lambda _e: self.search_creatures())

        search_btn = tk.Button(right_section, text="🔎 Search", command=self.search_creatures,
                       bg=self.colors["accent"], fg='white', font=('Segoe UI', 10, 'bold'),
                       relief='flat', padx=14, pady=10, cursor='hand2')
        search_btn.pack(side='left', padx=(0, 12))
        
        launch_all_btn = tk.Button(right_section, text="▶ Launch All", command=self.launch_all_accounts,
                       bg=self.colors["accent"], fg='white', font=('Segoe UI', 10, 'bold'),
                       relief='flat', padx=18, pady=10, cursor='hand2')
        launch_all_btn.pack(side='left', padx=(0, 10))
        
        stop_all_btn = tk.Button(right_section, text="⏹ Stop All", command=self.stop_all_accounts,
                    bg=self.colors["danger"], fg='white', font=('Segoe UI', 10, 'bold'),
                    relief='flat', padx=18, pady=10, cursor='hand2')
        stop_all_btn.pack(side='left', padx=(0, 10))
        
        update_btn = tk.Button(right_section, text="⬇ Check Updates", command=self._manual_check_updates,
                    bg=self.colors["muted"], fg='white', font=('Segoe UI', 10, 'bold'),
                    relief='flat', padx=12, pady=10, cursor='hand2')
        update_btn.pack(side='left')
        
        
    
    def show_add_account(self):
        """Show add account in side panel"""
        self.hide_side_panel()
        self.show_side_panel(width=400)
        
        # Header with close button
        header = tk.Frame(self.side_panel, bg=self.colors["panel_alt"], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        header_inner = tk.Frame(header, bg=self.colors["panel_alt"])
        header_inner.pack(fill='both', expand=True, padx=15, pady=12)
        
        tk.Label(header_inner, text="➕ Add Account", 
            bg=self.colors["panel_alt"], fg=self.colors["accent"], 
            font=('Segoe UI', 14, 'bold')).pack(side='left')
        
        close_btn = tk.Button(header_inner, text="✕", command=self.hide_side_panel,
            bg=self.colors["panel_alt"], fg=self.colors["muted"], font=('Segoe UI', 16),
            relief='flat', padx=8, pady=0, cursor='hand2', borderwidth=0)
        close_btn.pack(side='right')
        
        # Form content
        frame = tk.Frame(self.side_panel, bg=self.colors["panel"])
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(frame, text="Username:", bg=self.colors["panel"], fg=self.colors["text"],
                font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 5))
        username_entry = tk.Entry(frame, bg=self.colors["input"], fg=self.colors["text"], font=('Segoe UI', 10),
                     relief='flat', insertbackground=self.colors["text"])
        username_entry.pack(fill='x', pady=(0, 15), ipady=8)
        username_entry.focus_set()
        
        tk.Label(frame, text="Password:", bg=self.colors["panel"], fg=self.colors["text"],
                font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 5))
        password_entry = tk.Entry(frame, bg=self.colors["input"], fg=self.colors["text"], font=('Segoe UI', 10),
                     show='*', relief='flat', insertbackground=self.colors["text"])
        password_entry.pack(fill='x', pady=(0, 25), ipady=8)
        
        def add_account():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            
            if not username or not password:
                messagebox.showwarning("Invalid Input", "Please fill in both fields!")
                return
            
            if self.account_manager.add_account(username, password, False):
                self.update_account_boxes()
                self.hide_side_panel()
            else:
                messagebox.showerror("Error", "Account already exists!")
        
        tk.Button(frame, text="Add Account", command=add_account,
             bg=self.colors["accent"], fg='white', font=('Segoe UI', 11, 'bold'),
             relief='flat', padx=20, pady=12, cursor='hand2').pack(fill='x')
    
    def show_remove_account(self):
        """Show remove account in side panel"""
        accounts = self.account_manager.get_all_accounts()
        if not accounts:
            messagebox.showinfo("No Accounts", "No accounts to remove!")
            return
        
        self.hide_side_panel()
        self.show_side_panel(width=400)
        
        # Header with close button
        header = tk.Frame(self.side_panel, bg=self.colors["panel_alt"], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        header_inner = tk.Frame(header, bg=self.colors["panel_alt"])
        header_inner.pack(fill='both', expand=True, padx=15, pady=12)
        
        tk.Label(header_inner, text="🗑️ Remove Account", 
            bg=self.colors["panel_alt"], fg=self.colors["danger"], 
            font=('Segoe UI', 14, 'bold')).pack(side='left')
        
        close_btn = tk.Button(header_inner, text="✕", command=self.hide_side_panel,
            bg=self.colors["panel_alt"], fg=self.colors["muted"], font=('Segoe UI', 16),
            relief='flat', padx=8, pady=0, cursor='hand2', borderwidth=0)
        close_btn.pack(side='right')
        
        # Content
        frame = tk.Frame(self.side_panel, bg=self.colors["panel"])
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(frame, text="Select account to remove:", bg=self.colors["panel"], fg=self.colors["text"],
            font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 15))
        
        selected = tk.StringVar()
        
        for account in accounts:
            rb = tk.Radiobutton(frame, text=account.username, variable=selected, value=account.username,
                               bg=self.colors["panel"], fg=self.colors["text"], selectcolor=self.colors["panel"],
                               activebackground=self.colors["panel"], activeforeground=self.colors["accent"],
                               font=('Segoe UI', 10))
            rb.pack(anchor='w', pady=5)
        
        def remove_account():
            username = selected.get()
            if not username:
                messagebox.showwarning("No Selection", "Please select an account!")
                return
            
            if messagebox.askyesno("Confirm", f"Remove account '{username}'?"):
                self.account_manager.remove_account(username)
                self.update_account_boxes()
                self.hide_side_panel()
        
        tk.Button(frame, text="Remove Account", command=remove_account,
             bg=self.colors["danger"], fg='white', font=('Segoe UI', 11, 'bold'),
             relief='flat', padx=20, pady=12, cursor='hand2').pack(fill='x', pady=(20, 0))
        
        tk.Button(frame, text="Remove Account", command=remove_account,
             bg=self.colors["danger"], fg='white', font=('Segoe UI', 11, 'bold'),
             relief='flat', padx=20, pady=12, cursor='hand2').pack(fill='x', pady=(20, 0))
    
    def launch_account_from_box(self, box_frame):
        """Launch account from a specific box"""
        if box_frame.account:
            self.auto_close_singleton_and_launch(box_frame.account)

    def auto_close_singleton_and_launch(self, account):
        """Automatically close singleton event and launch the account."""
        def worker():
            # Step 1: close singleton event in all RobloxPlayer processes for a few seconds
            self.game_launcher.mutex_manager.close_singleton_events_in_player(
                target_pids=None,
                stop_after_first=False,
                scan_max_handle=0x2000,
                repeat_seconds=3.0,
                repeat_interval=0.25,
            )

            # Step 2: keep closing while launching (background)
            def hold_worker():
                self.game_launcher.mutex_manager.close_singleton_events_in_player(
                    target_pids=None,
                    stop_after_first=False,
                    scan_max_handle=0x2000,
                    repeat_seconds=10.0,
                    repeat_interval=0.25,
                )

            threading.Thread(target=hold_worker, daemon=True).start()

            # Step 3: launch without re-closing
            self.game_launcher.launch_game(
                account,
                join_username=self.join_username_var.get(),
                close_singleton_first=False,
            )

        threading.Thread(target=worker, daemon=True).start()

    def open_prelaunch_singleton_dialog(self, account):
        """Show pre-launch singleton close testing in side panel"""
        self.hide_side_panel()
        self.show_side_panel(width=700)

        # Header with close button
        header = tk.Frame(self.side_panel, bg=self.colors["panel_alt"], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        header_inner = tk.Frame(header, bg=self.colors["panel_alt"])
        header_inner.pack(fill='both', expand=True, padx=15, pady=12)
        
        tk.Label(header_inner, text="🔧 Test Singleton Close", 
            bg=self.colors["panel_alt"], fg=self.colors["accent"], 
            font=('Segoe UI', 14, 'bold')).pack(side='left')
        
        close_btn_header = tk.Button(header_inner, text="✕", command=self.hide_side_panel,
            bg=self.colors["panel_alt"], fg=self.colors["muted"], font=('Segoe UI', 16),
            relief='flat', padx=8, pady=0, cursor='hand2', borderwidth=0)
        close_btn_header.pack(side='right')

        # Scrollable content
        scroll_container = tk.Frame(self.side_panel, bg=self.colors["panel"])
        scroll_container.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(scroll_container, bg=self.colors["panel"], highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_container, orient='vertical', command=canvas.yview)
        scrollbar.config(bg=self.colors["panel"], troughcolor=self.colors["bg"], activebackground=self.colors["accent"])
        canvas.configure(yscrollcommand=scrollbar.set)
        
        content_frame = tk.Frame(canvas, bg=self.colors["panel"])
        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor='nw')
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width-20))
        
        # Mouse wheel scrolling only for this panel
        def on_panel_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        canvas.bind('<MouseWheel>', on_panel_mousewheel)

        body = tk.Frame(content_frame, bg=self.colors["panel"])
        body.pack(fill='both', expand=True, padx=14, pady=14)

        tk.Label(
            body,
            text="Test closing singleton event before launch",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            font=('Segoe UI', 10),
        ).pack(anchor='w', pady=(0, 10))

        # Target selection
        select_frame = tk.Frame(body, bg=self.colors["input"])
        select_frame.pack(fill='x', pady=(0, 10))
        select_frame_inner = tk.Frame(select_frame, bg=self.colors["input"])
        select_frame_inner.pack(fill='x', padx=12, pady=10)

        tk.Label(
            select_frame_inner,
            text="Target Roblox process:",
            bg=self.colors["input"],
            fg=self.colors["text"],
            font=('Segoe UI', 10, 'bold'),
        ).pack(anchor='w')

        target_mode = tk.StringVar(value='all')
        rb_row = tk.Frame(select_frame_inner, bg=self.colors["input"])
        rb_row.pack(fill='x', pady=(6, 0))
        
        for label, val in [("All processes", "all"), ("Oldest", "oldest"), ("Newest", "newest"), ("Choose PID", "choose")]:
            tk.Radiobutton(
                rb_row,
                text=label,
                variable=target_mode,
                value=val,
                bg=self.colors["input"],
                fg=self.colors["text"],
                selectcolor=self.colors["input"],
                activebackground=self.colors["input"],
                activeforeground=self.colors["accent"],
                font=('Segoe UI', 9),
            ).pack(side='left', padx=(0, 10))

        pid_var = tk.StringVar(value='')
        pid_combo = ttk.Combobox(select_frame_inner, textvariable=pid_var, state='readonly')
        pid_combo.pack(fill='x', pady=(8, 0))

        hold_frame = tk.Frame(select_frame_inner, bg=self.colors["input"])
        hold_frame.pack(fill='x', pady=(10, 0))

        hold_var = tk.IntVar(value=1)
        hold_check = tk.Checkbutton(
            hold_frame,
            text="Repeat close for",
            variable=hold_var,
            bg=self.colors["input"],
            fg=self.colors["text"],
            selectcolor=self.colors["input"],
            activebackground=self.colors["input"],
            activeforeground=self.colors["accent"],
            font=('Segoe UI', 9),
        )
        hold_check.pack(side='left')

        hold_seconds_var = tk.StringVar(value="3.0")
        hold_entry = ttk.Entry(hold_frame, textvariable=hold_seconds_var, width=6)
        hold_entry.pack(side='left', padx=(6, 4))
        tk.Label(hold_frame, text="seconds", bg=self.colors["input"], fg=self.colors["text"],
                font=('Segoe UI', 9)).pack(side='left')

        launch_hold_frame = tk.Frame(select_frame_inner, bg=self.colors["input"])
        launch_hold_frame.pack(fill='x', pady=(8, 0))

        auto_hold_launch_var = tk.IntVar(value=1)
        auto_hold_launch_check = tk.Checkbutton(
            launch_hold_frame,
            text="Keep closing while launching for",
            variable=auto_hold_launch_var,
            bg=self.colors["input"],
            fg=self.colors["text"],
            selectcolor=self.colors["input"],
            activebackground=self.colors["input"],
            activeforeground=self.colors["accent"],
            font=('Segoe UI', 9),
        )
        auto_hold_launch_check.pack(side='left')

        launch_hold_seconds_var = tk.StringVar(value="10.0")
        launch_hold_entry = ttk.Entry(launch_hold_frame, textvariable=launch_hold_seconds_var, width=6)
        launch_hold_entry.pack(side='left', padx=(6, 4))
        tk.Label(launch_hold_frame, text="seconds", bg=self.colors["input"], fg=self.colors["text"],
                font=('Segoe UI', 9)).pack(side='left')

        def _format_proc(p: dict) -> str:
            pid = p.get('pid')
            name = p.get('name')
            ct = p.get('create_time')
            try:
                started = datetime.fromtimestamp(ct).strftime('%H:%M:%S') if ct else 'unknown'
            except Exception:
                started = 'unknown'
            return f"PID {pid} - {name} (started {started})"

        procs_cache: list[dict] = []

        def refresh_pid_list():
            nonlocal procs_cache
            procs_cache = self.game_launcher.mutex_manager.list_roblox_player_processes()
            pid_combo['values'] = [_format_proc(p) for p in procs_cache]
            if procs_cache and not pid_var.get():
                pid_var.set(pid_combo['values'][0])

        tk.Button(
            select_frame_inner,
            text="🔄 Refresh PIDs",
            command=refresh_pid_list,
            bg=self.colors["accent"],
            fg='white',
            font=('Segoe UI', 9, 'bold'),
            relief='flat',
            padx=12,
            pady=6,
            cursor='hand2',
        ).pack(anchor='w', pady=(10, 0))

        # Results / log
        tk.Label(
            body,
            text="Result:",
            bg=self.colors["panel"],
            fg=self.colors["text"],
            font=('Segoe UI', 10, 'bold'),
        ).pack(anchor='w', pady=(0, 6))

        result_text = scrolledtext.ScrolledText(
            body,
            bg=self.colors["input"],
            fg=self.colors["text"],
            font=('Consolas', 8),
            height=10,
            relief='flat',
        )
        result_text.pack(fill='both', expand=True, pady=(0, 10))
        
        # Style the scrollbar
        result_text.vbar.config(bg=self.colors["panel"], troughcolor=self.colors["bg"], activebackground=self.colors["accent"])

        def append_result(line: str):
            result_text.insert('end', line + "\n")
            result_text.see('end')

        # Footer buttons
        footer = tk.Frame(body, bg=self.colors["panel"])
        footer.pack(fill='x', pady=(0, 0))

        close_btn = tk.Button(
            footer,
            text="1) Close Singleton",
            bg=self.colors["success"],
            fg='#0b0f14',
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            padx=14,
            pady=10,
            cursor='hand2',
        )
        close_btn.pack(fill='x', pady=(0, 8))

        launch_btn = tk.Button(
            footer,
            text="2) Launch Game",
            bg=self.colors["accent"],
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            padx=14,
            pady=10,
            cursor='hand2',
            state='disabled',
        )
        launch_btn.pack(fill='x')

        def resolve_target_pids() -> list[int] | None:
            current_procs = self.game_launcher.mutex_manager.list_roblox_player_processes()
            if not current_procs:
                return []

            mode = target_mode.get()
            if mode == 'all':
                return None
            if mode == 'oldest':
                return [current_procs[0]['pid']]
            if mode == 'newest':
                return [current_procs[-1]['pid']]

            selection = pid_var.get().strip()
            if selection.startswith('PID '):
                try:
                    pid_str = selection.split('PID ', 1)[1].split(' - ', 1)[0].strip()
                    return [int(pid_str)]
                except Exception:
                    return []
            return []

        def do_close_singleton():
            close_btn.config(state='disabled')
            launch_btn.config(state='disabled')
            append_result("Closing ROBLOX_singletonEvent...")

            def worker():
                target_pids = resolve_target_pids()
                if target_pids == []:
                    self.root.after(0, lambda: append_result("No RobloxPlayer processes found."))
                    self.root.after(0, lambda: close_btn.config(state='normal'))
                    return

                try:
                    hold_seconds = float(hold_seconds_var.get().strip()) if hold_var.get() else 0.0
                except Exception:
                    hold_seconds = 0.0

                res = self.game_launcher.mutex_manager.close_singleton_events_in_player(
                    target_pids=target_pids,
                    stop_after_first=True,
                    scan_max_handle=0x2000,
                    repeat_seconds=hold_seconds,
                    repeat_interval=0.25,
                )

                def finish():
                    append_result(f"Target PIDs: {res.get('attempted_pids', [])}")
                    
                    if res.get('closed'):
                        c = res['closed'][0]
                        append_result(f"✓ Closed in PID {c['pid']} (handle 0x{int(c['handle_id']):x})")
                        append_result(f"Total closes: {res.get('closed_total', 0)}")
                        launch_btn.config(state='normal')
                    else:
                        append_result("✗ Failed to close singleton")
                    
                    if res.get('errors'):
                        for err in res['errors']:
                            append_result(f"Error in PID {err.get('pid')}: {err.get('error')}")
                    
                    close_btn.config(state='normal')

                self.root.after(0, finish)

            threading.Thread(target=worker, daemon=True).start()

        def do_launch():
            self.hide_side_panel()

            if auto_hold_launch_var.get():
                try:
                    launch_hold_seconds = float(launch_hold_seconds_var.get().strip())
                except Exception:
                    launch_hold_seconds = 0.0

                if launch_hold_seconds > 0:
                    def hold_worker():
                        self.game_launcher.mutex_manager.close_singleton_events_in_player(
                            target_pids=None,
                            stop_after_first=False,
                            scan_max_handle=0x2000,
                            repeat_seconds=launch_hold_seconds,
                            repeat_interval=0.25,
                        )

                    threading.Thread(target=hold_worker, daemon=True).start()

            self.game_launcher.launch_game(
                account,
                join_username=self.join_username_var.get(),
                close_singleton_first=False,
            )

        close_btn.config(command=do_close_singleton)
        launch_btn.config(command=do_launch)

        refresh_pid_list()
    
    def stop_account_from_box(self, box_frame):
        """Stop account from a specific box"""
        if box_frame.account:
            self.game_launcher.stop_game(box_frame.account.username)
            box_frame.account.status = "offline"
            self.update_account_boxes()
    
    def launch_all_accounts(self):
        """Launch all accounts"""
        accounts = self.account_manager.get_all_accounts()
        if not accounts:
            messagebox.showinfo("No Accounts", "No accounts to launch!")
            return
        
        for account in accounts:
            if account.status == "offline":
                # Stagger launches
                time.sleep(2)
                self.game_launcher.launch_game(account, join_username=self.join_username_var.get())
    
    def stop_all_accounts(self):
        """Stop all running game instances"""
        self.game_launcher.stop_all_games()
        for account in self.account_manager.get_all_accounts():
            account.status = "offline"
        self.update_account_boxes()
    
    def on_game_status_update(self, username: str, status: str):
        """Callback from game launcher when status changes"""
        account = self.account_manager.get_account(username)
        if account:
            account.status = status
            # Update GUI in thread-safe way
            self.root.after(0, self.update_account_boxes)
    
    def on_closing(self):
        """Handle window close event"""
        # Stop all running games
        try:
            self.game_launcher.stop_all_games(self.account_manager.accounts)
            self.game_launcher.shutdown()
        except Exception as e:
            print(f"Error stopping games: {e}")
        # Destroy the window
        self.root.destroy()
    
    def open_log_viewer(self):
        """Show session logs in side panel"""
        self.hide_side_panel()
        self.show_side_panel(width=700)
        
        # Header with close button
        header = tk.Frame(self.side_panel, bg=self.colors["panel_alt"], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        header_inner = tk.Frame(header, bg=self.colors["panel_alt"])
        header_inner.pack(fill='both', expand=True, padx=15, pady=12)
        
        tk.Label(header_inner, text="📋 Session Logs", 
            bg=self.colors["panel_alt"], fg=self.colors["accent"], 
            font=('Segoe UI', 14, 'bold')).pack(side='left')
        
        # Buttons
        btn_container = tk.Frame(header_inner, bg=self.colors["panel_alt"])
        btn_container.pack(side='right')
        
        close_btn = tk.Button(btn_container, text="✕", command=self.hide_side_panel,
            bg=self.colors["panel_alt"], fg=self.colors["muted"], font=('Segoe UI', 16),
            relief='flat', padx=8, pady=0, cursor='hand2', borderwidth=0)
        close_btn.pack(side='right')
        
        # Log text area
        log_frame = tk.Frame(self.side_panel, bg=self.colors["panel"])
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Action buttons
        action_frame = tk.Frame(log_frame, bg=self.colors["panel"])
        action_frame.pack(fill='x', pady=(0, 10))
        
        log_text = scrolledtext.ScrolledText(log_frame, bg=self.colors["input"], fg=self.colors["text"],
                             font=('Consolas', 9), relief='flat',
                             insertbackground=self.colors["text"], selectbackground=self.colors["panel_alt"])
        log_text.vbar.config(bg=self.colors["panel"], troughcolor=self.colors["bg"], activebackground=self.colors["accent"])
        
        refresh_btn = tk.Button(action_frame, text="🔄 Refresh", command=lambda: self.refresh_logs(log_text),
                       bg=self.colors["accent"], fg='white', font=('Segoe UI', 9, 'bold'), relief='flat',
                       padx=15, pady=6, cursor='hand2')
        refresh_btn.pack(side='left', padx=(0, 8))
        
        download_btn = tk.Button(action_frame, text="💾 Download", command=lambda: self.download_logs(None),
                    bg=self.colors["success"], fg='#0b0f14', font=('Segoe UI', 9, 'bold'), relief='flat',
                    padx=15, pady=6, cursor='hand2')
        download_btn.pack(side='left')
        
        log_text.pack(fill='both', expand=True)
        
        # Load logs
        self.refresh_logs(log_text)

    
    def refresh_logs(self, log_text):
        """Refresh the log display"""
        log_text.delete('1.0', tk.END)
        logs = GameLauncher.get_session_logs()
        
        if logs:
            log_text.insert('1.0', '\n'.join(logs))
        else:
            log_text.insert('1.0', 'No logs available for current session.')
        
        # Auto-scroll to bottom
        log_text.see(tk.END)

    def search_creatures(self):
        """Search for creature name across all accounts and show matches."""
        try:
            query = (self.search_var.get() or "").strip().lower()
            if not query:
                messagebox.showinfo("Search", "Enter a creature name to search.")
                return

            results = []
            accounts = self.account_manager.get_all_accounts()
            for account in accounts:
                if not hasattr(account, 'creatures'):
                    continue
                matches = []
                for idx, creature in enumerate(account.creatures or []):
                    if not creature or not isinstance(creature, dict):
                        continue
                    name = (creature.get('name') or "").strip()
                    if name and query in name.lower():
                        age = creature.get('age', 'N/A')

                        # Back-compat: older saves used a single 'age_mutation'
                        age_mut1 = creature.get('age_mutation_1')
                        age_mut2 = creature.get('age_mutation_2')
                        if age_mut1 is None:
                            age_mut1 = creature.get('age_mutation', 'None')
                        if age_mut2 is None:
                            age_mut2 = 'None'

                        glimmer = creature.get('glimmer', None)
                        if glimmer is None:
                            # Legacy: Glimmer used to be stored as an age mutation
                            glimmer = (age_mut1 == 'Glimmer') or (age_mut2 == 'Glimmer')
                            if age_mut1 == 'Glimmer':
                                age_mut1 = 'None'
                            if age_mut2 == 'Glimmer':
                                age_mut2 = 'None'

                        nested_mut = creature.get('nested_mutation', 'None')
                        trait1 = creature.get('trait1', 'None')
                        trait2 = creature.get('trait2', 'None')

                        details = f"Slot {idx + 1}: {name} | Age: {age}"

                        mutations = []
                        if age_mut1 != 'None':
                            mutations.append(f"Age Mut 1: {age_mut1}")
                        if age_mut2 != 'None':
                            mutations.append(f"Age Mut 2: {age_mut2}")
                        if glimmer:
                            mutations.append("Glimmer")
                        if nested_mut != 'None':
                            mutations.append(f"Nested Mut: {nested_mut}")
                        if mutations:
                            details += f" | {', '.join(mutations)}"

                        traits = []
                        if trait1 != 'None':
                            traits.append(trait1)
                        if trait2 != 'None':
                            traits.append(trait2)
                        if traits:
                            details += f" | Traits: {', '.join(traits)}"

                        matches.append(details)
                if matches:
                    results.append((account.username, matches))

            if not results:
                messagebox.showinfo("Search", f"No accounts found with creature matching '{query}'.")
                return
        except Exception as e:
            try:
                GameLauncher.add_session_log(f"[search] error: {e}")
            except Exception:
                pass
            messagebox.showerror("Search", f"Search failed: {e}")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Creature Search Results")
        dialog.geometry("600x420")
        dialog.configure(bg=self.colors["bg"])
        dialog.transient(self.root)

        header = tk.Frame(dialog, bg=self.colors["panel"], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(
            header,
            text=f"Results for '{query}'",
            bg=self.colors["panel"],
            fg=self.colors["accent"],
            font=('Segoe UI', 12, 'bold')
        ).pack(pady=12)

        body = tk.Frame(dialog, bg=self.colors["bg"])
        body.pack(fill='both', expand=True, padx=12, pady=12)

        text = scrolledtext.ScrolledText(
            body,
            bg=self.colors["panel_alt"],
            fg=self.colors["text"],
            font=('Consolas', 10),
            relief='flat',
            insertbackground=self.colors["text"],
            selectbackground='#414868'
        )
        text.pack(fill='both', expand=True)

        for username, slots in results:
            text.insert(tk.END, f"{username}\n")
            for slot in slots:
                text.insert(tk.END, f"  - {slot}\n")
            text.insert(tk.END, "\n")

        text.config(state='disabled')
    
    def download_logs(self, parent_window):
        """Download logs to a file"""
        filename = filedialog.asksaveasfilename(
            parent=parent_window,
            defaultextension=".txt",
            initialfile=f"roblox_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    logs = GameLauncher.get_session_logs()
                    f.write('\n'.join(logs))
                messagebox.showinfo("Success", f"Logs saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs: {e}")
    
    def show_account_details(self, box_frame):
        """Show account details in side panel with 17 creature slots"""
        if not box_frame.account:
            return  # Empty slot, don't show details
        
        account = box_frame.account
        
        # Initialize creatures list if not exists
        if not hasattr(account, 'creatures'):
            account.creatures = [None] * 17
        
        # Clear and show side panel
        self.hide_side_panel()
        self.show_side_panel(width=550)
        
        # Header with close button
        header = tk.Frame(self.side_panel, bg=self.colors["panel_alt"], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        header_inner = tk.Frame(header, bg=self.colors["panel_alt"])
        header_inner.pack(fill='both', expand=True, padx=15, pady=12)
        
        tk.Label(header_inner, text=f"🦎 {account.username}'s Creatures", 
            bg=self.colors["panel_alt"], fg=self.colors["accent"], 
            font=('Segoe UI', 14, 'bold')).pack(side='left')
        
        close_btn = tk.Button(header_inner, text="✕", command=self.hide_side_panel,
            bg=self.colors["panel_alt"], fg=self.colors["muted"], font=('Segoe UI', 16),
            relief='flat', padx=8, pady=0, cursor='hand2', borderwidth=0)
        close_btn.pack(side='right')
        
        # Scrollable creature list
        container = tk.Frame(self.side_panel, bg=self.colors["panel"])
        container.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(container, bg=self.colors["panel"], highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient='vertical', command=canvas.yview)
        scrollbar.config(bg=self.colors["panel"], troughcolor=self.colors["bg"], activebackground=self.colors["accent"])
        canvas.configure(yscrollcommand=scrollbar.set)
        
        creatures_frame = tk.Frame(canvas, bg=self.colors["panel"])
        canvas_window = canvas.create_window((0, 0), window=creatures_frame, anchor='nw')
        
        canvas.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scrollbar.pack(side='right', fill='y')
        
        creatures_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width-20))
        
        # Mouse wheel scrolling only for this panel
        def on_panel_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
        canvas.bind('<MouseWheel>', on_panel_mousewheel)
        
        # Create 17 creature slot entries
        for i in range(17):
            self.create_creature_slot(creatures_frame, account, i)
        
        # Save button at bottom
        btn_frame = tk.Frame(self.side_panel, bg=self.colors["panel"])
        btn_frame.pack(fill='x', padx=15, pady=15)
        
        tk.Button(btn_frame, text="💾 Save Changes", command=lambda: self.save_creature_data_inline(account),
             bg=self.colors["accent"], fg='white', font=('Segoe UI', 11, 'bold'),
                 relief='flat', padx=25, pady=10, cursor='hand2').pack(fill='x')

    
    def create_creature_slot(self, parent, account, slot_index):
        """Create a single creature slot entry"""
        slot_frame = tk.Frame(parent, bg=self.colors["panel"], relief='solid', borderwidth=1)
        slot_frame.pack(fill='x', pady=8, padx=5)
        
        inner = tk.Frame(slot_frame, bg=self.colors["panel"])
        inner.pack(fill='x', padx=15, pady=12)
        
        # Slot header
        tk.Label(inner, text=f"Creature Slot {slot_index + 1}", bg=self.colors["panel"], fg=self.colors["accent"],
                font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, sticky='w', columnspan=4, pady=(0, 10))

        # Two-column layout: left = creature info, right = mutations
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_columnconfigure(1, weight=1)
        inner.grid_columnconfigure(2, weight=1)
        inner.grid_columnconfigure(3, weight=1)

        info_frame = tk.Frame(inner, bg=self.colors["panel"])
        info_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', padx=(0, 20))

        muts_frame = tk.Frame(inner, bg=self.colors["panel"])
        muts_frame.grid(row=1, column=2, columnspan=2, sticky='nsew')

        # Creature name
        tk.Label(info_frame, text="Name:", bg=self.colors["panel"], fg=self.colors["text"],
            font=('Segoe UI', 9)).grid(row=0, column=0, sticky='w', padx=(0, 8), pady=(0, 6))
        name_entry = tk.Entry(info_frame, bg=self.colors["input"], fg=self.colors["text"], font=('Segoe UI', 10),
                 relief='flat', insertbackground=self.colors["text"], width=24)
        name_entry.grid(row=0, column=1, sticky='w', pady=(0, 6))

        # Age field
        tk.Label(info_frame, text="Age:", bg=self.colors["panel"], fg=self.colors["text"],
            font=('Segoe UI', 9)).grid(row=1, column=0, sticky='w', padx=(0, 8), pady=(0, 6))
        age_entry = tk.Entry(info_frame, bg=self.colors["input"], fg=self.colors["text"], font=('Segoe UI', 10),
                 relief='flat', insertbackground=self.colors["text"], width=12)
        age_entry.grid(row=1, column=1, sticky='w', pady=(0, 6))
        
        # Mutation selectors with complete lists
        age_mutations = ["None", "Stich (Stich head plushie)", "Smore (Smore cat plushie)",
                "Gilded (Hardcore realm)", "Fools gold (Golden bulb plushie)",
                "Elemental (Elemental plushie)", "Creator star (content creator exclusive)",
                "Clownfish (Clownfish plushie)", "Blood moon (Catalyst plushie)",
                "Bewitch (Magic frog plushie)", "Glowhead", "Reverse shadow",
                "Shadow", "Glowtail"]
        
        nested_mutations = ["None", "Albinism", "Amethyst (February)", "Bewitched (Magic frog plushie)",
                           "Blood moon (Catalyst plushie)", "Blossom (February)", "Clover (March)",
                           "Clownfish (Clownfish plushie)", "Coal (December)", "Creator star (content creator exclusive)",
                           "Dark heart (Lss)", "Diamond", "Dwarfism", "Elemental (Elemental plushie)",
                           "Emerald (May)", "Fools error (April first)", "Fools gold (Golden bulb plushie)",
                           "Frostburn (December)", "Garnet (January)", "Ghostly (Halloween event)",
                   "Gigantism", "Gilded (hardcore realm)", "Harvest (November)",
                           "Headless (Halloween event)", "Leucistic", "Melanism", "Opal (October)",
                           "Overgrown", "Pearl (June)", "Peridot (August)", "Piebald", "Pure heart (Lss)",
                           "Rose Quartz (April)", "Ruby (July)", "Sapphire (September)", "Shadow (Age 67)",
                           "Shimmer", "Smore (Smore cat plushie)", "Souls blessing (Lss)", "Souls Fracture (Lss)",
                           "Stich (Stich head plushie)", "Zombified (Halloween event)"]

        # Remove Shadow/Glowtail from nested list (now age mutations)
        nested_mutations = [m for m in nested_mutations if m not in (
            "Shadow (Age 67)", "Shadow",
            "Glowtail (age 67)", "Glowtail (Age 67)", "Glowtail",
        )]
        
        traits_list = ["None", "Bite", "Damage", "Health", "Healing", "Speed",
                      "Max Stamina", "Stamina Regen", "Weight"]
        
        # Age Mutation 1
        tk.Label(muts_frame, text="Age Mutation 1:", bg=self.colors["panel"], fg=self.colors["text"],
            font=('Segoe UI', 9)).grid(row=0, column=0, sticky='w', padx=(0, 8), pady=(0, 6))
        age_var_1 = tk.StringVar(value="None")
        age_dropdown_1 = tk.OptionMenu(muts_frame, age_var_1, *age_mutations)
        age_dropdown_1.config(bg=self.colors["input"], fg=self.colors["text"], font=('Segoe UI', 9),
                           relief='flat', highlightthickness=0, width=15)
        age_dropdown_1['menu'].config(bg=self.colors["input"], fg=self.colors["text"])
        age_dropdown_1.grid(row=0, column=1, sticky='w', pady=(0, 6))

        # Age Mutation 2 (allows 2 age muts; if set, nested is disabled)
        tk.Label(muts_frame, text="Age Mutation 2:", bg=self.colors["panel"], fg=self.colors["text"],
            font=('Segoe UI', 9)).grid(row=1, column=0, sticky='w', padx=(0, 8), pady=(0, 6))
        age_var_2 = tk.StringVar(value="None")
        age_dropdown_2 = tk.OptionMenu(muts_frame, age_var_2, *age_mutations)
        age_dropdown_2.config(bg=self.colors["input"], fg=self.colors["text"], font=('Segoe UI', 9),
                   relief='flat', highlightthickness=0, width=15)
        age_dropdown_2['menu'].config(bg=self.colors["input"], fg=self.colors["text"])
        age_dropdown_2.grid(row=1, column=1, sticky='w', pady=(0, 6))

        # Nested Mutation
        tk.Label(muts_frame, text="Nested Mutation:", bg=self.colors["panel"], fg=self.colors["text"],
            font=('Segoe UI', 9)).grid(row=2, column=0, sticky='w', padx=(0, 8), pady=(0, 6))
        nested_var = tk.StringVar(value="None")
        nested_dropdown = tk.OptionMenu(muts_frame, nested_var, *nested_mutations)
        nested_dropdown.config(bg=self.colors["input"], fg=self.colors["text"], font=('Segoe UI', 9),
                              relief='flat', highlightthickness=0, width=12)
        nested_dropdown['menu'].config(bg=self.colors["input"], fg=self.colors["text"])
        nested_dropdown.grid(row=2, column=1, sticky='w', pady=(0, 6))

        # Glimmer (separate from age mutations)
        glimmer_var = tk.BooleanVar(value=False)
        glimmer_chk = tk.Checkbutton(
            muts_frame,
            text="Glimmer",
            variable=glimmer_var,
            onvalue=True,
            offvalue=False,
            bg=self.colors["panel"],
            fg=self.colors["text"],
            activebackground=self.colors["panel"],
            activeforeground=self.colors["text"],
            selectcolor=self.colors["input"],
            font=('Segoe UI', 9),
        )
        glimmer_chk.grid(row=3, column=0, sticky='w', pady=(0, 6), columnspan=2)

        def _sync_nested_enabled(*_args):
            try:
                if (age_var_2.get() or "None") != "None":
                    if (nested_var.get() or "None") != "None":
                        nested_var.set("None")
                    nested_dropdown.config(state='disabled')
                else:
                    nested_dropdown.config(state='normal')
            except Exception:
                pass

        age_var_2.trace_add('write', _sync_nested_enabled)
        
        # Trait 1
        tk.Label(info_frame, text="Trait 1:", bg=self.colors["panel"], fg=self.colors["text"],
            font=('Segoe UI', 9)).grid(row=2, column=0, sticky='w', padx=(0, 8), pady=(0, 6))
        trait1_var = tk.StringVar(value="None")
        trait1_dropdown = tk.OptionMenu(info_frame, trait1_var, *traits_list)
        trait1_dropdown.config(bg=self.colors["input"], fg=self.colors["text"], font=('Segoe UI', 9),
                              relief='flat', highlightthickness=0, width=15)
        trait1_dropdown['menu'].config(bg=self.colors["input"], fg=self.colors["text"])
        trait1_dropdown.grid(row=2, column=1, sticky='w', pady=(0, 6))
        
        # Trait 2
        tk.Label(info_frame, text="Trait 2:", bg=self.colors["panel"], fg=self.colors["text"],
            font=('Segoe UI', 9)).grid(row=3, column=0, sticky='w', padx=(0, 8), pady=(0, 6))
        trait2_var = tk.StringVar(value="None")
        trait2_dropdown = tk.OptionMenu(info_frame, trait2_var, *traits_list)
        trait2_dropdown.config(bg=self.colors["input"], fg=self.colors["text"], font=('Segoe UI', 9),
                              relief='flat', highlightthickness=0, width=12)
        trait2_dropdown['menu'].config(bg=self.colors["input"], fg=self.colors["text"])
        trait2_dropdown.grid(row=3, column=1, sticky='w', pady=(0, 6))
        
        # Load existing data
        if account.creatures[slot_index]:
            creature = account.creatures[slot_index]
            name_entry.insert(0, creature.get('name', ''))
            age_entry.insert(0, creature.get('age', ''))
            # Back-compat: allow older saves with single age mutation key
            loaded_age_1 = creature.get('age_mutation_1', creature.get('age_mutation', 'None'))
            loaded_age_2 = creature.get('age_mutation_2', 'None')
            loaded_nested = creature.get('nested_mutation', 'None')
            loaded_glimmer = creature.get('glimmer', None)

            # Normalize legacy values for Shadow/Glowtail
            legacy_map = {
                'Shadow (Age 67)': 'Shadow',
                'Shadow': 'Shadow',
                'Glowtail (age 67)': 'Glowtail',
                'Glowtail (Age 67)': 'Glowtail',
                'Glowtail': 'Glowtail',
            }
            if loaded_age_1 in legacy_map:
                loaded_age_1 = legacy_map[loaded_age_1]
            if loaded_age_2 in legacy_map:
                loaded_age_2 = legacy_map[loaded_age_2]

            # If user previously had Glowtail/Shadow as nested, migrate it into an age mutation slot
            if loaded_nested in ('Shadow (Age 67)', 'Shadow', 'Glowtail (age 67)', 'Glowtail (Age 67)', 'Glowtail'):
                migrated = 'Glowtail' if 'Glowtail' in loaded_nested else 'Shadow'
                loaded_nested = 'None'
                if loaded_age_1 in (None, '', 'None'):
                    loaded_age_1 = migrated
                elif loaded_age_2 in (None, '', 'None'):
                    loaded_age_2 = migrated

            # Glimmer used to be stored as an age mutation; migrate it to the dedicated checkbox
            glimmer_from_legacy = False
            if (loaded_age_1 or '') == 'Glimmer':
                loaded_age_1 = 'None'
                glimmer_from_legacy = True
            if (loaded_age_2 or '') == 'Glimmer':
                loaded_age_2 = 'None'
                glimmer_from_legacy = True
            if loaded_glimmer is None:
                loaded_glimmer = glimmer_from_legacy

            age_var_1.set(loaded_age_1 or 'None')
            age_var_2.set(loaded_age_2 or 'None')
            nested_var.set(loaded_nested or 'None')
            glimmer_var.set(bool(loaded_glimmer))
            trait1_var.set(creature.get('trait1', 'None'))
            trait2_var.set(creature.get('trait2', 'None'))

            # Enforce rule: if two age muts selected, nested must be None
            _sync_nested_enabled()
        
        # Store references for saving
        if not hasattr(account, '_creature_widgets'):
            account._creature_widgets = {}
        account._creature_widgets[slot_index] = {
            'name': name_entry,
            'age': age_entry,
            'age_mutation_1': age_var_1,
            'age_mutation_2': age_var_2,
            'nested_mutation': nested_var,
            'glimmer': glimmer_var,
            'trait1': trait1_var,
            'trait2': trait2_var
        }
    
    def save_creature_data(self, account, dialog):
        """Save creature data to account"""
        if not hasattr(account, '_creature_widgets'):
            return
        
        account.creatures = [None] * 17
        
        for i in range(17):
            widgets = account._creature_widgets.get(i)
            if widgets:
                name = widgets['name'].get().strip()
                if name:  # Only save if name is provided
                    age_mut_1 = widgets['age_mutation_1'].get()
                    age_mut_2 = widgets['age_mutation_2'].get()
                    nested_mut = widgets['nested_mutation'].get()
                    if age_mut_2 != 'None':
                        nested_mut = 'None'
                    account.creatures[i] = {
                        'name': name,
                        'age': widgets['age'].get().strip(),
                        'age_mutation_1': age_mut_1,
                        'age_mutation_2': age_mut_2,
                        'nested_mutation': nested_mut,
                        'glimmer': bool(widgets.get('glimmer').get()) if widgets.get('glimmer') else False,
                        'trait1': widgets['trait1'].get(),
                        'trait2': widgets['trait2'].get()
                    }
        
        # Save to config
        self.account_manager.save_config()
        messagebox.showinfo("Success", "Creature data saved!")
        dialog.destroy()
    
    def save_creature_data_inline(self, account):
        """Save creature data from inline side panel"""
        if not hasattr(account, '_creature_widgets'):
            return
        
        account.creatures = [None] * 17
        
        for i in range(17):
            widgets = account._creature_widgets.get(i)
            if widgets:
                name = widgets['name'].get().strip()
                if name:  # Only save if name is provided
                    age_mut_1 = widgets['age_mutation_1'].get()
                    age_mut_2 = widgets['age_mutation_2'].get()
                    nested_mut = widgets['nested_mutation'].get()
                    if age_mut_2 != 'None':
                        nested_mut = 'None'
                    account.creatures[i] = {
                        'name': name,
                        'age': widgets['age'].get().strip(),
                        'age_mutation_1': age_mut_1,
                        'age_mutation_2': age_mut_2,
                        'nested_mutation': nested_mut,
                        'glimmer': bool(widgets.get('glimmer').get()) if widgets.get('glimmer') else False,
                        'trait1': widgets['trait1'].get(),
                        'trait2': widgets['trait2'].get()
                    }
        
        # Save to config - this persists to disk
        self.account_manager.save_config()
        
        # Update the creature count display on the account card
        self.update_account_boxes()
        
        messagebox.showinfo("Success", "Creature data saved!")
        self.hide_side_panel()
    
    def run(self):
        """Start the GUI event loop"""
        # Check for updates in background thread
        update_thread = threading.Thread(target=self.check_for_updates, daemon=True)
        update_thread.start()
        
        self.root.mainloop()

