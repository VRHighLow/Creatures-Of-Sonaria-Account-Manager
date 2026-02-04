import os
import sys
import time
import subprocess

# Use Python 3.14 installation
python_exe = r"C:\Users\Owner\AppData\Local\Programs\Python\Python314\python.exe"

if not os.path.exists(python_exe):
    print("ERROR: Python not found at expected location")
    sys.exit(1)

print(f"Using Python: {python_exe}")

print("Installing dependencies...")
subprocess.run([python_exe, "-m", "pip", "install", "-r", "requirements.txt"], check=False)

print("\nInstalling PyInstaller...")
subprocess.run([python_exe, "-m", "pip", "install", "pyinstaller"], check=False)


def _try_remove(path: str, retries: int = 20, delay_s: float = 0.5) -> bool:
    if not os.path.exists(path):
        return True
    for _ in range(retries):
        try:
            os.remove(path)
            return True
        except PermissionError:
            time.sleep(delay_s)
        except Exception:
            time.sleep(delay_s)
    return False

print("\nBuilding LITE version (Account Manager only - no macros)...")

# Prevent PyInstaller from failing when trying to overwrite a temporarily locked EXE.
os.makedirs("dist", exist_ok=True)
exe_path = os.path.join("dist", "CosManagerLite.exe")
if not _try_remove(exe_path):
    print(f"\n✗ Build blocked: could not overwrite {exe_path} (file is in use).")
    print("Close any running CosManagerLite.exe and close File Explorer previews, then try again.")
    sys.exit(1)

result = subprocess.run(
    [python_exe, "-m", "PyInstaller", "RobloxAccountManager.spec", "--clean", "--noconfirm"],
    check=False,
)

if result.returncode != 0:
    print(f"\n✗ Build failed (PyInstaller exit code {result.returncode}).")
    sys.exit(result.returncode)

if os.path.exists("dist/CosManagerLite.exe"):
    print("\nSUCCESS! Lite EXE created at: dist/CosManagerLite.exe")
    print("\nThis is the LITE version - Account Management ONLY (No Macros)")
else:
    print("\n✗ Build failed. Check errors above.")
    sys.exit(1)
