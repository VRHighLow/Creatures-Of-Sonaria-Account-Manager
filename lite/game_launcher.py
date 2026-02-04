import threading
import time
import logging
import ctypes
import psutil
import os
import sys
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from ctypes import wintypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from account_manager import Account

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


class MutexManager:
    def __init__(self):
        self.singleton_handles = []

    @staticmethod
    def list_roblox_player_processes() -> list[dict]:
        """Return a list of running Roblox player processes.

        Each entry: {pid, name, create_time}
        """
        procs: list[dict] = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    info = proc.info
                    name = info.get('name')
                    if not name:
                        continue
                    if 'RobloxPlayer' not in name and 'RobloxPlayerBeta' not in name:
                        continue
                    procs.append(
                        {
                            'pid': int(info['pid']),
                            'name': name,
                            'create_time': float(info.get('create_time') or 0.0),
                        }
                    )
                except Exception:
                    continue
        except Exception:
            pass

        procs.sort(key=lambda p: p.get('create_time', 0.0) or 0.0)
        return procs

    def close_singleton_events_in_player(
        self,
        target_pids: list[int] | None = None,
        *,
        stop_after_first: bool = True,
        scan_max_handle: int = 0x1000,
        repeat_seconds: float = 0.0,
        repeat_interval: float = 0.25,
    ) -> dict:
        """Close only the ROBLOX_singletonEvent handle in RobloxPlayer.

        Args:
            target_pids: If provided, only scan these PIDs.
            stop_after_first: Stop after closing the first matching handle.
            scan_max_handle: Upper bound for handle scan (exclusive).

        Returns:
            Dict with keys: attempted_pids, closed (list), errors (list)
        """
        try:
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            ntdll = ctypes.WinDLL('ntdll', use_last_error=True)
            
            result: dict = {'attempted_pids': [], 'closed': [], 'errors': [], 'passes': 0, 'closed_total': 0}

            if target_pids is None:
                procs = self.list_roblox_player_processes()
                roblox_pids = [p['pid'] for p in procs]
            else:
                roblox_pids = list(dict.fromkeys(int(pid) for pid in target_pids if pid))

            if not roblox_pids:
                logging.info("No RobloxPlayer processes found")
                return result

            logging.info(f"Found RobloxPlayer PIDs: {roblox_pids}")

            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.DuplicateHandle.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.DuplicateHandle.restype = wintypes.BOOL
            current_process = kernel32.GetCurrentProcess()

            ntdll.NtQueryObject.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
            ntdll.NtQueryObject.restype = wintypes.LONG

            class UNICODE_STRING(ctypes.Structure):
                _fields_ = [
                    ("Length", ctypes.c_ushort),
                    ("MaximumLength", ctypes.c_ushort),
                    ("Buffer", ctypes.c_void_p),
                ]

            PROCESS_DUP_HANDLE = 0x0040
            DUPLICATE_CLOSE_SOURCE = 0x00000001
            ObjectNameInformation = 1

            closed_count = 0
            hold_mode = bool(repeat_seconds and repeat_seconds > 0)
            if hold_mode:
                stop_after_first = False
                try:
                    repeat_seconds = float(repeat_seconds)
                except Exception:
                    repeat_seconds = 0.0

            start_time = time.time()
            passes = 0
            closed_total = 0
            last_attempted: list[int] = []

            while True:
                passes += 1
                result['passes'] = passes
                result['attempted_pids'] = []
                closed_this_pass = 0
            
                for pid in roblox_pids:
                    process_handle = None
                    try:
                        process_handle = kernel32.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
                        if not process_handle:
                            logging.info(f"Could not open RobloxPlayer process {pid}")
                            continue

                        result['attempted_pids'].append(pid)
                        last_attempted = result['attempted_pids']

                        # Scan a wider handle ID range to find the singleton event
                        logging.info(f"Scanning handles in PID {pid} (0x4 - 0x{scan_max_handle:x})...")
                        dup_success = 0
                        name_success = 0
                        roblox_found = 0
                        
                        for handle_id in range(0x4, int(scan_max_handle), 4):
                            remote_handle = wintypes.HANDLE(handle_id)
                            dup_handle = wintypes.HANDLE()

                            # Duplicate to our process to query it
                            if not kernel32.DuplicateHandle(process_handle, remote_handle, current_process, ctypes.byref(dup_handle), 0, False, 0):
                                continue

                            dup_success += 1

                            try:
                                # Query the handle name
                                name_len = ctypes.c_ulong(0x1000)
                                name_buf = ctypes.create_string_buffer(name_len.value)
                                status = ntdll.NtQueryObject(dup_handle, ObjectNameInformation, name_buf, name_len, ctypes.byref(name_len))

                                if status != 0:
                                    continue

                                uni = ctypes.cast(name_buf, ctypes.POINTER(UNICODE_STRING)).contents
                                if not (uni.Buffer and uni.Length):
                                    continue

                                name = ctypes.wstring_at(uni.Buffer, uni.Length // 2)
                                name_success += 1
                                
                                if "ROBLOX" in name:
                                    roblox_found += 1
                                    logging.info(f"Handle 0x{handle_id:x} name: {name}")

                                if "ROBLOX_singletonEvent" not in name:
                                    continue

                                # Found it! Now close it in the remote process.
                                logging.info(f"Found ROBLOX_singletonEvent at handle 0x{handle_id:x}, attempting to close...")
                                
                                # Close the duplicated handle in our process first
                                try:
                                    kernel32.CloseHandle(dup_handle)
                                    dup_handle = wintypes.HANDLE()  # Mark as closed
                                except Exception as e:
                                    logging.info(f"Warning: couldn't close local dup_handle: {e}")
                                
                                # Now close it in the REMOTE process using DUPLICATE_CLOSE_SOURCE
                                dummy_target = wintypes.HANDLE()
                                close_result = kernel32.DuplicateHandle(
                                    process_handle,
                                    remote_handle,
                                    current_process,
                                    ctypes.byref(dummy_target),
                                    0,
                                    False,
                                    DUPLICATE_CLOSE_SOURCE,
                                )
                                
                                if close_result:
                                    logging.info(f"DuplicateHandle with CLOSE_SOURCE returned success")
                                    
                                    # Close the dummy handle we got
                                    try:
                                        kernel32.CloseHandle(dummy_target)
                                    except Exception:
                                        pass
                                    
                                    # VERIFY: Try to duplicate the same handle again - should fail if truly closed
                                    verify_handle = wintypes.HANDLE()
                                    verify_result = kernel32.DuplicateHandle(
                                        process_handle,
                                        remote_handle,
                                        current_process,
                                        ctypes.byref(verify_handle),
                                        0,
                                        False,
                                        0,
                                    )
                                    
                                    if verify_result:
                                        # Handle still exists! Close failed or Roblox recreated it instantly
                                        try:
                                            kernel32.CloseHandle(verify_handle)
                                        except Exception:
                                            pass
                                        logging.info(f"WARNING: Handle 0x{handle_id:x} still exists after close attempt - Roblox may have recreated it!")
                                        result['errors'].append({'pid': pid, 'error': 'Handle still exists after close (possibly recreated by Roblox)'})
                                    else:
                                        # Good - handle no longer exists
                                        logging.info(f"✓ VERIFIED: Handle 0x{handle_id:x} successfully closed in PID {pid}")
                                    
                                    closed_count += 1
                                    closed_total += 1
                                    closed_this_pass += 1
                                    result['closed'].append({'pid': pid, 'handle_id': handle_id, 'name': name})
                                    result['closed_total'] = closed_total
                                    if stop_after_first:
                                        return result
                                else:
                                    error_code = ctypes.get_last_error()
                                    logging.info(f"Failed to close handle 0x{handle_id:x}, error code: {error_code}")
                            finally:
                                # Only close if we haven't already closed it (when we found the singleton event)
                                if dup_handle and dup_handle.value:
                                    try:
                                        kernel32.CloseHandle(dup_handle)
                                    except Exception:
                                        pass
                        
                        logging.info(f"PID {pid} scan stats: duplicated={dup_success}, named={name_success}, ROBLOX-related={roblox_found}")
                        
                    except Exception as e:
                        logging.info(f"Error processing PID {pid}: {e}")
                        result['errors'].append({'pid': pid, 'error': str(e)})
                    finally:
                        if process_handle:
                            try:
                                kernel32.CloseHandle(process_handle)
                            except Exception:
                                pass

                if not hold_mode:
                    break

                elapsed = time.time() - start_time
                if elapsed >= repeat_seconds:
                    break

                time.sleep(max(0.05, float(repeat_interval)))

            if closed_count == 0:
                logging.info("Could not find ROBLOX_singletonEvent handle to close")

            if not result['attempted_pids'] and last_attempted:
                result['attempted_pids'] = last_attempted

            return result

        except Exception as e:
            logging.info(f"Failed to close singleton events: {e}")
            return {'attempted_pids': [], 'closed': [], 'errors': [{'pid': None, 'error': str(e)}]}

    def release_all(self) -> None:
        """Cleanup on shutdown."""
        pass

class GameLauncher:
    def __init__(self, game_url="", status_callback: Callable = None):
        self.game_url = self._normalize_game_url(game_url)
        self.drivers = {}
        self.status_callback = status_callback
        self.launch_threads = {}
        self.player_pids = {}  # username -> set of RobloxPlayer PIDs started by us
        self.mutex_manager = MutexManager()
        logging.info("GameLauncher initialized")

    def shutdown(self) -> None:
        """Release held mutexes on application shutdown."""
        try:
            self.mutex_manager.release_all()
        except Exception:
            pass

    @staticmethod
    def _snapshot_roblox_player_processes() -> dict[int, float]:
        """Return {pid: create_time} for RobloxPlayer* processes.

        Using create_time lets us safely distinguish a newly launched RobloxPlayer
        from an already-running one (prevents us from killing the wrong process).
        """
        procs: dict[int, float] = {}
        try:
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    info = proc.info
                    name = info.get('name')
                    if not name or 'RobloxPlayer' not in name:
                        continue
                    create_time = info.get('create_time')
                    if isinstance(create_time, (int, float)):
                        procs[int(info['pid'])] = float(create_time)
                except Exception:
                    continue
        except Exception:
            pass
        return procs

    @staticmethod
    def _normalize_game_url(game_url: str) -> str:
        """Ensure we have a usable public game page URL.

        If the stored URL is a private server link or has query params, strip it
        down to the base /games/<placeId>/ URL.
        """
        default_url = "https://www.roblox.com/games/5233782396/Creatures-of-Sonaria-Survive-Kaiju-Animals"
        url = (game_url or "").strip()
        if not url:
            return default_url

        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return default_url
            if "roblox.com" not in (parsed.netloc or ""):
                return default_url
            if "/games/" not in (parsed.path or ""):
                return default_url

            # Strip any private server link codes or other query params.
            base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return base
        except Exception:
            return default_url
    
    def launch_game(self, account: Account, join_username: str | None = None, *, close_singleton_first: bool = True):
        """Launch Roblox game for an account"""
        logging.info(f"{account.username}: Starting launch...")

        if close_singleton_first:
            # Close singleton event handles in currently-running RobloxPlayer
            logging.info("Closing singleton event in RobloxPlayer...")
            self.mutex_manager.close_singleton_events_in_player()

            # Wait for close to take effect
            import time
            time.sleep(1)
        
        # Check if already running
        if account.username in self.drivers:
            logging.info(f"{account.username}: Already running")
            if self.status_callback:
                self.status_callback(account.username, "online")
            return
        
        # Launch in thread
        join_username_clean = (join_username or "").strip()
        thread = threading.Thread(target=self._launch_thread, args=(account, join_username_clean), daemon=False)
        thread.start()
        self.launch_threads[account.username] = thread
    
    def _launch_thread(self, account: Account, join_username: str):
        """Thread worker for launching game"""
        # Some users see Chrome drop the DevTools connection ("invalid session id").
        # Retrying once from scratch makes this much more reliable.
        last_error: Exception | None = None
        for attempt in range(2):
            driver = None
            try:
                if self.status_callback:
                    self.status_callback(account.username, "launching")

                # Get Roblox game URL
                game_url = self.game_url or "https://www.roblox.com/games/5154755852/"

                # Initialize Chrome driver
                # webdriver_manager can sometimes return a non-exe path; resolve to chromedriver.exe.
                chromedriver_path = self._get_chromedriver_executable()
                service = Service(chromedriver_path)

                options = webdriver.ChromeOptions()
                # Speed: don't wait for full page load event on heavy Roblox pages.
                options.page_load_strategy = "eager"
                # Isolate each account into its own Chrome profile (prevents profile lock + reduces crashes).
                base_dir = os.path.join(os.environ.get('TEMP', '.'), 'RobloxBotProfiles') if getattr(sys, 'frozen', False) else './chrome_profiles'
                profile_dir = os.path.join(base_dir, account.username)
                os.makedirs(profile_dir, exist_ok=True)
                options.add_argument(f"--user-data-dir={profile_dir}")
                options.add_argument("--no-first-run")
                options.add_argument("--no-default-browser-check")
                options.add_argument("--start-minimized")
                # Speed/UX: reduce extra prompts and heavy resources where possible.
                options.add_argument("--disable-notifications")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-gpu")
                options.add_experimental_option('excludeSwitches', ['enable-logging'])
                options.add_experimental_option(
                    "prefs",
                    {
                        "profile.default_content_setting_values.notifications": 2,
                        "profile.managed_default_content_settings.images": 2,
                    },
                )

                driver = webdriver.Chrome(service=service, options=options)
                self.drivers[account.username] = driver

                # Check if already logged in (full version behavior)
                logging.info(f"{account.username}: Checking if already logged in...")
                driver.get("https://www.roblox.com/home")
                time.sleep(3)
                is_logged_in = False
                try:
                    driver.find_element(By.XPATH, "//li[@id='navbar-settings']")
                    is_logged_in = True
                    logging.info(f"{account.username}: Already logged in!")
                except Exception:
                    logging.info(f"{account.username}: Not logged in, will attempt login...")

                if not is_logged_in:
                    logging.info(f"{account.username}: Navigating to login page...")
                    driver.get("https://www.roblox.com/login")
                    time.sleep(3)
                    logging.info(f"{account.username}: On login page, searching for fields...")

                    # Username field (full version strategy)
                    username_field = None
                    try:
                        username_field = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "login-username"))
                        )
                    except Exception:
                        try:
                            username_field = driver.find_element(By.XPATH, "//input[@type='text' or @inputmode='text']")
                        except Exception:
                            username_field = driver.find_element(By.XPATH, "//input[@placeholder='Username/Email/Phone']")

                    if username_field:
                        logging.info(f"{account.username}: Found username field, filling...")
                        try:
                            username_field.clear()
                        except Exception:
                            pass
                        time.sleep(0.5)
                        username_field.send_keys(account.username)
                        time.sleep(0.5)
                    else:
                        logging.error(f"{account.username}: Could not find username field!")

                    # Password field
                    password_field = None
                    try:
                        password_field = driver.find_element(By.ID, "login-password")
                    except Exception:
                        try:
                            password_field = driver.find_element(By.XPATH, "//input[@type='password']")
                        except Exception:
                            password_field = driver.find_element(By.XPATH, "//input[@placeholder='Password']")

                    if password_field:
                        logging.info(f"{account.username}: Found password field, filling...")
                        try:
                            password_field.clear()
                        except Exception:
                            pass
                        time.sleep(0.5)
                        password_field.send_keys(account.password)
                        time.sleep(0.5)
                    else:
                        logging.error(f"{account.username}: Could not find password field!")

                    # Login button (full version strategy)
                    try:
                        login_btn = driver.find_element(By.ID, "login-button")
                        logging.info(f"{account.username}: Found login button, clicking...")
                        login_btn.click()
                    except Exception:
                        try:
                            login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")
                            logging.info(f"{account.username}: Found login button (XPath), clicking...")
                            login_btn.click()
                        except Exception:
                            logging.info(f"{account.username}: Submitting form instead...")
                            if password_field:
                                try:
                                    password_field.submit()
                                except Exception:
                                    pass

                    logging.info(f"{account.username}: Waiting for login to complete...")
                    time.sleep(7)

                # Navigate to game (or join a specific user)
                if join_username:
                    logging.info(f"{account.username}: Joining user via profile: {join_username}")
                    if self.status_callback:
                        self.status_callback(account.username, "joining user")
                else:
                    logging.info(f"{account.username}: Navigating to game...")
                    if self.status_callback:
                        self.status_callback(account.username, "joining game")
                before = self._snapshot_roblox_player_processes()

                play_click_time = time.time()
                if join_username:
                    self._join_user_by_profile(driver, join_username, account.username)
                    logging.info(f"{account.username}: Join clicked")
                else:
                    driver.get(game_url)
                    # Click Play button on the game page (required to launch Roblox Player)
                    self._click_game_play_button(driver, account.username)
                    logging.info(f"{account.username}: Play clicked")

                # Keep singleton event held during entire bot session (don't release)

                # Give RobloxPlayer a moment to start, then track its PID(s).
                time.sleep(5)
                after = self._snapshot_roblox_player_processes()

                # New PIDs since before snapshot...
                new_pids = set(after.keys()) - set(before.keys())

                # ...and also created after we clicked Play (with a small tolerance).
                # This prevents us from ever tracking/killing a pre-existing Roblox.
                min_create_time = play_click_time - 2.0
                new_pids = {pid for pid in new_pids if after.get(pid, 0.0) >= min_create_time}

                self.player_pids[account.username] = new_pids
                logging.info(f"{account.username}: Tracked Roblox player PIDs: {sorted(new_pids)}")

                if self.status_callback:
                    self.status_callback(account.username, "online")
                return
            except Exception as e:
                last_error = e
                msg = str(e).lower()
                should_retry = attempt == 0 and (
                    "invalid session id" in msg or
                    "not connected to devtools" in msg or
                    "disconnected" in msg
                )
                logging.error(f"{account.username}: Launch error: {e}")
                if should_retry:
                    logging.info(f"{account.username}: Chrome session dropped; retrying launch once...")
                else:
                    if self.status_callback:
                        self.status_callback(account.username, "error")

                # Cleanup driver
                try:
                    if driver is not None:
                        driver.quit()
                except Exception:
                    pass
                if account.username in self.drivers:
                    del self.drivers[account.username]
                if not should_retry and account.username in self.player_pids:
                    del self.player_pids[account.username]
                if not should_retry:
                    return

        # If we fall through, raise or mark error.
        if self.status_callback:
            self.status_callback(account.username, "error")
        if last_error:
            raise last_error

    @staticmethod
    def _join_user_by_profile(driver: webdriver.Chrome, target_username: str, launcher_username: str) -> None:
        """Navigate to a user's profile and click Join if available."""
        profile_url = f"https://www.roblox.com/user.aspx?username={target_username}"
        driver.get(profile_url)

        # Speed: poll the DOM quickly and click as soon as the Join button appears.
        # (Roblox profile pages are heavy; the Join button can appear late after XHR.)
        js_click_join = r"""
            const selectors = [
              "button[data-testid='join-game-button']",
              "button#profile-header-join-game-button",
              "button[data-testid='profile-join-button']",
              "a[data-testid='join-game-button']",
            ];

            function isVisible(el) {
              if (!el) return false;
              const r = el.getBoundingClientRect();
              const style = window.getComputedStyle(el);
              return r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
            }

            // First try: stable selectors.
            for (const sel of selectors) {
              const el = document.querySelector(sel);
              if (isVisible(el) && !el.disabled) {
                el.scrollIntoView({block: 'center'});
                el.click();
                return true;
              }
            }

            // Fallback: any visible button/link containing the word "Join".
            const candidates = Array.from(document.querySelectorAll('button, a'))
              .filter(el => isVisible(el) && (el.textContent || '').trim().toLowerCase() === 'join');
            for (const el of candidates) {
              if (!el.disabled) {
                el.scrollIntoView({block: 'center'});
                el.click();
                return true;
              }
            }

            return false;
        """

        try:
            WebDriverWait(driver, 8, poll_frequency=0.1).until(
                lambda d: bool(d.execute_script(js_click_join))
            )
            return
        except TimeoutException as e:
            # As a last resort, use a slightly slower Selenium wait.
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Join')]"))
                )
                try:
                    ActionChains(driver).move_to_element(element).pause(0.05).click(element).perform()
                except Exception:
                    driver.execute_script("arguments[0].click();", element)
                return
            except Exception:
                raise TimeoutException(
                    f"{launcher_username}: Could not find Join button on {target_username} profile"
                ) from e

    @staticmethod
    def _click_game_play_button(driver: webdriver.Chrome, username: str) -> None:
        """Find and click the Play button on a Roblox game page."""
        wait_short = WebDriverWait(driver, 12)
        wait_long = WebDriverWait(driver, 20)

        def click_element(el):
            try:
                ActionChains(driver).move_to_element(el).pause(0.05).click(el).perform()
            except (ElementClickInterceptedException, Exception):
                driver.execute_script("arguments[0].click();", el)

        # Primary: Roblox game pages typically have this stable ID.
        try:
            element = wait_long.until(EC.presence_of_element_located((By.ID, "game-details-play-button")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            click_element(element)
            return
        except TimeoutException:
            pass

        # Fallbacks (keep these fast to avoid long delays).
        candidates = [
            (By.CSS_SELECTOR, "button[data-testid='play-button']"),
            (By.XPATH, "//button[contains(translate(., 'PLAY', 'play'), 'play')]"),
        ]
        last_error = None
        for by, value in candidates:
            try:
                element = wait_short.until(EC.presence_of_element_located((by, value)))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                click_element(element)
                return
            except TimeoutException as e:
                last_error = e

        raise TimeoutException(f"{username}: Could not find Play button") from last_error

    @staticmethod
    def _type_into_locator(driver: webdriver.Chrome, locator, text: str) -> None:
        """Type into an input reliably; refetch element to avoid staleness.

        Roblox login page can re-render inputs, causing stale element errors.
        """
        # Fast + robust: if we have a CSS selector, set via JS directly to avoid stale elements.
        if locator and locator[0] == By.CSS_SELECTOR:
            css = locator[1]
            last_error = None
            for _ in range(4):
                try:
                    WebDriverWait(driver, 20).until(lambda d: d.execute_script(
                        "return document.querySelector(arguments[0]) !== null;", css
                    ))
                    driver.execute_script(
                        """
                        const sel = arguments[0];
                        const value = arguments[1];
                        const el = document.querySelector(sel);
                        if (!el) return false;
                        el.focus();
                        el.value = value;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, key: 'a' }));
                        return true;
                        """,
                        css,
                        text,
                    )
                    return
                except Exception as e:
                    last_error = e
                    continue

            raise last_error if last_error else RuntimeError("Failed to type into element")

        # Fallback path for non-CSS locators.
        wait = WebDriverWait(driver, 20)
        last_error = None
        for _ in range(4):
            try:
                element = wait.until(EC.visibility_of_element_located(locator))
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                except Exception:
                    pass

                try:
                    element.click()
                except StaleElementReferenceException as e:
                    last_error = e
                    continue
                except Exception:
                    pass

                try:
                    element.clear()
                except StaleElementReferenceException as e:
                    last_error = e
                    continue
                except Exception:
                    pass

                try:
                    element.send_keys(text)
                    return
                except (ElementNotInteractableException, StaleElementReferenceException) as e:
                    last_error = e
                    continue
                except Exception as e:
                    last_error = e
                    continue
            except Exception as e:
                last_error = e

        raise last_error if last_error else RuntimeError("Failed to type into element")

    @staticmethod
    def _type_into_first_available(driver: webdriver.Chrome, locators: list, text: str) -> None:
        """Try multiple locators until one succeeds."""
        last_error: Exception | None = None
        for locator in locators:
            try:
                GameLauncher._type_into_locator(driver, locator, text)
                return
            except Exception as e:
                last_error = e
                continue
        raise last_error if last_error else RuntimeError("Failed to type into any locator")

    @staticmethod
    def _get_first_available_element(driver: webdriver.Chrome, locators: list):
        """Return the first element that can be located and is visible."""
        last_error: Exception | None = None
        wait = WebDriverWait(driver, 10)
        for locator in locators:
            try:
                return wait.until(EC.visibility_of_element_located(locator))
            except Exception as e:
                last_error = e
                continue
        raise last_error if last_error else RuntimeError("Failed to find any matching element")

    @staticmethod
    def _click_first_available(driver: webdriver.Chrome, locators: list) -> None:
        """Try multiple locators until one click succeeds."""
        last_error: Exception | None = None
        for locator in locators:
            try:
                GameLauncher._click_locator(driver, locator)
                return
            except Exception as e:
                last_error = e
                continue
        raise last_error if last_error else RuntimeError("Failed to click any locator")

    @staticmethod
    def _click_locator(driver: webdriver.Chrome, locator) -> None:
        """Click an element by locator with retries to avoid stale/interactable issues."""
        wait = WebDriverWait(driver, 20)
        last_error = None
        for _ in range(4):
            try:
                element = wait.until(EC.element_to_be_clickable(locator))
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                except Exception:
                    pass
                try:
                    element.click()
                except (ElementClickInterceptedException, StaleElementReferenceException):
                    driver.execute_script("arguments[0].click();", element)
                return
            except Exception as e:
                last_error = e
                continue

        raise last_error if last_error else RuntimeError("Failed to click element")

    @staticmethod
    def _get_chromedriver_executable() -> str:
        """Return a valid path to chromedriver.exe for the current Chrome install."""
        installed_path = ChromeDriverManager().install()
        path_obj = Path(installed_path)

        if path_obj.is_file() and path_obj.suffix.lower() == ".exe":
            return str(path_obj)

        search_root = path_obj if path_obj.is_dir() else path_obj.parent
        candidates = list(search_root.rglob("chromedriver.exe"))
        if candidates:
            # Prefer the shortest path (usually .../chromedriver.exe) if multiple copies exist.
            candidates_sorted = sorted(candidates, key=lambda p: len(str(p)))
            return str(candidates_sorted[0])

        # Fallback: return what webdriver_manager gave us (will raise a clearer error upstream)
        return installed_path
    
    def stop_game(self, account_or_username):
        """Stop Roblox for an account (accepts Account or username string)."""
        username = account_or_username.username if hasattr(account_or_username, "username") else str(account_or_username)
        logging.info(f"{username}: Stopping...")
        
        # Close browser (non-blocking; Chrome quit can take ~10s and would freeze the GUI)
        driver = self.drivers.pop(username, None)
        if driver is not None:
            def _quit_driver(drv, user):
                try:
                    drv.quit()
                except Exception as e:
                    logging.info(f"{user}: driver.quit() error: {e}")

            t = threading.Thread(target=_quit_driver, args=(driver, username), daemon=True)
            t.start()
        
        if self.status_callback:
            self.status_callback(username, "offline")

        # Kill only the RobloxPlayer processes we started for this account.
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
    
    def launch_all_staggered(self, accounts):
        """Launch accounts with staggered delays"""
        def staggered_launch_thread():
            for i, account in enumerate(accounts):
                if i > 0:
                    time.sleep(3)  # 3 second delay between launches
                self.launch_game(account)
        
        thread = threading.Thread(target=staggered_launch_thread, daemon=False)
        thread.start()
    
    def stop_all_games(self, accounts=None):
        """Stop all running instances we are tracking."""
        if accounts is not None:
            for account in accounts:
                self.stop_game(account)
            return

        for username in list(self.drivers.keys()):
            self.stop_game(username)
        for username in list(self.player_pids.keys()):
            self.stop_game(username)
    
    @staticmethod
    def get_session_logs():
        """Get current session logs"""
        return session_handler.get_logs()
