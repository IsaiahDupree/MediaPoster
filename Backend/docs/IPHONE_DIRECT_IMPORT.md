# iPhone Direct File Import with Fingerprinting

**Date:** December 26, 2024  
**Status:** Implemented ✅

---

## 🎯 Overview

Direct file import from iPhone with intelligent duplicate detection using fast fingerprinting. This avoids re-importing files that already exist.

---

## 🔧 Implementation

### Method 1: Image Capture + Fingerprinting (Current - Works on macOS)

**How it works:**
1. Uses AppleScript to automate Image Capture
2. Transfers all files to import folder
3. **After transfer**: Applies fingerprinting to detect duplicates
4. Removes duplicate files automatically
5. Maintains index for future duplicate detection

**Fingerprinting Algorithm:**
- Fast hash: `sha256(first_4MB + last_4MB + file_size)`
- Much faster than full file hash
- Strong enough for duplicate detection
- Stored in `.import_index.json`

**Files Created:**
- `.import_manifest.jsonl` - Append-only log of all imports
- `.import_index.json` - Fingerprint → file path mapping

### Method 2: Direct AFC Access (Future - Requires pymobiledevice3)

**Status:** Partially implemented, API compatibility issues

**Requirements:**
- `pip install pymobiledevice3`
- iPhone unlocked and trusted

**Benefits:**
- No Image Capture needed
- Direct file access
- Can list files before transfer
- More control over transfer process

---

## 📊 API Endpoints

### `POST /api/import/ios/transfer-files`

**Image Capture method with duplicate detection**

**Request:**
```json
{
  "media_types": ["video", "image"],
  "delete_after_transfer": false
}
```

**Response:**
```json
{
  "status": "success",
  "transferred_count": 15,
  "duplicates_removed": 3,
  "destination": "/Volumes/My Passport/MediaPoster/workspace1/iphone_import"
}
```

### `POST /api/import/ios/transfer-files-direct`

**Direct AFC method (requires pymobiledevice3)**

**Request:**
```json
{
  "media_types": ["video", "image"],
  "max_files": 50
}
```

**Response:**
```json
{
  "status": "success",
  "imported": 12,
  "skipped": 8,
  "total_found": 20
}
```

---

## 🔍 Fingerprinting Details

### Fast Fingerprint Algorithm

```python
def fingerprint(file_path, sample_bytes=4MB):
    size = file_size
    hash = sha256()
    hash.update(str(size))
    hash.update(read_first_4MB(file))
    if size > 4MB:
        hash.update(read_last_4MB(file))
    return hash.hexdigest()
```

**Why this works:**
- Video files have unique headers/metadata at start
- File size is a strong indicator
- Tail bytes catch end-of-file differences
- 4MB sample is enough for most videos (even 1GB+ files)

**Performance:**
- Full hash of 1GB file: ~5-10 seconds
- Fast fingerprint: ~0.1-0.5 seconds
- **10-100x faster** for large files

---

## 📁 File Structure

```
iphone_import/
├── IMG_1234.MOV          # Imported files
├── IMG_1235.MOV
├── .import_manifest.jsonl  # Import log
└── .import_index.json      # Fingerprint index
```

**Manifest Format (JSONL):**
```json
{"src": "/DCIM/100APPLE/IMG_1234.MOV", "dst": "/path/to/IMG_1234.MOV", "fp": "abc123...", "size": 12345678, "imported_at": "2024-12-26T10:00:00Z"}
```

**Index Format (JSON):**
```json
{
  "abc123...": "/path/to/IMG_1234.MOV",
  "def456...": "/path/to/IMG_1235.MOV"
}
```

---

## 🚀 Usage

### Frontend

Click **"Transfer Files Automatically"** button in iOS Import page.

### Backend API

```bash
curl -X POST http://localhost:5555/api/import/ios/transfer-files \
  -H "Content-Type: application/json" \
  -d '{"media_types": ["video", "image"]}'
```

### Python Script

```python
from services.iphone_direct_import import iPhoneDirectImporter
from pathlib import Path

importer = iPhoneDirectImporter(Path("/path/to/import"))
if importer.connect():
    result = importer.import_files(media_types=["video", "image"])
    print(f"Imported: {result['imported']}, Skipped: {result['skipped']}")
    importer.disconnect()
```

---

## ✅ Benefits

1. **No Duplicates**: Automatic duplicate detection and removal
2. **Fast**: Fingerprinting is 10-100x faster than full hashing
3. **Reliable**: Index persists across sessions
4. **Efficient**: Only imports new files
5. **Safe**: Doesn't delete from iPhone by default

---

## 🔮 Future Enhancements

1. **Date Filtering**: Only import files newer than X days
2. **Auto-Organization**: Create folders by date taken
3. **Progress Tracking**: Real-time progress for large transfers
4. **Selective Import**: Choose specific files before transfer
5. **Direct AFC**: Full pymobiledevice3 integration when API is stable

---

*For questions or issues, see the implementation in `Backend/services/iphone_direct_import.py`*

