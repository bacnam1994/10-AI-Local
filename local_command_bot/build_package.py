"""PyInstaller Build Script to package Local Command Bot for Windows."""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

cmd = [
    sys.executable,
    "-m", "PyInstaller",
    "--noconfirm",
    "--onedir",
    "--windowed",
    "--name", "LocalCommandBot",
    "--add-data", f"{BASE_DIR / 'prompts'};prompts",
    "--add-data", f"{BASE_DIR / 'templates'};templates",
    "--hidden-import", "pyside6",
    "--hidden-import", "httpx",
    "--hidden-import", "reportlab",
    "--hidden-import", "docx",
    "--hidden-import", "keyring",
    "--hidden-import", "keyring.backends",
    "--hidden-import", "keyring.backends.Windows",
    str(BASE_DIR / "app" / "main.py")
]

print("Executing PyInstaller command:", " ".join(cmd))
subprocess.run(cmd, check=True, cwd=str(BASE_DIR))
print("\n[SUCCESS] Đóng gói thành công vào thư mục: dist/LocalCommandBot")
