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
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageGrab

# Log to file since .pyw has no console
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
ERROR_LOG = os.path.join(LOG_DIR, "error.log")
UPLOAD_LOG = os.path.join(LOG_DIR, "upload_log.json")
IMGBB_API_KEY = "01d1a3244bec84ed1d30c7dc07e75ade"  # Get yours at https://api.imgbb.com
POLL_INTERVAL = 0.2

def log_error(msg):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040

user32.OpenClipboard.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.restype = ctypes.c_bool
user32.EmptyClipboard.restype = ctypes.c_bool
user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.CloseClipboard.restype = ctypes.c_bool
kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = ctypes.c_bool
kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
kernel32.GlobalFree.restype = ctypes.c_void_p


def set_clipboard_text(text):
    for _ in range(10):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.1)
    else:
        log_error("Clipboard error: could not open clipboard")
        return False

    h_mem = None
    try:
        if not user32.EmptyClipboard():
            log_error("Clipboard error: EmptyClipboard failed")
            return False

        text_bytes = (text + "\0").encode("utf-16-le")
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, len(text_bytes))
        if not h_mem:
            log_error("Clipboard error: GlobalAlloc failed")
            return False

        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            log_error("Clipboard error: GlobalLock failed")
            return False

        ctypes.memmove(ptr, text_bytes, len(text_bytes))
        kernel32.GlobalUnlock(h_mem)

        if not user32.SetClipboardData(CF_UNICODETEXT, h_mem):
            log_error("Clipboard error: SetClipboardData failed")
            return False

        h_mem = None  # Clipboard owns the memory after a successful SetClipboardData.
        return True
    except Exception as e:
        log_error(f"Clipboard error: {e}")
        return False
    finally:
        if h_mem:
            kernel32.GlobalFree(h_mem)
        user32.CloseClipboard()


def get_clipboard_seq():
    return user32.GetClipboardSequenceNumber()


def write_upload_log(entry):
    log = []
    if os.path.exists(UPLOAD_LOG):
        try:
            with open(UPLOAD_LOG, "r") as f:
                log = json.load(f)
        except (json.JSONDecodeError, ValueError):
            log_error("upload_log.json corrupted, starting fresh")
            log = []
    log.append(entry)
    with open(UPLOAD_LOG, "w") as f:
        json.dump(log, f, indent=2)


def upload_imgbb(image_bytes, name):
    data = base64.b64encode(image_bytes).decode("utf-8")
    try:
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": data, "name": name},
            timeout=10,
        )
    except requests.RequestException as e:
        log_error(f"ImgBB upload request failed: {e}")
        return None

    if r.status_code != 200:
        log_error(f"ImgBB upload failed: {r.status_code} {r.text}")
        return None

    d = r.json()
    return {
        "provider": "imgbb",
        "link": d["data"]["url"],
        "delete_url": d["data"]["delete_url"],
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def upload_catbox(image_bytes, name):
    try:
        r = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (f"{name}.png", image_bytes, "image/png")},
            timeout=10,
        )
    except requests.RequestException as e:
        log_error(f"Catbox upload request failed: {e}")
        return None

    if r.status_code != 200:
        log_error(f"Catbox upload failed: {r.status_code} {r.text}")
        return None

    link = r.text.strip()
    if not link.startswith(("http://", "https://")):
        log_error(f"Catbox upload returned unexpected response: {link[:200]}")
        return None

    return {
        "provider": "catbox",
        "link": link,
        "delete_url": "",
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def upload_uguu(image_bytes, name):
    try:
        r = requests.post(
            "https://uguu.se/upload",
            files={"files[]": (f"{name}.png", image_bytes, "image/png")},
            timeout=10,
        )
    except requests.RequestException as e:
        log_error(f"uguu upload request failed: {e}")
        return None

    if r.status_code != 200:
        log_error(f"uguu upload failed: {r.status_code} {r.text[:200]}")
        return None

    try:
        link = r.json()["files"][0]["url"]
    except Exception as e:
        log_error(f"uguu upload parse failed: {e}")
        return None

    return {
        "provider": "uguu",
        "link": link,
        "delete_url": "",
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def encode_png(image):
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    buf = io.BytesIO()
    image.convert("RGB").quantize(colors=256).save(buf, format="PNG")
    q_bytes = buf.getvalue()

    if len(q_bytes) < len(png_bytes) * 0.8:
        return q_bytes
    return png_bytes


def upload(image):
    image_bytes = encode_png(image)
    name = f"ss_{time.strftime('%Y%m%d_%H%M%S')}"

    log_error("Uploading in parallel (catbox/uguu/imgbb)...")
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(upload_catbox, image_bytes, name),
            pool.submit(upload_uguu, image_bytes, name),
            pool.submit(upload_imgbb, image_bytes, name),
        }
        for fut in as_completed(futures):
            try:
                entry = fut.result()
            except Exception as e:
                log_error(f"Upload thread failed: {e}")
                continue
            if entry:
                write_upload_log(entry)
                return entry["link"]

    log_error("All uploads failed (catbox/uguu/imgbb)")
    return None


def show_toast(link):
    """Show a balloon tip from system tray area."""
    ctypes.windll.user32.MessageBeep(0x00000040)  # MB_ICONINFORMATION sound


def main():
    log_error("Script started")
    last_seq = get_clipboard_seq()
    last_img_hash = None
    last_upload_time = 0
    last_attempt_hash = None
    last_attempt_time = 0

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

            # grabclipboard() returns a list of paths when files are copied from Explorer
            if isinstance(img, list):
                path = next((p for p in img if p.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"))), None)
                if not path:
                    continue
                try:
                    img = Image.open(path)
                except Exception as e:
                    log_error(f"Could not open clipboard file {path}: {e}")
                    continue

            # Deduplicate: skip if same image was just uploaded
            img_hash = hashlib.md5(img.tobytes()).hexdigest()
            now = time.time()
            if img_hash == last_img_hash and (now - last_upload_time) < 10:
                log_error(f"Skipped duplicate (same image within {now - last_upload_time:.1f}s)")
                continue
            if img_hash == last_attempt_hash and (now - last_attempt_time) < 10:
                log_error(f"Skipped retry (same image attempted within {now - last_attempt_time:.1f}s)")
                continue

            log_error("Image detected, uploading...")
            last_attempt_hash = img_hash
            last_attempt_time = now
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
