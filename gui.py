import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
import time
import threading
import logging
from account_manager import AccountManager
from game_launcher import GameLauncher

class CustomDropdown(tk.Frame):
    """Custom dropdown widget with dark theme styling"""
    def __init__(self, parent, variable, values, width=20, **kwargs):
        super().__init__(parent, bg='#2a2a3e', **kwargs)
        self.variable = variable
        self.values = values
        self.width = width
        self.dropdown_open = False
        self._current_canvas = None
        
        # Configure frame size
        self.config(width=width, height=40)
        
        # Main button frame
        button_frame = tk.Frame(self, bg='#363654', highlightthickness=1, 
                               highlightbackground='#4a4a5e')
        button_frame.pack(fill='both', expand=True)
        
        # Clickable label (acts as button)
        self.button = tk.Label(
            button_frame, text=variable.get(), bg='#363654', fg='#cdd6f4',
            font=('Segoe UI', 10), anchor='w', padx=10, pady=8, cursor='hand2'
        )
        self.button.pack(fill='both', expand=True, side='left')
        self.button.bind('<Button-1>', lambda e: self.toggle_dropdown())
        
        # Arrow indicator
        arrow_frame = tk.Frame(button_frame, bg='#363654')
        arrow_frame.pack(side='right', padx=5)
        arrow = tk.Label(arrow_frame, text='▼', bg='#363654', fg='#89b4fa', 
                        font=('Segoe UI', 8), cursor='hand2')
        arrow.pack()
        arrow.bind('<Button-1>', lambda e: self.toggle_dropdown())
        
        # Dropdown window (created on demand)
        self.dropdown_window = None
        
        # Update button text when variable changes
        self.variable.trace('w', lambda *args: self.button.config(text=self.variable.get()))
    
    def toggle_dropdown(self, event=None):
        if self.dropdown_open:
            self.close_dropdown()
        else:
            self.open_dropdown()
    
    def open_dropdown(self):
        if self.dropdown_window:
            return
        
        self.dropdown_open = True
        self.dropdown_window = tk.Toplevel(self)
        self.dropdown_window.overrideredirect(True)
        self.dropdown_window.configure(bg='#363654', relief='solid', borderwidth=1)
        
        # Position below button
        x = self.button.winfo_rootx()
        y = self.button.winfo_rooty() + self.button.winfo_height()
        self.dropdown_window.geometry(f'+{x}+{y}')
        
        show_scrollbar = len(self.values) > 6
        dropdown_width = self.button.winfo_width() + (14 if show_scrollbar else 0)
        dropdown_height = min(200, len(self.values) * 35)

        container = tk.Frame(self.dropdown_window, bg='#363654')
        container.pack(fill='both', expand=True)

        # Create scrollable listbox
        canvas = tk.Canvas(
            container,
            bg='#363654',
            highlightthickness=0,
            width=dropdown_width,
            height=dropdown_height
        )
        scrollbar = tk.Scrollbar(
            container,
            command=canvas.yview,
            bg='#4a4a5e',
            troughcolor='#2a2a3e',
            activebackground='#89b4fa'
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        frame = tk.Frame(canvas, bg='#363654')
        canvas.create_window((0, 0), window=frame, anchor='nw')
        
        # Add options
        for value in self.values:
            btn = tk.Button(
                frame, text=value, bg='#363654', fg='#cdd6f4',
                font=('Segoe UI', 10), relief='flat', anchor='w',
                padx=12, pady=8, cursor='hand2', borderwidth=0,
                activebackground='#89b4fa', activeforeground='white'
            )
            btn.pack(fill='x')
            btn.bind('<Button-1>', lambda e, v=value: self.select_value(v))
            
            # Hover effect
            def on_enter(e, b=btn):
                b.config(bg='#424268')
            def on_leave(e, b=btn):
                b.config(bg='#363654')
            btn.bind('<Enter>', on_enter)
            btn.bind('<Leave>', on_leave)
        
        frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
        if show_scrollbar:
            scrollbar.pack(side='right', fill='y')
            canvas.pack(side='left', fill='both', expand=True)
        else:
            canvas.pack(fill='both', expand=True)

        # Mouse wheel scrolling (bind only while hovering)
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', on_mousewheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))
        self._current_canvas = canvas
        
        # Close on click outside
        self.dropdown_window.bind('<FocusOut>', lambda e: self.close_dropdown())
        self.dropdown_window.focus_set()
    
    def close_dropdown(self):
        if self.dropdown_window:
            if self._current_canvas:
                self._current_canvas.unbind_all('<MouseWheel>')
                self._current_canvas = None
            self.dropdown_window.destroy()
            self.dropdown_window = None
            self.dropdown_open = False
    
    def select_value(self, value):
        self.variable.set(value)
        self.close_dropdown()
    
    def update_values(self, new_values):
        """Update the available values in the dropdown"""
        self.values = new_values
        if self.dropdown_open:
            self.close_dropdown()
            self.open_dropdown()

class RobloxBotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Roblox Multi-Account Manager - Creatures of Sonaria")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e1e2e')
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Macro stop flag
        self.macro_stop_flag = False
        self._hotkey_thread_id = None
        
        # Configure dropdown menu styling
        self.root.option_add('*TCombobox*Listbox.background', '#363654')
        self.root.option_add('*TCombobox*Listbox.foreground', '#cdd6f4')
        self.root.option_add('*TCombobox*Listbox.selectBackground', '#89b4fa')
        self.root.option_add('*TCombobox*Listbox.selectForeground', 'white')
        self.root.option_add('*TCombobox*Listbox.font', ('Segoe UI', 10))
        
        # Style configuration
        self.setup_styles()
        
        self.account_manager = AccountManager()
        self.game_launcher = GameLauncher(
            self.account_manager.config.get("game_url", ""),
            status_callback=self.on_game_status_update
        )
        
        # Track account display boxes
        self.account_boxes = {}
        
        self.init_ui()

        # Global stop hotkey (F8): stops any running macro
        self._start_stop_hotkey_listener()
    
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        bg_dark = '#1e1e2e'
        bg_medium = '#2a2a3e'
        bg_light = '#363654'
        accent = '#89b4fa'
        accent_hover = '#74c7ec'
        text_color = '#cdd6f4'
        
        style.configure('TFrame', background=bg_dark)
        style.configure('TLabel', background=bg_dark, foreground=text_color, font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 14, 'bold'), foreground=accent)
        style.configure('TButton', font=('Segoe UI', 10), borderwidth=0)
        style.configure('Accent.TButton', background=accent, foreground='white')
        style.map('Accent.TButton', background=[('active', accent_hover)])
        style.configure('TEntry', fieldbackground=bg_light, foreground=text_color, borderwidth=1)
        style.configure('TCheckbutton', background=bg_dark, foreground=text_color)
        # Custom combobox style for dropdowns
        style.configure('Dropdown.TCombobox',
                fieldbackground=bg_light,
                background=bg_light,
                foreground=text_color,
                arrowcolor=text_color,
                bordercolor=bg_light,
                lightcolor=bg_light,
                darkcolor=bg_light)
        style.map('Dropdown.TCombobox',
               fieldbackground=[('readonly', bg_light), ('focus', '#424268')],
               background=[('active', bg_light)],
               foreground=[('focus', text_color)],
               arrowcolor=[('active', accent)])
    
    def init_ui(self):
        # Main container
        main_frame = tk.Frame(self.root, bg='#1e1e2e')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Title
        title = ttk.Label(main_frame, text="🎮 Creatures of Sonaria - Multi-Account Manager", style='Title.TLabel')
        title.pack(pady=(0, 15))
        
        # Top section: Account view boxes (5 boxes in grid)
        self.create_account_view_section(main_frame)
        
        # Macro control panel
        self.create_macro_panel(main_frame)
        
        # Bottom section: Controls
        self.create_control_panel(main_frame)
        
        # Load saved accounts into the UI
        self.update_account_boxes()
    
    def run(self):
        self.root.mainloop()
    
    def create_account_view_section(self, parent):
        """Create the 5-box grid showing each account's view/status"""
        view_frame = tk.Frame(parent, bg='#1e1e2e')
        view_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Slot 1 (Main) - Large box on the left spanning 2 rows
        box1 = self.create_account_box(view_frame, 1, is_main_slot=True, label="Main Account")
        box1.grid(row=0, column=0, rowspan=2, padx=8, pady=8, sticky='nsew')
        self.account_boxes[1] = box1
        
        # Slots 2-5 (Alts) - 2x2 grid on the right
        positions = [
            (2, 0, 0, "Sub Account 1"),  # Slot 2: row 0, col 1
            (3, 0, 1, "Sub Account 2"),  # Slot 3: row 0, col 2
            (4, 1, 0, "Sub Account 3"),  # Slot 4: row 1, col 1
            (5, 1, 1, "Sub Account 4"),  # Slot 5: row 1, col 2
        ]
        
        for slot_num, row, col, label in positions:
            box = self.create_account_box(view_frame, slot_num, is_main_slot=False, label=label)
            box.grid(row=row, column=col+1, padx=8, pady=8, sticky='nsew')
            self.account_boxes[slot_num] = box
        
        # Configure grid weights for responsive layout
        view_frame.grid_rowconfigure(0, weight=1)
        view_frame.grid_rowconfigure(1, weight=1)
        view_frame.grid_columnconfigure(0, weight=2)  # Main slot gets more width
        view_frame.grid_columnconfigure(1, weight=1)
        view_frame.grid_columnconfigure(2, weight=1)
    
    def create_account_box(self, parent, slot_number, is_main_slot=False, label=""):
        """Create a single account display box"""
        # Color scheme based on slot type
        if is_main_slot:
            border_color = '#f38ba8'  # Red/Pink for main
            header_bg = '#4a2a3a'     # Dark red
            accent_color = '#f38ba8'
        else:
            border_color = '#f9e2af'  # Yellow for alts
            header_bg = '#4a4630'     # Dark yellow
            accent_color = '#f9e2af'
        
        box_frame = tk.Frame(parent, bg='#2a2a3e', relief='solid', borderwidth=2, 
                            highlightbackground=border_color, highlightthickness=3)
        
        # Header with slot number
        header = tk.Frame(box_frame, bg=header_bg, height=40)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        slot_label = tk.Label(header, text=label, bg=header_bg, fg=accent_color, 
                             font=('Segoe UI', 12, 'bold'))
        slot_label.pack(side='left', padx=12, pady=8)
        
        # Status indicator
        status_dot = tk.Label(header, text="●", bg=header_bg, fg='#6c7086', font=('Segoe UI', 18))
        status_dot.pack(side='right', padx=12)
        
        # Content area
        content = tk.Frame(box_frame, bg='#2a2a3e')
        content.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Account info
        username_label = tk.Label(content, text="No Account", bg='#2a2a3e', fg='#6c7086', 
                                 font=('Segoe UI', 13 if is_main_slot else 11))
        username_label.pack(pady=(15, 8))
        
        status_label = tk.Label(content, text="Empty Slot", bg='#2a2a3e', fg='#6c7086', 
                               font=('Segoe UI', 10))
        status_label.pack(pady=(0, 15))
        
        # Action buttons
        btn_frame = tk.Frame(content, bg='#2a2a3e')
        btn_frame.pack(pady=15)
        
        btn_size = (18, 8) if is_main_slot else (15, 6)
        launch_btn = tk.Button(btn_frame, text="Launch", bg='#89b4fa', fg='white', 
                               font=('Segoe UI', 10 if is_main_slot else 9, 'bold'),
                               relief='flat', padx=btn_size[0], pady=btn_size[1], 
                               cursor='hand2', state='disabled')
        launch_btn.pack(side='left', padx=5)
        
        stop_btn = tk.Button(btn_frame, text="Stop", bg='#f38ba8', fg='white', 
                            font=('Segoe UI', 10 if is_main_slot else 9, 'bold'),
                            relief='flat', padx=btn_size[0], pady=btn_size[1], 
                            cursor='hand2', state='disabled')
        stop_btn.pack(side='left', padx=5)

        # Main account only: mutation and trait selectors
        if is_main_slot:
            age_mutations = [
                "Albinism", "Diamond", "Dwarfism", "Gigantism", "Glimmer",
                "Leucistic", "Melanism", "Overgrown", "Piebald", "Shimmer"
            ]
            nested_mutations = [
                "Shadow", "Glow Tail", "Gilded"
            ]
            traits = [
                "Bite", "Damage", "Health", "Healing", "Speed",
                "Max Stamina", "Stamina Regen", "Weight"
            ]

            # Only nested mutations are mutually exclusive with each other
            nested_incompatible_group = {"Shadow", "Glow Tail", "Gilded"}

            selector_frame = tk.Frame(content, bg='#1e1e2e')
            selector_frame.pack(side='bottom', pady=(15, 8), padx=8, fill='both')

            # Title label for mutations section
            mutation_title = tk.Label(selector_frame, text="MUTATIONS", bg='#1e1e2e', fg='#89b4fa',
                                      font=('Segoe UI', 11, 'bold'))
            mutation_title.grid(row=0, column=0, columnspan=2, sticky='w', pady=(8, 4))

            # Age Mutation Picker
            age_mutation_var = tk.StringVar(value="None")
            age_mutation_panel = tk.Frame(selector_frame, bg='#252536', relief='flat', highlightthickness=1, highlightbackground='#363654')
            age_mutation_panel.grid(row=2, column=0, columnspan=2, sticky='ew', padx=4, pady=(0, 8))
            age_mutation_panel.grid_remove()

            def hide_age_mutation_panel():
                age_mutation_panel.grid_remove()

            def set_age_mutation_button_text(value):
                age_btn.config(text=f"🧬 Age: {value}")

            def render_age_mutation_panel():
                for child in age_mutation_panel.winfo_children():
                    child.destroy()

                tk.Label(age_mutation_panel, text="Select one age mutation", bg='#252536', fg='#89b4fa',
                         font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(6, 4), padx=6)

                none_btn = tk.Button(
                    age_mutation_panel,
                    text="❌ None",
                    bg='#363654',
                    fg='#cdd6f4',
                    activebackground='#424268',
                    activeforeground='#89b4fa',
                    relief='flat',
                    padx=10, pady=5,
                    cursor='hand2',
                    font=('Segoe UI', 9),
                    command=lambda: (age_mutation_var.set("None"), set_age_mutation_button_text("None"), hide_age_mutation_panel())
                )
                none_btn.pack(anchor='w', pady=2, padx=6, fill='x')

                for name in age_mutations:
                    fg = '#cdd6f4'

                    def make_cmd(n=name):
                        return lambda: (age_mutation_var.set(n), set_age_mutation_button_text(n), hide_age_mutation_panel())

                    btn = tk.Checkbutton(
                        age_mutation_panel,
                        text=f"✓ {name}",
                        bg='#252536',
                        fg=fg,
                        activebackground='#2a2a3e',
                        activeforeground='#89b4fa',
                        selectcolor='#363654',
                        highlightthickness=0,
                        font=('Segoe UI', 9),
                        cursor='hand2',
                        command=make_cmd(),
                        onvalue=True,
                        offvalue=False
                    )
                    if age_mutation_var.get() == name:
                        btn.select()
                    btn.pack(anchor='w', pady=1, padx=8)

            def open_age_mutation_picker():
                render_age_mutation_panel()
                age_mutation_panel.grid()

            # Nested Mutation Picker
            nested_mutation_var = tk.StringVar(value="None")
            nested_mutation_panel = tk.Frame(selector_frame, bg='#252536', relief='flat', highlightthickness=1, highlightbackground='#363654')
            nested_mutation_panel.grid(row=3, column=0, columnspan=2, sticky='ew', padx=4, pady=(0, 8))
            nested_mutation_panel.grid_remove()

            def hide_nested_mutation_panel():
                nested_mutation_panel.grid_remove()

            def set_nested_mutation_button_text(value):
                nested_btn.config(text=f"🎭 Nested: {value}")

            def render_nested_mutation_panel():
                for child in nested_mutation_panel.winfo_children():
                    child.destroy()

                tk.Label(nested_mutation_panel, text="Select one nested mutation", bg='#252536', fg='#89b4fa',
                         font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(6, 4), padx=6)

                none_btn = tk.Button(
                    nested_mutation_panel,
                    text="❌ None",
                    bg='#363654',
                    fg='#cdd6f4',
                    activebackground='#424268',
                    activeforeground='#89b4fa',
                    relief='flat',
                    padx=10, pady=5,
                    cursor='hand2',
                    font=('Segoe UI', 9),
                    command=lambda: (nested_mutation_var.set("None"), set_nested_mutation_button_text("None"), hide_nested_mutation_panel())
                )
                none_btn.pack(anchor='w', pady=2, padx=6, fill='x')

                for name in nested_mutations:
                    fg = '#cdd6f4'

                    def make_cmd(n=name):
                        return lambda: (nested_mutation_var.set(n), set_nested_mutation_button_text(n), hide_nested_mutation_panel())

                    btn = tk.Checkbutton(
                        nested_mutation_panel,
                        text=f"✓ {name}",
                        bg='#252536',
                        fg=fg,
                        activebackground='#2a2a3e',
                        activeforeground='#89b4fa',
                        selectcolor='#363654',
                        highlightthickness=0,
                        font=('Segoe UI', 9),
                        cursor='hand2',
                        command=make_cmd(),
                        onvalue=True,
                        offvalue=False
                    )
                    if nested_mutation_var.get() == name:
                        btn.select()
                    btn.pack(anchor='w', pady=1, padx=8)

            def open_nested_mutation_picker():
                render_nested_mutation_panel()
                nested_mutation_panel.grid()

            # Buttons to open pickers with improved styling
            age_btn = tk.Button(selector_frame, text="🧬 Age: None", bg='#363654', fg='#89b4fa',
                                activebackground='#424268', activeforeground='#89b4fa', relief='flat',
                                padx=12, pady=10, cursor='hand2', width=20, font=('Segoe UI', 10, 'bold'),
                                command=open_age_mutation_picker)
            nested_btn = tk.Button(selector_frame, text="🎭 Nested: None", bg='#363654', fg='#89b4fa',
                                   activebackground='#424268', activeforeground='#89b4fa', relief='flat',
                                   padx=12, pady=10, cursor='hand2', width=20, font=('Segoe UI', 10, 'bold'),
                                   command=open_nested_mutation_picker)
            age_btn.grid(row=1, column=0, padx=4, pady=(0, 6), sticky='ew')
            nested_btn.grid(row=1, column=1, padx=4, pady=(0, 6), sticky='ew')

            # Separator
            separator = tk.Frame(selector_frame, bg='#363654', height=1)
            separator.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(8, 8), padx=4)

            tk.Label(selector_frame, text="TRAITS", bg='#1e1e2e', fg='#89b4fa',
                     font=('Segoe UI', 11, 'bold')).grid(row=5, column=0, columnspan=2, sticky='w', pady=(8, 4))

            trait_var1 = tk.StringVar(value="None")
            trait_var2 = tk.StringVar(value="None")

            def set_trait_button_text(btn, value):
                idx = 1 if btn == trait_btn1 else 2
                btn.config(text=f"🎯 Trait {idx}: {value}")

            active_trait_target = {"var": None, "other": None, "btn": None}

            trait_panel = tk.Frame(selector_frame, bg='#252536', relief='flat', highlightthickness=1, highlightbackground='#363654')
            trait_panel.grid(row=7, column=0, columnspan=2, sticky='ew', padx=4, pady=(0, 8))
            trait_panel.grid_remove()

            def hide_trait_panel():
                trait_panel.grid_remove()

            def render_trait_panel():
                for child in trait_panel.winfo_children():
                    child.destroy()

                target_var = active_trait_target["var"]
                button_widget = active_trait_target["btn"]

                tk.Label(trait_panel, text="Select up to 2 traits", bg='#252536', fg='#89b4fa',
                         font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(6, 4), padx=6)

                selected_set = {v for v in [trait_var1.get(), trait_var2.get()] if v != "None"}
                max_selected = len(selected_set)

                none_btn = tk.Button(
                    trait_panel,
                    text="❌ None",
                    bg='#363654',
                    fg='#cdd6f4',
                    activebackground='#424268',
                    activeforeground='#89b4fa',
                    relief='flat',
                    padx=10, pady=5,
                    cursor='hand2',
                    font=('Segoe UI', 9),
                    command=lambda: (target_var.set("None"), set_trait_button_text(button_widget, "None"), hide_trait_panel())
                )
                none_btn.pack(anchor='w', pady=2, padx=6, fill='x')

                for name in traits:
                    would_exceed = (max_selected >= 2) and (name not in selected_set)
                    disabled = would_exceed
                    fg = '#6c7086' if disabled else '#cdd6f4'

                    def make_cmd(n=name, dis=disabled):
                        if dis:
                            return lambda: None
                        return lambda: (target_var.set(n), set_trait_button_text(button_widget, n), hide_trait_panel())

                    btn = tk.Checkbutton(
                        trait_panel,
                        text=f"✓ {name}",
                        bg='#252536',
                        fg=fg,
                        activebackground='#2a2a3e',
                        activeforeground='#89b4fa',
                        selectcolor='#363654',
                        highlightthickness=0,
                        font=('Segoe UI', 9),
                        cursor='hand2',
                        command=make_cmd(),
                        onvalue=True,
                        offvalue=False
                    )
                    if target_var.get() == name:
                        btn.select()
                    if disabled:
                        btn.configure(state='disabled')
                    btn.pack(anchor='w', pady=1, padx=8)

            def open_trait_picker(target_var, other_var, button_widget):
                active_trait_target.update({"var": target_var, "other": other_var, "btn": button_widget})
                render_trait_panel()
                trait_panel.grid()

            trait_btn1 = tk.Button(selector_frame, text="🎯 Trait 1: None", bg='#363654', fg='#89b4fa',
                                 activebackground='#424268', activeforeground='#89b4fa', relief='flat',
                                 padx=12, pady=10, cursor='hand2', width=20, font=('Segoe UI', 10, 'bold'),
                                 command=lambda: open_trait_picker(trait_var1, trait_var2, trait_btn1))
            trait_btn2 = tk.Button(selector_frame, text="🎯 Trait 2: None", bg='#363654', fg='#89b4fa',
                                 activebackground='#424268', activeforeground='#89b4fa', relief='flat',
                                 padx=12, pady=10, cursor='hand2', width=20, font=('Segoe UI', 10, 'bold'),
                                 command=lambda: open_trait_picker(trait_var2, trait_var1, trait_btn2))
            trait_btn1.grid(row=6, column=0, padx=4, pady=(0, 6), sticky='ew')
            trait_btn2.grid(row=6, column=1, padx=4, pady=(0, 6), sticky='ew')

            # Store selectors on the box for future use
            box_frame.age_mutation_var = age_mutation_var
            box_frame.nested_mutation_var = nested_mutation_var
            box_frame.trait_vars = (trait_var1, trait_var2)
        
        # Store references
        box_frame.username_label = username_label
        box_frame.status_label = status_label
        box_frame.status_dot = status_dot
        box_frame.launch_btn = launch_btn
        box_frame.stop_btn = stop_btn
        box_frame.account = None
        box_frame.is_main_slot = is_main_slot
        
        return box_frame
    
    
    def create_macro_panel(self, parent):
        """Create macro control panel for automated actions"""
        macro_frame = tk.Frame(parent, bg='#2a2a3e', relief='solid', borderwidth=1)
        macro_frame.pack(fill='x', pady=(0, 10))
        
        inner = tk.Frame(macro_frame, bg='#2a2a3e')
        inner.pack(fill='both', expand=True, padx=20, pady=12)
        
        # Title
        tk.Label(inner, text="🎮 MACRO CONTROLS", 
                bg='#2a2a3e', fg='#89b4fa', font=('Segoe UI', 11, 'bold')).pack(side='left', padx=(0, 20))
        
        # Enable Macro Mode checkbox
        self.macros_enabled_var = tk.BooleanVar(value=self.account_manager.config.get('macros_enabled', False))
        macro_toggle = tk.Checkbutton(inner, text="Enable Macro Mode (OS-level input)", variable=self.macros_enabled_var,
                                     bg='#2a2a3e', fg='#cdd6f4', font=('Segoe UI', 9, 'bold'),
                                     selectcolor='#2a2a3e', activebackground='#2a2a3e', activeforeground='#89b4fa',
                                     command=self.toggle_macro_mode)
        macro_toggle.pack(side='left', padx=(0, 15))

        # Test key macro button
        self.key_btn = tk.Button(inner, text="⌨️ TEST KEY (SPACE)", command=self.test_key_macro,
                   bg='#a6e3a1', fg='#1e1e2e', font=('Segoe UI', 12, 'bold'),
                   relief='flat', padx=22, pady=12, cursor='hand2', state='disabled')
        self.key_btn.pack(side='left', padx=(0, 10))

        # Test left click macro button
        self.click_btn = tk.Button(inner, text="🖱️ TEST LEFT CLICK", command=self.test_left_click_macro,
                     bg='#89b4fa', fg='white', font=('Segoe UI', 12, 'bold'),
                     relief='flat', padx=22, pady=12, cursor='hand2', state='disabled')
        self.click_btn.pack(side='left', padx=(0, 10))
        
        # Stop macro button
        self.stop_btn = tk.Button(inner, text="⏹️ STOP (F8)", command=self.stop_macro,
                            bg='#f38ba8', fg='white', font=('Segoe UI', 10, 'bold'),
                            relief='flat', padx=15, pady=10, cursor='hand2', state='disabled')
        self.stop_btn.pack(side='left', padx=(0, 15))
        
        # Status label
        self.macro_status_label = tk.Label(inner, text="Ready", bg='#2a2a3e', fg='#cdd6f4', 
                                           font=('Segoe UI', 10))
        self.macro_status_label.pack(side='left', padx=(15, 0))
    
    def toggle_macro_mode(self):
        """Toggle macro mode on/off"""
        enabled = self.macros_enabled_var.get()
        self.account_manager.config['macros_enabled'] = enabled
        self.account_manager.save_config()
        
        # Update button states
        btn_state = 'normal' if enabled else 'disabled'
        self.key_btn.config(state=btn_state)
        self.click_btn.config(state=btn_state)
        self.stop_btn.config(state=btn_state)
        
        if enabled:
            self.macro_status_label.config(text="⚠️ Macro Mode ENABLED (OS-level input active)", fg='#f9e2af')
            logging.warning("MACRO MODE ENABLED - OS-level input injection is active")
        else:
            self.macro_status_label.config(text="Macro Mode disabled", fg='#cdd6f4')
            logging.info("Macro mode disabled")
        
        self.root.after(3000, lambda: self.macro_status_label.config(text="Ready", fg='#cdd6f4'))
    
    def _require_windows_or_show(self) -> bool:
        window_count = self.game_launcher.window_controller.get_window_count()
        logging.info(f"Macro check: Found {window_count} windows")
        logging.info(f"Tracked windows: {self.game_launcher.window_controller.window_handles}")
        if window_count == 0:
            messagebox.showinfo("No Windows", "No active game windows found. Launch accounts first!")
            return False
        return True

    def test_key_macro(self):
        """Test macro: press SPACE once per window in a cycle."""
        if not self.macros_enabled_var.get():
            messagebox.showwarning("Macro Disabled", "Enable 'Macro Mode' first!")
            return
        
        try:
            if not self._require_windows_or_show():
                return

            self.macro_status_label.config(text="Testing SPACE key...", fg='#f9e2af')
            self.root.update()

            t = threading.Thread(target=self._test_key_macro_thread, args=('SPACE',), daemon=False)
            t.start()
        except Exception as e:
            logging.error(f"Key test macro error: {e}", exc_info=True)
            messagebox.showerror("Macro Error", f"Error running key test macro: {e}")

    def test_left_click_macro(self):
        """Test macro: left click center of each window in a cycle."""
        if not self.macros_enabled_var.get():
            messagebox.showwarning("Macro Disabled", "Enable 'Macro Mode' first!")
            return
        
        try:
            if not self._require_windows_or_show():
                return

            self.macro_status_label.config(text="Testing left click...", fg='#f9e2af')
            self.root.update()

            t = threading.Thread(target=self._test_left_click_macro_thread, daemon=False)
            t.start()
        except Exception as e:
            logging.error(f"Click test macro error: {e}", exc_info=True)
            messagebox.showerror("Macro Error", f"Error running click test macro: {e}")
    
    def stop_macro(self):
        """Stop the currently running macro"""
        self.macro_stop_flag = True
        logging.info("Stop signal sent to macro")
        self.macro_status_label.config(text="Stopping... (F8)", fg='#f9e2af')
        self.root.update()

    def _test_key_macro_thread(self, key_name: str):
        try:
            wc = self.game_launcher.window_controller
            self.macro_stop_flag = False
            presses = 0

            start = time.time()
            duration = 10  # short test
            while time.time() - start < duration and not self.macro_stop_flag:
                hwnds = wc.get_all_hwnds()
                for hwnd in hwnds:
                    if self.macro_stop_flag:
                        break
                    if wc.send_key_press(hwnd, key_name, hold_duration=0.04):
                        presses += 1
                        logging.info(f"TEST KEY: Sent {key_name} to hwnd={hwnd} total={presses}")
                    time.sleep(0.15)
                time.sleep(0.25)

            if self.macro_stop_flag:
                self.macro_status_label.config(text=f"Stopped (F8) — {presses} keys", fg='#f38ba8')
            else:
                self.macro_status_label.config(text=f"Key test done — {presses} keys", fg='#a6e3a1')
            self.root.after(3000, lambda: self.macro_status_label.config(text="Ready", fg='#cdd6f4'))
        except Exception as e:
            logging.error(f"Key test macro thread error: {e}", exc_info=True)

    def _test_left_click_macro_thread(self):
        try:
            wc = self.game_launcher.window_controller
            self.macro_stop_flag = False
            clicks = 0

            start = time.time()
            duration = 10  # short test
            while time.time() - start < duration and not self.macro_stop_flag:
                hwnds = wc.get_all_hwnds()
                for hwnd in hwnds:
                    if self.macro_stop_flag:
                        break
                    if wc.click_window_center(hwnd):
                        clicks += 1
                        logging.info(f"TEST CLICK: Clicked center hwnd={hwnd} total={clicks}")
                    time.sleep(0.20)
                time.sleep(0.25)

            if self.macro_stop_flag:
                self.macro_status_label.config(text=f"Stopped (F8) — {clicks} clicks", fg='#f38ba8')
            else:
                self.macro_status_label.config(text=f"Click test done — {clicks} clicks", fg='#a6e3a1')
            self.root.after(3000, lambda: self.macro_status_label.config(text="Ready", fg='#cdd6f4'))
        except Exception as e:
            logging.error(f"Click test macro thread error: {e}", exc_info=True)

    def _start_stop_hotkey_listener(self):
        """Register global hotkey F8 to stop macros (works even if GUI isn't focused)."""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL('user32', use_last_error=True)
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

            WM_HOTKEY = 0x0312
            WM_QUIT = 0x0012
            HOTKEY_ID = 1
            VK_F8 = 0x77
            MOD_NOREPEAT = 0x4000

            RegisterHotKey = user32.RegisterHotKey
            UnregisterHotKey = user32.UnregisterHotKey
            GetMessageW = user32.GetMessageW
            TranslateMessage = user32.TranslateMessage
            DispatchMessageW = user32.DispatchMessageW
            PostThreadMessageW = user32.PostThreadMessageW
            GetCurrentThreadId = kernel32.GetCurrentThreadId

            def loop():
                tid = GetCurrentThreadId()
                self._hotkey_thread_id = int(tid)

                if not RegisterHotKey(None, HOTKEY_ID, MOD_NOREPEAT, VK_F8):
                    logging.warning("Global hotkey F8 could not be registered")
                    return

                try:
                    msg = wintypes.MSG()
                    while True:
                        ret = GetMessageW(ctypes.byref(msg), None, 0, 0)
                        if ret == 0:
                            break  # WM_QUIT
                        if ret == -1:
                            break
                        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                            self.stop_macro()
                        TranslateMessage(ctypes.byref(msg))
                        DispatchMessageW(ctypes.byref(msg))
                finally:
                    UnregisterHotKey(None, HOTKEY_ID)

            t = threading.Thread(target=loop, daemon=True)
            t.start()
        except Exception as e:
            logging.warning(f"Failed to start hotkey listener: {e}")
    
    def update_macro_target_dropdown(self):
        """Update macro target dropdown with active accounts (not used in simplified version)"""
        pass
    
    def create_control_panel(self, parent):
        """Create the control panel with account management and settings"""
        control_frame = tk.Frame(parent, bg='#2a2a3e', relief='solid', borderwidth=1)
        control_frame.pack(fill='x', pady=(0, 0))
        
        # Inner padding
        inner = tk.Frame(control_frame, bg='#2a2a3e')
        inner.pack(fill='both', expand=True, padx=20, pady=15)
        
        # Left section: Add Account
        left_frame = tk.Frame(inner, bg='#2a2a3e')
        left_frame.pack(side='left', fill='both', expand=True)
        
        add_label = tk.Label(left_frame, text="Add New Account", bg='#2a2a3e', fg='#89b4fa', font=('Segoe UI', 11, 'bold'))
        add_label.grid(row=0, column=0, columnspan=5, sticky='w', pady=(0, 10))
        
        tk.Label(left_frame, text="Username:", bg='#2a2a3e', fg='#cdd6f4', font=('Segoe UI', 9)).grid(row=1, column=0, sticky='w', padx=(0, 5))
        self.username_input = tk.Entry(left_frame, bg='#363654', fg='#cdd6f4', font=('Segoe UI', 10), relief='flat', borderwidth=1, insertbackground='#cdd6f4')
        self.username_input.grid(row=1, column=1, padx=5, ipady=5, ipadx=5)
        
        tk.Label(left_frame, text="Password:", bg='#2a2a3e', fg='#cdd6f4', font=('Segoe UI', 9)).grid(row=1, column=2, sticky='w', padx=(15, 5))
        self.password_input = tk.Entry(left_frame, bg='#363654', fg='#cdd6f4', font=('Segoe UI', 10), show='●', relief='flat', borderwidth=1, insertbackground='#cdd6f4')
        self.password_input.grid(row=1, column=3, padx=5, ipady=5, ipadx=5)
        
        self.main_account_var = tk.BooleanVar()
        main_check = tk.Checkbutton(left_frame, text="Main Account", variable=self.main_account_var, bg='#2a2a3e', fg='#cdd6f4', 
                                   selectcolor='#363654', activebackground='#2a2a3e', activeforeground='#89b4fa', font=('Segoe UI', 9))
        main_check.grid(row=1, column=4, padx=(15, 5))
        
        add_btn = tk.Button(left_frame, text="➕ Add Account", command=self.add_account, bg='#a6e3a1', fg='#1e1e2e', 
                          font=('Segoe UI', 10, 'bold'), relief='flat', padx=20, pady=8, cursor='hand2')
        add_btn.grid(row=1, column=5, padx=(15, 0))
        
        # Right section: Global controls and settings
        right_frame = tk.Frame(inner, bg='#2a2a3e')
        right_frame.pack(side='right', padx=(20, 0))
        
        # Private Server Link
        tk.Label(right_frame, text="Private Server Link:", bg='#2a2a3e', fg='#89b4fa', font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 5))
        server_frame = tk.Frame(right_frame, bg='#2a2a3e')
        server_frame.pack(fill='x', pady=(0, 10))
        
        self.private_server_input = tk.Entry(server_frame, bg='#363654', fg='#cdd6f4', font=('Segoe UI', 9), width=50, relief='flat', borderwidth=1, insertbackground='#cdd6f4')
        self.private_server_input.pack(side='left', ipady=5, ipadx=5)
        self.private_server_input.insert(0, self.account_manager.config.get("private_server_link", ""))
        
        save_server_btn = tk.Button(server_frame, text="💾 Save", command=self.save_private_server, bg='#89b4fa', fg='white',
                                   font=('Segoe UI', 9, 'bold'), relief='flat', padx=15, pady=5, cursor='hand2')
        save_server_btn.pack(side='left', padx=(5, 0))
        
        # Control buttons
        btn_container = tk.Frame(right_frame, bg='#2a2a3e')
        btn_container.pack(pady=(5, 0))
        
        launch_all_btn = tk.Button(btn_container, text="🚀 Launch All Accounts", command=self.launch_all_accounts, 
                                  bg='#89b4fa', fg='white', font=('Segoe UI', 10, 'bold'), relief='flat', 
                                  padx=20, pady=10, cursor='hand2')
        launch_all_btn.pack(side='left', padx=5)
        
        stop_all_btn = tk.Button(btn_container, text="⏹ Stop All", command=self.stop_all_accounts,
                               bg='#f38ba8', fg='white', font=('Segoe UI', 10, 'bold'), relief='flat',
                               padx=20, pady=10, cursor='hand2')
        stop_all_btn.pack(side='left', padx=5)
        
        view_logs_btn = tk.Button(btn_container, text="📋 View Logs", command=self.open_log_viewer,
                                bg='#cba6f7', fg='white', font=('Segoe UI', 10, 'bold'), relief='flat',
                                padx=20, pady=10, cursor='hand2')
        view_logs_btn.pack(side='left', padx=5)
    
    def add_account(self):
        username = self.username_input.get().strip()
        password = self.password_input.get().strip()
        is_main = self.main_account_var.get()
        
        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter both username and password")
            return
        
        if self.account_manager.add_account(username, password, is_main):
            self.username_input.delete(0, tk.END)
            self.password_input.delete(0, tk.END)
            self.main_account_var.set(False)
            self.update_account_boxes()
            messagebox.showinfo("Success", f"Account '{username}' added successfully")
        else:
            messagebox.showwarning("Error", "Failed to add account (max limit reached or duplicate)")
    
    def update_account_boxes(self):
        """Update all 5 account boxes with current account info"""
        accounts = self.account_manager.get_all_accounts()
        
        # Separate main and sub accounts
        main_accounts = [acc for acc in accounts if acc.is_main]
        sub_accounts = [acc for acc in accounts if not acc.is_main]
        
        # Update Slot 1 (Main Account)
        box = self.account_boxes[1]
        if main_accounts:
            account = main_accounts[0]
            box.account = account
            
            # Update display
            box.username_label.config(text=account.username, fg='#cdd6f4')
            box.status_label.config(text=account.status.title(), fg='#a6adc8')
            
            # Update status indicator color
            status_colors = {
                'offline': '#6c7086',
                'launching': '#f9e2af',
                'online': '#a6e3a1',
                'error': '#f38ba8'
            }
            box.status_dot.config(fg=status_colors.get(account.status.lower(), '#6c7086'))
            
            # Enable buttons
            box.launch_btn.config(state='normal', command=lambda a=account: self.launch_account(a))
            box.stop_btn.config(state='normal', command=lambda a=account: self.stop_account(a))
        else:
            # Empty main slot
            box.account = None
            box.username_label.config(text="No Account", fg='#6c7086')
            box.status_label.config(text="Empty Slot", fg='#6c7086')
            box.status_dot.config(fg='#6c7086')
            box.launch_btn.config(state='disabled')
            box.stop_btn.config(state='disabled')
        
        # Update Slots 2-5 (Sub Accounts)
        for slot_num in range(2, 6):
            box = self.account_boxes[slot_num]
            sub_index = slot_num - 2  # 0-3 for sub accounts
            
            if sub_index < len(sub_accounts):
                account = sub_accounts[sub_index]
                box.account = account
                
                # Update display
                box.username_label.config(text=account.username, fg='#cdd6f4')
                box.status_label.config(text=account.status.title(), fg='#a6adc8')
                
                # Update status indicator color
                status_colors = {
                    'offline': '#6c7086',
                    'launching': '#f9e2af',
                    'online': '#a6e3a1',
                    'error': '#f38ba8'
                }
                box.status_dot.config(fg=status_colors.get(account.status.lower(), '#6c7086'))
                
                # Enable buttons
                box.launch_btn.config(state='normal', command=lambda a=account: self.launch_account(a))
                box.stop_btn.config(state='normal', command=lambda a=account: self.stop_account(a))
            else:
                # Empty sub account slot
                box.account = None
                box.username_label.config(text="No Account", fg='#6c7086')
                box.status_label.config(text="Empty Slot", fg='#6c7086')
                box.status_dot.config(fg='#6c7086')
                box.launch_btn.config(state='disabled')
                box.stop_btn.config(state='disabled')
    
    def launch_account(self, account):
        """Launch a specific account"""
        server_link = self.private_server_input.get().strip()
        if server_link:
            self.game_launcher.game_url = server_link
        self.game_launcher.launch_game(account)
    
    def stop_account(self, account):
        """Stop a specific account"""
        # Update status
        account.status = "offline"
        self.update_account_boxes()
    
    def launch_all_accounts(self):
        """Launch all configured accounts with staggered timing"""
        server_link = self.private_server_input.get().strip()
        if not server_link:
            messagebox.showwarning("Missing Link", "Please enter a private server link first")
            return
        
        self.game_launcher.game_url = server_link
        
        # Get accounts and sort: main first, then subs
        accounts = self.account_manager.get_all_accounts()
        main_accounts = [acc for acc in accounts if acc.is_main]
        sub_accounts = [acc for acc in accounts if not acc.is_main]
        sorted_accounts = main_accounts + sub_accounts
        
        # Launch with staggering
        self.game_launcher.launch_all_staggered(sorted_accounts)
    
    def stop_all_accounts(self):
        """Stop all running game instances"""
        self.game_launcher.stop_all_games()
        for account in self.account_manager.get_all_accounts():
            account.status = "offline"
        self.update_account_boxes()
    
    def save_private_server(self):
        """Save the private server link to config"""
        link = self.private_server_input.get().strip()
        self.account_manager.config["private_server_link"] = link
        self.account_manager.save_config()
        messagebox.showinfo("Saved", "Private server link saved!")
    
    def on_game_status_update(self, username: str, status: str):
        """Callback from game launcher when status changes"""
        account = self.account_manager.get_account(username)
        if account:
            account.status = status
            # Update GUI in thread-safe way
            self.root.after(0, self.update_account_boxes)
            # Update macro target dropdown
            self.root.after(100, self.update_macro_target_dropdown)
    
    def on_closing(self):
        """Handle window close event"""
        # Stop all running games
        self.game_launcher.stop_all_games()
        # Destroy the window
        self.root.destroy()
    
    def open_log_viewer(self):
        """Open a window to view current session logs"""
        log_window = tk.Toplevel(self.root)
        log_window.title("Session Logs")
        log_window.geometry("900x600")
        log_window.configure(bg='#1e1e2e')
        
        # Header
        header_frame = tk.Frame(log_window, bg='#2a2a3e', height=50)
        header_frame.pack(fill='x', padx=10, pady=(10, 0))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="📋 Current Session Logs", bg='#2a2a3e', fg='#89b4fa',
                              font=('Segoe UI', 14, 'bold'))
        title_label.pack(side='left', padx=15, pady=10)
        
        # Button frame
        btn_frame = tk.Frame(header_frame, bg='#2a2a3e')
        btn_frame.pack(side='right', padx=15)
        
        refresh_btn = tk.Button(btn_frame, text="🔄 Refresh", command=lambda: self.refresh_logs(log_text),
                               bg='#89b4fa', fg='white', font=('Segoe UI', 9, 'bold'), relief='flat',
                               padx=15, pady=5, cursor='hand2')
        refresh_btn.pack(side='left', padx=3)
        
        download_btn = tk.Button(btn_frame, text="💾 Download", command=lambda: self.download_logs(log_window),
                                bg='#a6e3a1', fg='#1e1e2e', font=('Segoe UI', 9, 'bold'), relief='flat',
                                padx=15, pady=5, cursor='hand2')
        download_btn.pack(side='left', padx=3)
        
        # Log text area
        log_frame = tk.Frame(log_window, bg='#1e1e2e')
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        log_text = scrolledtext.ScrolledText(log_frame, bg='#181825', fg='#cdd6f4',
                                             font=('Consolas', 9), relief='flat',
                                             insertbackground='#cdd6f4', selectbackground='#45475a')
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
    
    def download_logs(self, parent_window):
        """Save logs to a file"""
        logs = GameLauncher.get_session_logs()
        
        if not logs:
            messagebox.showinfo("No Logs", "No logs available to download.", parent=parent_window)
            return
        
        # Generate default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"roblox_bot_session_{timestamp}.log"
        
        # Ask user where to save
        file_path = filedialog.asksaveasfilename(
            parent=parent_window,
            title="Save Logs",
            defaultextension=".log",
            initialfile=default_filename,
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(logs))
                messagebox.showinfo("Success", f"Logs saved to:\n{file_path}", parent=parent_window)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save logs:\n{str(e)}", parent=parent_window)

if __name__ == "__main__":
    app = RobloxBotGUI()
    app.run()
