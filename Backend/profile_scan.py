import os
import time
from pathlib import Path

scan_path = os.path.expanduser("~/Documents/IphoneImport")
start_time = time.time()

supported_extensions = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.jpg', '.jpeg', '.png', '.heic'}
found_files = []

for root, _, files in os.walk(scan_path):
    for file in files:
        if Path(file).suffix.lower() in supported_extensions:
            full_path = os.path.join(root, file)
            found_files.append(full_path)

end_time = time.time()
print(f"Found {len(found_files)} files in {end_time - start_time:.4f} seconds")
