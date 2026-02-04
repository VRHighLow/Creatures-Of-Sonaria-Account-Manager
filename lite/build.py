import os
import sys

# Use Python 3.14 installation
python_exe = r"C:\Users\Owner\AppData\Local\Programs\Python\Python314\python.exe"

if not os.path.exists(python_exe):
    print("ERROR: Python not found at expected location")
    sys.exit(1)

print(f"Using Python: {python_exe}")

print("Installing dependencies...")
os.system(f'"{python_exe}" -m pip install -r requirements.txt')

print("\nInstalling PyInstaller...")
os.system(f'"{python_exe}" -m pip install pyinstaller')

print("\nBuilding single-file EXE (this may take a few minutes)...")
os.system(f'"{python_exe}" -m PyInstaller RobloxBotCOS.spec --clean --noconfirm --distpath dist/full')

if os.path.exists("dist/full/RobloxBotCOS.exe"):
    print("\n✓ SUCCESS! Full version EXE created at: dist/full/RobloxBotCOS.exe")
    print("\nThis is the FULL version - Includes Macro Controls!")
else:
    print("\n✗ Build failed. Check errors above.")

