import subprocess
import threading
import time
import os
import sys
import logging
import ctypes
import psutil
from typing import Callable
from ctypes import wintypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from account_manager import Account
from window_controller import WindowController

# Custom handler to store logs in memory for current session
class SessionLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs = []
    
    def emit(self, record):
        log_entry = self.format(record)
        self.logs.append(log_entry)
    
    def get_logs(self):
        return self.logs.copy()
    
    def clear(self):
        self.logs.clear()

# Create session log handler
session_handler = SessionLogHandler()
session_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[session_handler]
)

# Mutex handling to allow multiple Roblox instances
# 
# CRITICAL: Roblox natively prevents multiple instances from running simultaneously
# by acquiring an exclusive lock on the mutex "ROBLOX_singletonEvent". 
# 
# Solution: We create the mutex FIRST (before Roblox tries to create it), 
# and hold the handle open WITHOUT acquiring ownership. This prevents Roblox 
# from being able to acquire exclusive ownership.
#
# IMPORTANT NOTES:
# - The handle MUST be held open for the entire lifetime of the application
# - If the handle is closed, Roblox will immediately lock it and prevent new instances
# - The mutex is created with bInitialOwner=False, so we don't own it exclusively
# - Each RobloxPlayer.exe tries to create the same mutex and fails (already exists)
# - Since we don't own it exclusively, all instances can coexist
#
# DO NOT:
# - Close the handle after creation
# - Release the mutex during runtime
# - Change CreateMutexW parameters (bInitialOwner must be False)
#
class MutexManager:
    def __init__(self):
        # Hold ALL created handles for the entire app lifetime.
        # If handles are closed, Roblox can immediately re-create/lock its singleton objects.
        self.mutex_handles = []
    
    def create_roblox_mutex(self):
        """
        Create Roblox singleton guard objects and HOLD THEM OPEN to allow multiple instances.
        
        This must be called BEFORE any RobloxPlayer.exe process is launched.
        The handles are kept in memory for the entire app lifetime.
        
        Returns: True if successful, False otherwise
        """
        try:
            # Use WinDLL + last-error so we can debug failures reliably.
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE

            # Roblox has historically used a named object like "ROBLOX_singletonEvent".
            # Roblox can also change/add additional singleton object names over time.
            # We defensively create and hold several likely names (and Global/Local variants).
            candidate_names = [
                "ROBLOX_singletonEvent",
                "ROBLOX_singletonMutex",
                "RobloxPlayerSingletonMutex",
                "RobloxPlayerLauncherMutex",
            ]

            prefixes = ["", "Global\\", "Local\\"]
            created_any = False

            for base_name in candidate_names:
                for prefix in prefixes:
                    name = f"{prefix}{base_name}"
                    handle = kernel32.CreateMutexW(None, False, name)
                    last_err = ctypes.get_last_error()
                    if handle:
                        self.mutex_handles.append(handle)
                        created_any = True
                        logging.info(f"✓ Singleton guard HELD: {name} (last_error={last_err})")
                    else:
                        logging.warning(f"✗ Failed to create singleton guard: {name} (last_error={last_err})")

            return created_any
        except Exception as e:
            logging.error(f"Failed to create mutex: {e}")
        return False
    
    def release_all(self):
        """
        Release mutex handles on application shutdown.
        WARNING: This only happens on app exit, NOT during runtime!
        """
        try:
            if self.mutex_handles:
                kernel32 = ctypes.windll.kernel32
                for handle in self.mutex_handles:
                    try:
                        kernel32.CloseHandle(handle)
                    except:
                        pass
                self.mutex_handles = []
                logging.info("Mutex handles released on shutdown")
        except:
            pass

class GameLauncher:
    def __init__(self, game_url: str, status_callback: Callable = None):
        self.game_url = game_url
        self.drivers = {}  # username -> webdriver
        self.status_callback = status_callback
        self.launch_threads = {}
        self.mutex_manager = MutexManager()
        self.player_pids = {}  # username -> set of RobloxPlayer PIDs started by us
        self.window_controller = WindowController()  # Window input controller
        
        # CRITICAL: Create mutex BEFORE any RobloxPlayer.exe process starts
        # This MUST happen in __init__ (before any launch_game calls)
        # If this is delayed or skipped, Roblox will lock the mutex and prevent multiple instances
        self.mutex_manager.create_roblox_mutex()
        logging.info("✓ Roblox mutex created - multiple instances enabled")
    
    @staticmethod
    def get_session_logs():
        """Get logs from current session"""
        return session_handler.get_logs()
    
    def status_update(self, username: str, status: str):
        """Send status update to GUI"""
        if self.status_callback:
            self.status_callback(username, status)
    
    def launch_game(self, account: Account):
        """Launch game for a specific account in a background thread"""
        thread = threading.Thread(target=self._launch_game_thread, args=(account,))
        thread.daemon = False  # Must be non-daemon to keep browsers/Roblox processes alive
        thread.start()
        self.launch_threads[account.username] = thread
    
    def _launch_game_thread(self, account: Account):
        """Background thread for launching game"""
        try:
            logging.info(f"Starting launch for account: {account.username}")
            self.status_update(account.username, "launching")
            
            # Setup Chrome options for multiple instances
            options = webdriver.ChromeOptions()
            
            # Create profile directory in user's temp folder
            if getattr(sys, 'frozen', False):
                # Running as compiled EXE
                base_dir = os.path.join(os.environ.get('TEMP', '.'), 'RobloxBotProfiles')
            else:
                # Running as script
                base_dir = './chrome_profiles'
            
            profile_dir = os.path.join(base_dir, account.username)
            os.makedirs(profile_dir, exist_ok=True)
            
            options.add_argument(f"--user-data-dir={profile_dir}")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--start-minimized")  # Open browsers in background without focus
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            # Try to find Chrome in system
            driver = webdriver.Chrome(options=options)
            self.drivers[account.username] = driver
            
            # Check if already logged in by going to Roblox home
            logging.info(f"{account.username}: Checking if already logged in...")
            driver.get("https://www.roblox.com/home")
            time.sleep(3)
            
            # Check if we're actually logged in by looking for user profile elements
            is_logged_in = False
            try:
                # Try to find the user menu or profile icon (indicates logged in)
                driver.find_element(By.XPATH, "//li[@id='navbar-settings']")
                is_logged_in = True
                logging.info(f"{account.username}: Already logged in!")
            except:
                logging.info(f"{account.username}: Not logged in, will attempt login...")
            
            # If not logged in, do the login process
            if not is_logged_in:
                logging.info(f"{account.username}: Navigating to login page...")
                self.status_update(account.username, "logging in")
                
                # Go to login page
                driver.get("https://www.roblox.com/login")
                time.sleep(3)
                logging.info(f"{account.username}: On login page, searching for fields...")
                
                # Try multiple selectors for username field (Roblox changes their HTML)
                username_field = None
                try:
                    username_field = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "login-username"))
                    )
                except:
                    try:
                        username_field = driver.find_element(By.XPATH, "//input[@type='text' or @inputmode='text']")
                    except:
                        username_field = driver.find_element(By.XPATH, "//input[@placeholder='Username/Email/Phone']")
                
                if username_field:
                    logging.info(f"{account.username}: Found username field, filling...")
                    username_field.clear()
                    time.sleep(0.5)
                    username_field.send_keys(account.username)
                    time.sleep(0.5)
                else:
                    logging.error(f"{account.username}: Could not find username field!")
                
                # Fill in password - try multiple selectors
                password_field = None
                try:
                    password_field = driver.find_element(By.ID, "login-password")
                except:
                    try:
                        password_field = driver.find_element(By.XPATH, "//input[@type='password']")
                    except:
                        password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password']")
                
                if password_field:
                    logging.info(f"{account.username}: Found password field, filling...")
                    password_field.clear()
                    time.sleep(0.5)
                    password_field.send_keys(account.password)
                    time.sleep(0.5)
                else:
                    logging.error(f"{account.username}: Could not find password field!")
                
                # Click login button - try multiple selectors
                try:
                    login_btn = driver.find_element(By.ID, "login-button")
                    logging.info(f"{account.username}: Found login button, clicking...")
                    login_btn.click()
                except:
                    try:
                        login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")
                        logging.info(f"{account.username}: Found login button (XPath), clicking...")
                        login_btn.click()
                    except:
                        # Try submitting the form
                        logging.info(f"{account.username}: Submitting form instead...")
                        if password_field:
                            password_field.submit()
                
                # Wait for login to complete
                logging.info(f"{account.username}: Waiting for login to complete...")
                time.sleep(7)

            # Snapshot existing Roblox player PIDs before launch
            before_pids = set()
            try:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] and 'RobloxPlayer' in proc.info['name']:
                        before_pids.add(proc.pid)
            except Exception:
                pass
            
            # Navigate to game
            logging.info(f"{account.username}: Navigating to game: {self.game_url}")
            self.status_update(account.username, "joining game")
            driver.get(self.game_url)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(3)
            logging.info(f"{account.username}: Successfully online!")
            self.status_update(account.username, "online")
            
            # Wait for Roblox player to open then close browser
            time.sleep(5)

            # Capture new Roblox player processes started by this launch
            after_pids = set()
            try:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] and 'RobloxPlayer' in proc.info['name']:
                        after_pids.add(proc.pid)
            except Exception:
                pass

            new_pids = after_pids - before_pids
            self.player_pids[account.username] = new_pids
            logging.info(f"{account.username}: Tracked Roblox player PIDs: {list(new_pids)}")
            
            # Update window handles for input control (wait a bit for windows to initialize)
            time.sleep(2)
            handles = self.window_controller.update_window_handles(account.username, new_pids)
            logging.info(f"{account.username}: Tracked {len(handles)} window handles for input control")

            # Close the browser since Roblox player is now running
            logging.info(f"{account.username}: Closing browser, Roblox player will stay running...")
            driver.quit()
            if account.username in self.drivers:
                del self.drivers[account.username]
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"{account.username}: Error during launch: {error_msg}")
            if "chromedriver" in error_msg.lower() or "chrome" in error_msg.lower():
                self.status_update(account.username, "error: Chrome not found - Install Google Chrome")
            else:
                self.status_update(account.username, f"error: {error_msg[:50]}")
            
            if account.username in self.drivers:
                try:
                    self.drivers[account.username].quit()
                except:
                    pass
                del self.drivers[account.username]
    
    def stop_game(self, username: str):
        """Stop game for a specific account"""
        if username in self.drivers:
            try:
                self.drivers[username].quit()
                del self.drivers[username]
                self.status_update(username, "offline")
            except Exception as e:
                self.status_update(username, f"error stopping: {str(e)}")
        
        # Kill only the Roblox player processes we started for this user
        pids = self.player_pids.get(username, set())
        for pid in list(pids):
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    logging.info(f"Stopping Roblox player for {username}: PID {pid}")
                    proc.kill()
            except Exception:
                pass
        if username in self.player_pids:
            del self.player_pids[username]
        
        # Clear window handles for input control
        self.window_controller.clear_username(username)
    
    def launch_all_staggered(self, accounts):
        """Launch accounts with staggered delays between each start"""
        def staggered_launch_thread():
            for i, account in enumerate(accounts):
                account_type = "Main" if account.is_main else f"Sub {i}"
                logging.info(f"Launching {account_type} account: {account.username}")
                
                # Launch the account (this starts a thread, doesn't block)
                self.launch_game(account)
                
                # Small delay before launching next account (don't wait for completion)
                # This staggers the launch sequence so browsers don't all open at once
                wait_time = 3 if i == 0 else 5  # 3s for first, 5s between others
                logging.info(f"Stagger delay: {wait_time}s before launching next account...")
                time.sleep(wait_time)
            
            logging.info("All account launches initiated! (they may still be loading in background)")
        
        # Run in separate thread so GUI doesn't freeze
        thread = threading.Thread(target=staggered_launch_thread, daemon=False)
        thread.start()
    
    def stop_all_games(self):
        """Stop all running game instances and close only the Roblox players we started"""
        # Stop drivers first
        usernames = list(self.drivers.keys())
        for username in usernames:
            self.stop_game(username)
        
        # Stop any remaining tracked Roblox players (if driver was already removed)
        for username in list(self.player_pids.keys()):
            self.stop_game(username)
    
    def get_driver(self, username: str):
        """Get webdriver for a specific account"""
        return self.drivers.get(username)
