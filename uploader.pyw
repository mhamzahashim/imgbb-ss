import time
import os
import sys
import io
import json
import base64
import ctypes
import hashlib
import traceback
import requests
from PIL import ImageGrab

# Log to file since .pyw has no console
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
ERROR_LOG = os.path.join(LOG_DIR, "error.log")
UPLOAD_LOG = os.path.join(LOG_DIR, "upload_log.json")
IMGBB_API_KEY = "YOUR_API_KEY_HERE"  # Get yours at https://api.imgbb.com
POLL_INTERVAL = 0.5

def log_error(msg):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

# Fix ctypes for 64-bit Windows
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
user32.SetClipboardData.restype = ctypes.c_void_p


def set_clipboard_text(text):
    for _ in range(10):
        if user32.OpenClipboard(0):
            break
        time.sleep(0.1)
    else:
        log_error("Could not open clipboard")
        return False
    try:
        user32.EmptyClipboard()
        text_bytes = (text + "\0").encode("utf-16-le")
        h_mem = kernel32.GlobalAlloc(0x0042, len(text_bytes))
        if not h_mem:
            log_error("GlobalAlloc failed")
            return False
        ptr = kernel32.GlobalLock(h_mem)
        ctypes.memmove(ptr, text_bytes, len(text_bytes))
        kernel32.GlobalUnlock(h_mem)
        result = user32.SetClipboardData(13, h_mem)
        return bool(result)
    finally:
        user32.CloseClipboard()


def get_clipboard_seq():
    return user32.GetClipboardSequenceNumber()


def upload(image):
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    data = base64.b64encode(buf.getvalue()).decode("utf-8")
    r = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": IMGBB_API_KEY, "image": data, "name": f"ss_{time.strftime('%Y%m%d_%H%M%S')}"},
    )
    if r.status_code == 200:
        d = r.json()
        link = d["data"]["url"]
        # Save to log
        log = []
        if os.path.exists(UPLOAD_LOG):
            try:
                with open(UPLOAD_LOG, "r") as f:
                    log = json.load(f)
            except (json.JSONDecodeError, ValueError):
                log_error("upload_log.json corrupted, starting fresh")
                log = []
        log.append({"link": link, "delete_url": d["data"]["delete_url"], "at": time.strftime("%Y-%m-%d %H:%M:%S")})
        with open(UPLOAD_LOG, "w") as f:
            json.dump(log, f, indent=2)
        return link
    else:
        log_error(f"Upload failed: {r.status_code} {r.text}")
        return None


def show_toast(link):
    """Show a balloon tip from system tray area."""
    ctypes.windll.user32.MessageBeep(0x00000040)  # MB_ICONINFORMATION sound


def main():
    log_error("Script started")
    last_seq = get_clipboard_seq()
    last_img_hash = None
    last_upload_time = 0

    while True:
        try:
            time.sleep(POLL_INTERVAL)
            seq = get_clipboard_seq()
            if seq == last_seq:
                continue
            last_seq = seq

            img = ImageGrab.grabclipboard()
            if img is None:
                continue

            # Deduplicate: skip if same image was just uploaded
            img_hash = hashlib.md5(img.tobytes()).hexdigest()
            now = time.time()
            if img_hash == last_img_hash and (now - last_upload_time) < 10:
                log_error(f"Skipped duplicate (same image within {now - last_upload_time:.1f}s)")
                continue

            log_error("Image detected, uploading...")
            link = upload(img)
            if link:
                last_img_hash = img_hash
                last_upload_time = time.time()
                ok = set_clipboard_text(link)
                time.sleep(0.2)
                last_seq = get_clipboard_seq()
                log_error(f"OK clipboard={ok} link={link}")
                show_toast(link)
            else:
                log_error("Upload returned None")
        except Exception as e:
            log_error(f"ERROR: {traceback.format_exc()}")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_error(f"FATAL: {traceback.format_exc()}")
