"""
Simplified GUI for Account Management Only (No Macros)
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime
import time
import threading
import json
import random
import math
import requests
from account_manager import AccountManager
from game_launcher import GameLauncher

APP_VERSION = "1.0.1"
GITHUB_REPO = "VRHighLow/Creatures-Of-Sonaria-Account-Manager"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

class RobloxBotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Roblox Account Manager - Creatures of Sonaria (Lite)")
        self.root.geometry("1280x760")
        self.root.minsize(960, 600)
        self.colors = {
            "bg": "#0b0d12",
            "panel": "#11151d",
            "panel_alt": "#141a24",
            "input": "#0b1220",
            "text": "#e6edf3",
            "muted": "#8b949e",
            "accent": "#7f8cff",
            "accent_hover": "#9aa4ff",
            "success": "#3bd671",
            "danger": "#ff5c5c",
            "warning": "#e6c96a",
            "stroke": "#1f2836",
            "bg_top": "#0a0d14",
            "bg_mid": "#0c101b",
            "bg_bottom": "#0a0c12",
            "glow_teal": "#1a6d7a",
            "glow_blue": "#1b2a6b",
            "particle": "#9fe7ff",
            "particle_dim": "#3a6f86",
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

        # Background visuals
        self._bg_size = (0, 0)
        self._bg_particles = []
        self._bg_nebulas = []
        self._bg_animating = False
        self._bg_render_job = None
        self._accent_bars = []
        self._accent_phase = 0

        # UI motion accents
        self._title_phase = 0
        self._title_label = None

        # Search highlight animation
        self._search_phase = 0

        # Side panel animation state
        self._side_panel_anim_job = None
        self._side_panel_animating = False

        # Card hover tracking (robust against fast mouse moves)
        self._hovered_card = None
        self._hover_tracking_enabled = False

        # Scroll routing (mouse wheel should work anywhere over scrollable panels)
        self._scroll_canvases = []
        self._global_scroll_bound = False
        
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
        style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), foreground=accent)
        style.configure('TButton', font=('Segoe UI', 10), borderwidth=0)
        style.configure('Accent.TButton', background=accent, foreground='white')
        style.map('Accent.TButton', background=[('active', accent_hover)])
        style.configure('TEntry', fieldbackground=bg_light, foreground=text_color, borderwidth=1)
        style.configure('TCheckbutton', background=bg_dark, foreground=text_color)

        # Scrollbars (match app theme; avoids bright/white default bars)
        try:
            style.configure(
                'Cos.Vertical.TScrollbar',
                troughcolor=bg_dark,
                background=self.colors["panel_alt"],
                bordercolor=self.colors["stroke"],
                arrowcolor=self.colors["muted"],
                lightcolor=self.colors["stroke"],
                darkcolor=self.colors["stroke"],
                relief='flat',
            )
            style.map(
                'Cos.Vertical.TScrollbar',
                background=[('active', self.colors["panel"])],
                arrowcolor=[('active', self.colors["text"])],
            )
        except Exception:
            pass

    def _register_scroll_canvas(self, canvas: tk.Canvas):
        """Register a canvas as a scroll target for global mouse-wheel routing."""
        if canvas is None:
            return
        try:
            if canvas in self._scroll_canvases:
                return
        except Exception:
            pass
        self._scroll_canvases.append(canvas)

    def _init_global_scroll_routing(self):
        """Route mouse wheel to the scrollable panel under the cursor (Windows)."""
        if self._global_scroll_bound:
            return
        self._global_scroll_bound = True

        def is_descendant(widget, ancestor) -> bool:
            try:
                while widget is not None:
                    if widget == ancestor:
                        return True
                    parent_name = widget.winfo_parent()
                    if not parent_name:
                        break
                    widget = widget.nametowidget(parent_name)
            except Exception:
                return False
            return False

        def on_mousewheel(event):
            try:
                w = self.root.winfo_containing(event.x_root, event.y_root)
            except Exception:
                return
            if w is None:
                return

            # Prefer the most recently registered scroll canvas (side panel usually comes last).
            for canvas in reversed(list(self._scroll_canvases)):
                try:
                    if not canvas.winfo_exists():
                        continue
                    if is_descendant(w, canvas):
                        canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
                        return
                except Exception:
                    continue

        # Bind globally; handler chooses the correct canvas by cursor position.
        self.root.bind_all('<MouseWheel>', on_mousewheel, add=True)
    
    def init_ui(self):
        # Main container split into left (content) and right (side panel)
        # Background canvas must live inside this container; otherwise it gets covered by an opaque full-window Frame.
        main_container = tk.Frame(self.root, bg=self.colors["bg"])
        main_container.place(x=0, y=0, relwidth=1, relheight=1)

        # Background canvas (behind all content)
        self.bg_canvas = tk.Canvas(main_container, bg=self.colors["bg"], highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Left side: main content area
        # Add a bit more outer padding so the animated background is visible around the UI.
        self.main_content = tk.Frame(main_container, bg=self.colors["bg"])
        self.main_content.pack(side='left', fill='both', expand=True, padx=24, pady=18)
        
        # Right side: sliding panel (initially hidden)
        # Use an outer shell matching the app background, with an inset "card".
        self.side_panel = tk.Frame(main_container, bg=self.colors["bg"], highlightthickness=0)
        self.side_panel_card = tk.Frame(
            self.side_panel,
            bg=self.colors["panel_alt"],
            highlightthickness=1,
            highlightbackground=self.colors["stroke"],
        )
        self.side_panel_card.pack(fill='both', expand=True, padx=12, pady=12)
        self.side_panel_inner = tk.Frame(self.side_panel_card, bg=self.colors["panel_alt"])
        self.side_panel_inner.pack(fill='both', expand=True)
        self.side_panel_visible = False
        
        # Header card
        header = tk.Frame(self.main_content, bg=self.colors["panel_alt"], relief='flat', highlightthickness=1, highlightbackground=self.colors["stroke"])
        header.pack(fill='x', pady=(0, 15))
        header_bar = tk.Frame(header, bg=self.colors["accent"], height=4)
        header_bar.pack(fill='x', side='top')
        self._register_accent_bar(header_bar)
        header_inner = tk.Frame(header, bg=self.colors["panel_alt"])
        header_inner.pack(fill='x', padx=18, pady=16)

        title = tk.Label(
            header_inner,
            text="🎮 Roblox Account Manager",
            bg=self.colors["panel_alt"],
            fg=self.colors["accent"],
            font=('Bahnschrift SemiBold', 20),
        )
        title.pack(expand=True)
        self._title_label = title

        subtitle = tk.Label(
            header_inner,
            text=f"Lite Edition v{APP_VERSION}",
            bg=self.colors["panel_alt"],
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

        # Ensure background is behind content
        try:
            self.bg_canvas.lower()
        except Exception:
            pass

        # Render background after initial layout
        self._render_background()

        # Start accent pulse animation
        self._animate_accents()

        # Start title pulse animation (very visible)
        self._animate_title()

        # Robust card hover tracking
        self._init_card_hover_tracking()

        # Global wheel scroll routing
        self._init_global_scroll_routing()

    def _side_panel_parent(self):
        """Return the correct parent for side panel content."""
        return getattr(self, 'side_panel_inner', self.side_panel)

    def _render_background(self):
        """Draw a themed background with soft gradients and glows."""
        if not hasattr(self, 'bg_canvas'):
            return

        width = self.root.winfo_width() or 1280
        height = self.root.winfo_height() or 760
        if (width, height) == self._bg_size and self._bg_particles:
            return

        self._bg_size = (width, height)
        self.bg_canvas.delete('all')

        self._bg_particles = []
        self._bg_nebulas = []

        # Vertical gradient
        steps = 60
        for i in range(steps):
            t = i / max(1, steps - 1)
            if t < 0.5:
                start = self.colors["bg_top"]
                end = self.colors["bg_mid"]
                tt = t / 0.5
            else:
                start = self.colors["bg_mid"]
                end = self.colors["bg_bottom"]
                tt = (t - 0.5) / 0.5

            def _lerp(a, b, tval):
                return int(a + (b - a) * tval)

            sr = int(start[1:3], 16)
            sg = int(start[3:5], 16)
            sb = int(start[5:7], 16)
            er = int(end[1:3], 16)
            eg = int(end[3:5], 16)
            eb = int(end[5:7], 16)
            rr = _lerp(sr, er, tt)
            rg = _lerp(sg, eg, tt)
            rb = _lerp(sb, eb, tt)
            color = f"#{rr:02x}{rg:02x}{rb:02x}"

            y0 = int((height / steps) * i)
            y1 = int((height / steps) * (i + 1))
            self.bg_canvas.create_rectangle(0, y0, width, y1, fill=color, outline="")

        # Soft glow shapes
        # (Store IDs so we can drift them subtly for obvious motion.)
        n1 = self.bg_canvas.create_oval(
            -width * 0.25, -height * 0.35, width * 0.85, height * 0.65,
            outline="", fill=self.colors["glow_blue"],
        )
        n2 = self.bg_canvas.create_oval(
            width * 0.30, -height * 0.15, width * 1.20, height * 0.75,
            outline="", fill=self.colors["glow_teal"],
        )
        n3 = self.bg_canvas.create_oval(
            -width * 0.15, height * 0.35, width * 0.75, height * 1.20,
            outline="", fill="#0f1b2a",
        )
        self._bg_nebulas = [
            {"id": n1, "dx": 0.05, "dy": 0.02, "wrap": 80},
            {"id": n2, "dx": -0.03, "dy": 0.03, "wrap": 80},
            {"id": n3, "dx": 0.02, "dy": -0.02, "wrap": 80},
        ]

        self._init_background_particles(width, height)
        if not self._bg_animating:
            self._bg_animating = True
            self._animate_background()

        if self._accent_bars:
            self._animate_accents()

    def _init_background_particles(self, width, height):
        """Initialize drifting particles for subtle motion."""
        self._bg_particles = []
        # Make it denser so motion is unmistakable even in small windows.
        count = max(60, (width * height) // 18000)
        rng = random.Random(21)

        for _ in range(count):
            x = rng.randint(0, width)
            y = rng.randint(0, height)
            r = rng.choice([1, 1, 2, 2, 3])
            color = self.colors["particle"] if rng.random() > 0.55 else self.colors["particle_dim"]
            drift_x = rng.uniform(-0.35, 0.55)
            drift_y = rng.uniform(0.15, 0.80)
            tw_phase = rng.uniform(0.0, math.tau)
            tw_speed = rng.uniform(0.06, 0.14)
            pid = self.bg_canvas.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")
            self._bg_particles.append({
                "id": pid,
                "x": x,
                "y": y,
                "r": r,
                "dx": drift_x,
                "dy": drift_y,
                "tw": tw_phase,
                "tw_speed": tw_speed,
            })

    def _animate_background(self):
        """Animate background particles with gentle drift."""
        if not hasattr(self, 'bg_canvas'):
            self._bg_animating = False
            return

        width = self.root.winfo_width() or 1280
        height = self.root.winfo_height() or 760

        # Drift the big glows (nebula) very subtly.
        for neb in self._bg_nebulas:
            try:
                self.bg_canvas.move(neb["id"], neb["dx"], neb["dy"])
                x0, y0, x1, y1 = self.bg_canvas.coords(neb["id"])
                wrap = neb.get("wrap", 80)
                if x1 < -wrap:
                    self.bg_canvas.move(neb["id"], width + wrap * 2, 0)
                elif x0 > width + wrap:
                    self.bg_canvas.move(neb["id"], -(width + wrap * 2), 0)
                if y1 < -wrap:
                    self.bg_canvas.move(neb["id"], 0, height + wrap * 2)
                elif y0 > height + wrap:
                    self.bg_canvas.move(neb["id"], 0, -(height + wrap * 2))
            except Exception:
                pass

        for particle in self._bg_particles:
            particle["x"] += particle["dx"]
            particle["y"] += particle["dy"]

            # Twinkle (alternate between dim and bright)
            particle["tw"] = (particle["tw"] + particle["tw_speed"]) % math.tau
            tw = (math.sin(particle["tw"]) + 1.0) / 2.0
            color = self.colors["particle"] if tw > 0.55 else self.colors["particle_dim"]
            try:
                self.bg_canvas.itemconfig(particle["id"], fill=color)
            except Exception:
                pass

            if particle["x"] > width + 10:
                particle["x"] = -10
            if particle["y"] > height + 10:
                particle["y"] = -10

            r = particle["r"]
            self.bg_canvas.coords(
                particle["id"],
                particle["x"] - r,
                particle["y"] - r,
                particle["x"] + r,
                particle["y"] + r,
            )

        self.root.after(60, self._animate_background)

    def _animate_title(self):
        """Pulse the main title color so motion is always visible."""
        if not self._title_label:
            return

        self._title_phase = (self._title_phase + 1) % 120
        t = abs(60 - self._title_phase) / 60.0

        def _lerp_color(a, b, tval):
            ar = int(a[1:3], 16)
            ag = int(a[3:5], 16)
            ab = int(a[5:7], 16)
            br = int(b[1:3], 16)
            bg = int(b[3:5], 16)
            bb = int(b[5:7], 16)
            rr = int(ar + (br - ar) * tval)
            rg = int(ag + (bg - ag) * tval)
            rb = int(ab + (bb - ab) * tval)
            return f"#{rr:02x}{rg:02x}{rb:02x}"

        color = _lerp_color(self.colors["accent"], self.colors["accent_hover"], t)
        try:
            self._title_label.config(fg=color)
        except Exception:
            pass

        self.root.after(80, self._animate_title)

    def _register_accent_bar(self, bar):
        """Register an accent bar for pulsing animation."""
        if bar not in self._accent_bars:
            self._accent_bars.append(bar)

    def _animate_accents(self):
        """Pulse accent bars between accent and hover colors."""
        if not self._accent_bars:
            return

        self._accent_phase = (self._accent_phase + 1) % 120
        t = abs(60 - self._accent_phase) / 60.0

        def _lerp_color(a, b, tval):
            ar = int(a[1:3], 16)
            ag = int(a[3:5], 16)
            ab = int(a[5:7], 16)
            br = int(b[1:3], 16)
            bg = int(b[3:5], 16)
            bb = int(b[5:7], 16)
            rr = int(ar + (br - ar) * tval)
            rg = int(ag + (bg - ag) * tval)
            rb = int(ab + (bb - ab) * tval)
            return f"#{rr:02x}{rg:02x}{rb:02x}"

        color = _lerp_color(self.colors["accent"], self.colors["accent_hover"], t)
        for bar in self._accent_bars:
            try:
                # If a bar belongs to a search-highlighted card, don't override the highlight.
                owner = getattr(bar, '_owner_card', None)
                if owner is not None and getattr(owner, '_search_highlight', False):
                    continue
                bar.config(bg=color)
            except Exception:
                pass

        self.root.after(80, self._animate_accents)
    
    def create_scrollable_account_section(self, parent):
        """Create scrollable container for account boxes"""
        # Container frame
        container = tk.Frame(parent, bg=self.colors["bg"])
        container.pack(fill='both', expand=True, pady=(0, 15))
        
        # Canvas for scrolling
        # Give the scroll area a subtle outline without creating a heavy solid panel.
        self.accounts_canvas = tk.Canvas(
            container,
            bg=self.colors["bg"],
            highlightthickness=1,
            highlightbackground=self.colors["stroke"],
        )
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=self.accounts_canvas.yview, style='Cos.Vertical.TScrollbar')
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

        # Register for mouse-wheel routing
        self._register_scroll_canvas(self.accounts_canvas)
        
        # Bind canvas resize
        self.accounts_frame.bind('<Configure>', lambda e: self.accounts_canvas.configure(scrollregion=self.accounts_canvas.bbox('all')))
        self.accounts_canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Mouse wheel scrolling is handled by global routing.
    
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
            # Use a bit more spacing so the background breathes.
            # Keep cards from stretching vertically by default.
            box.grid(row=row, column=col, padx=12, pady=10, sticky='ew')

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

        # Debounce background redraw; <Configure> can fire a lot while resizing.
        try:
            if self._bg_render_job is not None:
                self.root.after_cancel(self._bg_render_job)
        except Exception:
            pass
        self._bg_render_job = self.root.after(120, self._render_background)
    
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
        """Show the side panel by animating its width."""
        computed_width = self._compute_side_panel_width(min_width=width)

        self._cancel_side_panel_animation()

        if not self.side_panel_visible:
            # Add padding so the animated background remains visible around the drawer.
            self.side_panel.pack(side='right', fill='y', padx=(0, 14), pady=14)
            self.side_panel.pack_propagate(False)
            self.side_panel.config(width=0)
            self.side_panel_visible = True

        self._animate_side_panel_width(to_width=computed_width)
    
    def hide_side_panel(self):
        """Hide the side panel with a slide-out animation."""
        if not self.side_panel_visible:
            return

        self._cancel_side_panel_animation()

        # Clear panel content immediately to avoid stacking UIs when switching views.
        try:
            parent = self._side_panel_parent()
            for widget in parent.winfo_children():
                widget.destroy()
        except Exception:
            pass

        self._animate_side_panel_width(to_width=0, on_done=self._finish_hide_side_panel)

    def _finish_hide_side_panel(self):
        try:
            self.side_panel.pack_forget()
        except Exception:
            pass
        self.side_panel_visible = False

    def _cancel_side_panel_animation(self):
        try:
            if self._side_panel_anim_job is not None:
                self.root.after_cancel(self._side_panel_anim_job)
        except Exception:
            pass
        self._side_panel_anim_job = None
        self._side_panel_animating = False

    def _animate_side_panel_width(self, to_width: int, on_done=None):
        """Animate side panel width to target."""
        self._side_panel_animating = True

        try:
            from_width = int(self.side_panel.cget('width') or 0)
        except Exception:
            try:
                from_width = int(self.side_panel.winfo_width() or 0)
            except Exception:
                from_width = 0

        to_width = int(max(0, to_width))
        if from_width == to_width:
            self._side_panel_animating = False
            if callable(on_done):
                on_done()
            return

        steps = 14
        duration_ms = 180
        step_ms = max(10, duration_ms // steps)
        delta = (to_width - from_width) / float(steps)

        def tick(i: int, w: float):
            try:
                self.side_panel.config(width=int(round(w)))
            except Exception:
                pass

            if i >= steps:
                try:
                    self.side_panel.config(width=to_width)
                except Exception:
                    pass
                self._side_panel_anim_job = None
                self._side_panel_animating = False
                if callable(on_done):
                    on_done()
                return

            self._side_panel_anim_job = self.root.after(step_ms, lambda: tick(i + 1, w + delta))

        tick(0, float(from_width))
    
    
    def create_account_box(self, parent):
        """Create a single account display box"""
        box_frame = tk.Frame(
            parent,
            bg=self.colors["input"],
            relief='flat',
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.colors["stroke"],
            cursor='hand2'
        )

        box_bar = tk.Frame(box_frame, bg=self.colors["accent"], height=4)
        box_bar.pack(fill='x', side='top')
        self._register_accent_bar(box_bar)
        
        # Make box clickable to open details
        box_frame.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        # Inner frame for padding
        inner = tk.Frame(box_frame, bg=self.colors["input"], cursor='hand2')
        inner.pack(fill='both', expand=True, padx=14, pady=12)
        inner.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        # Top row: username + creature badge
        header_row = tk.Frame(inner, bg=self.colors["input"], cursor='hand2')
        header_row.pack(fill='x', pady=(0, 8))
        header_row.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        username_label = tk.Label(header_row, text="Account Name", bg=self.colors["input"], fg=self.colors["text"],
                     font=('Segoe UI', 12, 'bold'), cursor='hand2')
        username_label.pack(side='left')
        username_label.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        creature_count_label = tk.Label(
            header_row,
            text="0 creatures",
            bg=self.colors["panel_alt"],
            fg=self.colors["muted"],
            font=('Segoe UI', 9, 'bold'),
            cursor='hand2',
            padx=10,
            pady=4,
        )
        creature_count_label.pack(side='right')
        creature_count_label.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        # Status pill
        status_pill = tk.Frame(
            inner,
            bg=self.colors["panel_alt"],
            highlightthickness=1,
            highlightbackground=self.colors["stroke"],
            cursor='hand2',
        )
        status_pill.pack(anchor='w', pady=(0, 10))
        status_pill.bind('<Button-1>', lambda e: self.show_account_details(box_frame))

        status_dot = tk.Label(
            status_pill,
            text="●",
            bg=self.colors["panel_alt"],
            fg=self.colors["muted"],
            font=('Segoe UI', 12),
            cursor='hand2',
            padx=8,
            pady=3,
        )
        status_dot.pack(side='left')
        status_dot.bind('<Button-1>', lambda e: self.show_account_details(box_frame))

        status_label = tk.Label(
            status_pill,
            text="Offline",
            bg=self.colors["panel_alt"],
            fg=self.colors["muted"],
            font=('Segoe UI', 9, 'bold'),
            cursor='hand2',
            padx=2,
            pady=3,
        )
        status_label.pack(side='left', padx=(0, 10))
        status_label.bind('<Button-1>', lambda e: self.show_account_details(box_frame))
        
        # Buttons frame
        btn_frame = tk.Frame(inner, bg=self.colors["input"])
        btn_frame.pack(fill='x')
        
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
        box_frame.status_pill = status_pill
        box_frame.launch_btn = launch_btn
        box_frame.stop_btn = stop_btn
        box_frame.box_bar = box_bar
        # Let accent animation know which card owns the bar.
        try:
            box_bar._owner_card = box_frame
        except Exception:
            pass
        box_frame.account = None

        # Search highlight state
        box_frame._search_highlight = False
        box_frame._search_anim_job = None
        box_frame._search_sweep = None
        box_frame._search_border_color = self.colors["stroke"]

        # Mark as an account card so hover tracking can find it.
        box_frame._is_account_card = True

        # Hover animation plumbing
        box_frame._hover_job = None
        box_frame._hover_t = 0.0
        box_frame._hover_targets = [
            box_frame,
            inner,
            header_row,
            username_label,
            creature_count_label,
            status_pill,
            status_dot,
            status_label,
            btn_frame,
            launch_btn,
            stop_btn,
        ]
        
        return box_frame

    def _init_card_hover_tracking(self):
        """Track which account card is under the mouse and animate hover reliably."""
        if self._hover_tracking_enabled:
            return
        self._hover_tracking_enabled = True

        def find_card(widget):
            try:
                while widget is not None:
                    if getattr(widget, '_is_account_card', False):
                        return widget
                    parent_name = widget.winfo_parent()
                    if not parent_name:
                        break
                    widget = widget.nametowidget(parent_name)
            except Exception:
                return None
            return None

        def clear_hover():
            if self._hovered_card is not None:
                self._animate_card_hover(self._hovered_card, entering=False)
                self._hovered_card = None

        def on_motion(event):
            try:
                w = self.root.winfo_containing(event.x_root, event.y_root)
            except Exception:
                w = None
            card = find_card(w) if w is not None else None
            if card is self._hovered_card:
                return

            # Swap hovered card
            if self._hovered_card is not None:
                self._animate_card_hover(self._hovered_card, entering=False)
            self._hovered_card = card
            if self._hovered_card is not None:
                self._animate_card_hover(self._hovered_card, entering=True)

        # Bind to root motion; this is resilient to missed enter/leave events.
        self.root.bind('<Motion>', on_motion, add=True)
        self.root.bind('<Leave>', lambda _e: clear_hover(), add=True)

    def _animate_card_hover(self, box_frame, entering: bool):
        """Smoothly fade card background + border on hover."""
        try:
            if box_frame._hover_job is not None:
                self.root.after_cancel(box_frame._hover_job)
        except Exception:
            pass

        start = float(getattr(box_frame, '_hover_t', 0.0))
        end = 1.0 if entering else 0.0
        steps = 8
        dt = (end - start) / max(1, steps)

        def _lerp_color(a, b, tval):
            ar = int(a[1:3], 16)
            ag = int(a[3:5], 16)
            ab = int(a[5:7], 16)
            br = int(b[1:3], 16)
            bg = int(b[3:5], 16)
            bb = int(b[5:7], 16)
            rr = int(ar + (br - ar) * tval)
            rg = int(ag + (bg - ag) * tval)
            rb = int(ab + (bb - ab) * tval)
            return f"#{rr:02x}{rg:02x}{rb:02x}"

        base_bg = self.colors["input"]
        hover_bg = self.colors["panel_alt"]
        if getattr(box_frame, '_search_highlight', False):
            base_border = getattr(box_frame, '_search_border_color', self.colors["warning"])
            hover_border = base_border
        else:
            base_border = self.colors["stroke"]
            hover_border = self.colors["accent"]

        def tick(i: int, t: float):
            box_frame._hover_t = t
            card_bg = _lerp_color(base_bg, hover_bg, t)
            border = _lerp_color(base_border, hover_border, t)

            try:
                box_frame.config(bg=card_bg, highlightbackground=border)
            except Exception:
                pass

            # If this card is search-highlighted, keep its top bar yellow.
            try:
                if getattr(box_frame, '_search_highlight', False) and hasattr(box_frame, 'box_bar'):
                    box_frame.box_bar.config(bg=self.colors["warning"])
            except Exception:
                pass

            for w in getattr(box_frame, '_hover_targets', []):
                try:
                    # Never override action button colors.
                    if isinstance(w, tk.Button) and (w == box_frame.launch_btn or w == box_frame.stop_btn):
                        continue
                    if isinstance(w, tk.Label) and w == box_frame.creature_count_label:
                        continue
                    if w == box_frame.status_pill or w == box_frame.status_dot or w == box_frame.status_label:
                        continue
                    w.config(bg=card_bg)
                except Exception:
                    pass

            try:
                badge_bg = _lerp_color(self.colors["panel_alt"], self.colors["input"], t)
                box_frame.creature_count_label.config(bg=badge_bg)
            except Exception:
                pass

            if i >= steps:
                box_frame._hover_job = None
                return

            box_frame._hover_job = self.root.after(18, lambda: tick(i + 1, max(0.0, min(1.0, t + dt))))

        tick(0, start)
    
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
                try:
                    box.status_pill.config(bg=self.colors["panel_alt"], highlightbackground=self.colors["stroke"])
                    box.status_dot.config(bg=self.colors["panel_alt"])
                    box.status_label.config(bg=self.colors["panel_alt"])
                except Exception:
                    pass
                
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
                try:
                    box.status_pill.config(bg=self.colors["panel_alt"], highlightbackground=self.colors["stroke"])
                    box.status_dot.config(bg=self.colors["panel_alt"])
                    box.status_label.config(bg=self.colors["panel_alt"])
                except Exception:
                    pass
                box.launch_btn.config(state='disabled')
                box.stop_btn.config(state='disabled')
                box.grid()

        # Ensure search highlights remain consistent after refresh.
        try:
            self._apply_search_highlights(getattr(self, '_last_search_matches', set()))
        except Exception:
            pass

    def _clear_search_highlights(self):
        self._last_search_matches = set()
        for box in getattr(self, 'account_boxes', {}).values():
            try:
                box._search_highlight = False
                self._stop_search_highlight_animation(box)
                box.config(highlightthickness=1, highlightbackground=self.colors["stroke"])
                if hasattr(box, 'box_bar'):
                    box.box_bar.config(bg=self.colors["accent"])
            except Exception:
                pass

    def _apply_search_highlights(self, matched_usernames: set[str]):
        self._last_search_matches = set(matched_usernames or set())
        for box in getattr(self, 'account_boxes', {}).values():
            try:
                acct = getattr(box, 'account', None)
                if not acct or not getattr(acct, 'username', None):
                    box._search_highlight = False
                    self._stop_search_highlight_animation(box)
                    box.config(highlightthickness=1, highlightbackground=self.colors["stroke"])
                    if hasattr(box, 'box_bar'):
                        box.box_bar.config(bg=self.colors["accent"])
                    continue

                if acct.username in self._last_search_matches:
                    box._search_highlight = True
                    box.config(highlightthickness=2)
                    self._start_search_highlight_animation(box)
                    if hasattr(box, 'box_bar'):
                        box.box_bar.config(bg=self.colors["warning"])
                else:
                    box._search_highlight = False
                    self._stop_search_highlight_animation(box)
                    box.config(highlightthickness=1, highlightbackground=self.colors["stroke"])
                    if hasattr(box, 'box_bar'):
                        box.box_bar.config(bg=self.colors["accent"])
            except Exception:
                continue

    def _start_search_highlight_animation(self, box_frame):
        """Animate a stronger, more noticeable search highlight (pulse + sweep)."""
        if box_frame is None:
            return
        if not getattr(box_frame, '_search_highlight', False):
            return

        # Ensure sweep element exists
        try:
            if getattr(box_frame, '_search_sweep', None) is None and hasattr(box_frame, 'box_bar'):
                sweep = tk.Frame(box_frame.box_bar, bg=self.colors["text"], height=4)
                sweep.place(x=0, y=0, width=44, height=4)
                box_frame._search_sweep = sweep
        except Exception:
            box_frame._search_sweep = None

        # Cancel previous animation job
        try:
            if getattr(box_frame, '_search_anim_job', None) is not None:
                self.root.after_cancel(box_frame._search_anim_job)
        except Exception:
            pass
        box_frame._search_anim_job = None

        def _lerp_color(a, b, tval):
            ar = int(a[1:3], 16)
            ag = int(a[3:5], 16)
            ab = int(a[5:7], 16)
            br = int(b[1:3], 16)
            bg = int(b[3:5], 16)
            bb = int(b[5:7], 16)
            rr = int(ar + (br - ar) * tval)
            rg = int(ag + (bg - ag) * tval)
            rb = int(ab + (bb - ab) * tval)
            return f"#{rr:02x}{rg:02x}{rb:02x}"

        def tick():
            if not getattr(box_frame, '_search_highlight', False):
                box_frame._search_anim_job = None
                return

            self._search_phase = (self._search_phase + 1) % 120
            tt = abs(60 - self._search_phase) / 60.0

            # Pulse between warning and text (brighter) for better visibility.
            border = _lerp_color(self.colors["warning"], self.colors["text"], 0.35 * (1.0 - tt))
            box_frame._search_border_color = border
            try:
                box_frame.config(highlightbackground=border)
            except Exception:
                pass

            # Keep the top bar locked to yellow (avoid fighting accent pulse)
            try:
                if hasattr(box_frame, 'box_bar'):
                    box_frame.box_bar.config(bg=self.colors["warning"])
            except Exception:
                pass

            # Sweep effect across the top bar
            try:
                sweep = getattr(box_frame, '_search_sweep', None)
                if sweep is not None and hasattr(box_frame, 'box_bar'):
                    bw = int(box_frame.box_bar.winfo_width() or 0)
                    if bw > 0:
                        speed = max(6, bw // 60)
                        x = int(getattr(box_frame, '_search_sweep_x', 0)) + speed
                        if x > bw + 44:
                            x = -44
                        box_frame._search_sweep_x = x
                        sweep.place(x=x, y=0, width=44, height=4)
                        sweep.config(bg=_lerp_color(self.colors["text"], self.colors["warning"], 0.5 + 0.5 * (1.0 - tt)))
            except Exception:
                pass

            box_frame._search_anim_job = self.root.after(40, tick)

        tick()

    def _stop_search_highlight_animation(self, box_frame):
        if box_frame is None:
            return

        try:
            if getattr(box_frame, '_search_anim_job', None) is not None:
                self.root.after_cancel(box_frame._search_anim_job)
        except Exception:
            pass
        box_frame._search_anim_job = None
        box_frame._search_border_color = self.colors["stroke"]
        try:
            if getattr(box_frame, '_search_sweep', None) is not None:
                box_frame._search_sweep.destroy()
        except Exception:
            pass
        box_frame._search_sweep = None
        try:
            if hasattr(box_frame, 'box_bar'):
                box_frame.box_bar.config(bg=self.colors["accent"])
        except Exception:
            pass


    
    def create_control_panel(self, parent):
        """Create bottom control panel"""
        control_frame = tk.Frame(parent, bg=self.colors["panel_alt"], relief='flat', highlightthickness=1, highlightbackground=self.colors["stroke"])
        control_frame.pack(fill='x', pady=(0, 10))
        control_bar = tk.Frame(control_frame, bg=self.colors["accent"], height=4)
        control_bar.pack(fill='x', side='top')
        self._register_accent_bar(control_bar)
        
        inner = tk.Frame(control_frame, bg=self.colors["panel_alt"])
        inner.pack(fill='x', padx=18, pady=16)
        
        # Left section: Add/Remove account
        left_section = tk.Frame(inner, bg=self.colors["panel_alt"])
        left_section.pack(side='left', fill='x', expand=True)
        
        tk.Label(left_section, text="Account Management", bg=self.colors["panel_alt"], fg=self.colors["accent"],
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
        right_section = tk.Frame(inner, bg=self.colors["panel_alt"])
        right_section.pack(side='right')

        tk.Label(right_section, text="Join Username:", bg=self.colors["panel_alt"], fg=self.colors["text"],
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

        tk.Label(right_section, text="Search Creature:", bg=self.colors["panel_alt"], fg=self.colors["text"],
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
                bg=self.colors["panel_alt"], fg=self.colors["text"], font=('Segoe UI', 10, 'bold'),
                relief='flat', padx=12, pady=10, cursor='hand2')
        update_btn.pack(side='left')
        
        
    
    def show_add_account(self):
        """Show add account in side panel"""
        self.hide_side_panel()
        self.show_side_panel(width=400)

        parent = self._side_panel_parent()
        
        # Header with close button
        header = tk.Frame(parent, bg=self.colors["panel_alt"], height=60)
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
        frame = tk.Frame(parent, bg=self.colors["panel_alt"])
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(frame, text="Username:", bg=self.colors["panel_alt"], fg=self.colors["text"],
                font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 5))
        username_entry = tk.Entry(frame, bg=self.colors["input"], fg=self.colors["text"], font=('Segoe UI', 10),
                     relief='flat', insertbackground=self.colors["text"])
        username_entry.pack(fill='x', pady=(0, 15), ipady=8)
        username_entry.focus_set()
        
        tk.Label(frame, text="Password:", bg=self.colors["panel_alt"], fg=self.colors["text"],
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

        parent = self._side_panel_parent()
        
        # Header with close button
        header = tk.Frame(parent, bg=self.colors["panel_alt"], height=60)
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
        frame = tk.Frame(parent, bg=self.colors["panel_alt"])
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(frame, text="Select account to remove:", bg=self.colors["panel_alt"], fg=self.colors["text"],
            font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 15))
        
        selected = tk.StringVar()
        
        for account in accounts:
            rb = tk.Radiobutton(frame, text=account.username, variable=selected, value=account.username,
                               bg=self.colors["panel_alt"], fg=self.colors["text"], selectcolor=self.colors["panel_alt"],
                               activebackground=self.colors["panel_alt"], activeforeground=self.colors["accent"],
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

        parent = self._side_panel_parent()

        # Header with close button
        header = tk.Frame(parent, bg=self.colors["panel_alt"], height=60)
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
        scroll_container = tk.Frame(parent, bg=self.colors["panel_alt"])
        scroll_container.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(scroll_container, bg=self.colors["panel_alt"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient='vertical', command=canvas.yview, style='Cos.Vertical.TScrollbar')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        content_frame = tk.Frame(canvas, bg=self.colors["panel_alt"])
        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor='nw')
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Register for mouse-wheel routing
        self._register_scroll_canvas(canvas)
        
        content_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width-20))
        
        # Mouse wheel scrolling is handled by global routing.

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

        parent = self._side_panel_parent()
        
        # Header with close button
        header = tk.Frame(parent, bg=self.colors["panel_alt"], height=60)
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
        log_frame = tk.Frame(parent, bg=self.colors["panel_alt"])
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Action buttons
        action_frame = tk.Frame(log_frame, bg=self.colors["panel_alt"])
        action_frame.pack(fill='x', pady=(0, 10))
        
        log_text = scrolledtext.ScrolledText(log_frame, bg=self.colors["input"], fg=self.colors["text"],
                             font=('Consolas', 9), relief='flat',
                             insertbackground=self.colors["text"], selectbackground=self.colors["panel_alt"])
        log_text.vbar.config(bg=self.colors["panel_alt"], troughcolor=self.colors["bg"], activebackground=self.colors["accent"])
        
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
        """Search for creature name across all accounts and highlight matching account cards."""
        try:
            query = (self.search_var.get() or "").strip().lower()
            if not query:
                self._clear_search_highlights()
                return

            matched_usernames: set[str] = set()
            accounts = self.account_manager.get_all_accounts()
            for account in accounts:
                if not hasattr(account, 'creatures'):
                    continue
                for idx, creature in enumerate(account.creatures or []):
                    if not creature or not isinstance(creature, dict):
                        continue
                    name = (creature.get('name') or "").strip()
                    if name and query in name.lower():
                        matched_usernames.add(account.username)
                        break

            self._apply_search_highlights(matched_usernames)
        except Exception as e:
            try:
                GameLauncher.add_session_log(f"[search] error: {e}")
            except Exception:
                pass
            messagebox.showerror("Search", f"Search failed: {e}")
            return
    
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

        parent = self._side_panel_parent()
        
        # Header with close button
        header = tk.Frame(parent, bg=self.colors["panel_alt"], height=60)
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
        container = tk.Frame(parent, bg=self.colors["panel_alt"])
        container.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(container, bg=self.colors["panel_alt"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview, style='Cos.Vertical.TScrollbar')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        creatures_frame = tk.Frame(canvas, bg=self.colors["panel_alt"])
        canvas_window = canvas.create_window((0, 0), window=creatures_frame, anchor='nw')
        
        canvas.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        scrollbar.pack(side='right', fill='y')

        # Register for mouse-wheel routing
        self._register_scroll_canvas(canvas)
        
        creatures_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width-20))
        
        # Mouse wheel scrolling is handled by global routing.
        
        # Create 17 creature slot entries
        for i in range(17):
            self.create_creature_slot(creatures_frame, account, i)
        
        # Save button at bottom
        btn_frame = tk.Frame(parent, bg=self.colors["panel_alt"])
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

