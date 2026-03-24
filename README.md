# ImgBB Screenshot Uploader

Automatically upload screenshots to [ImgBB](https://imgbb.com) and copy the image link to your clipboard. Take a screenshot with Windows Snipping Tool (`Win+Shift+S`), and within seconds the shareable image URL replaces your clipboard content — ready to paste anywhere.

No manual uploading. No browser tabs. Just screenshot and paste the link.

## How It Works

1. A lightweight Python script runs silently in the background
2. It monitors your clipboard for new images
3. When a screenshot is detected, it uploads to ImgBB via their free API
4. The clipboard is replaced with the direct image URL (e.g. `https://i.ibb.co/abc123/screenshot.png`)
5. Just `Ctrl+V` to paste the link anywhere — Slack, Discord, GitHub, email, etc.

## Features

- **Instant clipboard replacement** — screenshot → image link in ~2-3 seconds
- **Runs silently** — no console window, no tray icon clutter
- **Auto-restart on crash** — `launcher.pyw` monitors the uploader and restarts it automatically if it exits
- **Auto-start on boot** — VBS startup script launches the uploader silently on login
- **Duplicate detection** — skips re-uploading the same screenshot (Windows Snipping Tool sometimes triggers the clipboard twice)
- **Upload history** — all links saved to `upload_log.json` with timestamps
- **Free hosting** — uses ImgBB's free API (32 MB max per image)
- **Lightweight** — minimal CPU/memory usage, polls clipboard every 0.5 seconds
- **64-bit Windows compatible** — proper Win32 API clipboard handling

## Quick Start

### 1. Get a free ImgBB API Key

1. Go to [https://api.imgbb.com](https://api.imgbb.com)
2. Create an account (Google sign-in supported)
3. Copy your API key from the dashboard

### 2. Install

```bash
git clone https://github.com/mhamzahashim/imgbb-ss.git
cd imgbb-ss
pip install -r requirements.txt
```

### 3. Configure

Open `uploader.pyw` and replace the API key:

```python
IMGBB_API_KEY = "YOUR_API_KEY_HERE"
```

### 4. Run

**Double-click** `launcher.pyw` — it starts the uploader silently and auto-restarts it if it ever crashes.

Or from the command line:

```bash
pythonw launcher.pyw
```

### 5. Auto-Start on Login (Optional)

1. Press `Win+R` → type `shell:startup` → Enter
2. Create a file called `screenshot-uploader.vbs` in the Startup folder with this content:

```vbs
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\path\to\imgbb-ss"
WshShell.Run "pythonw ""C:\path\to\imgbb-ss\launcher.pyw""", 0, False
```

Replace `C:\path\to\imgbb-ss` with the actual path where you cloned the repo.

The uploader will now start silently on every login and auto-restart on crash.

## Usage

1. Press `Win+Shift+S` to take a screenshot (or use Snipping Tool)
2. Wait ~2-3 seconds
3. Press `Ctrl+V` — the ImgBB image link is pasted instead of the image

## Upload History

All uploads are logged to `upload_log.json`:

```json
[
  {
    "link": "https://i.ibb.co/abc123/screenshot.png",
    "delete_url": "https://ibb.co/xyz789/delete_hash",
    "at": "2025-03-14 10:30:45"
  }
]
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Script not detecting screenshots | Make sure `pythonw` is running: `tasklist \| findstr pythonw` |
| Clipboard still has image, not link | Wait 2-3 seconds after taking the screenshot |
| Upload fails | Check your internet connection and ImgBB API key |
| Script crashes on startup | Run `python uploader.pyw` in a terminal to see errors |
| Script keeps crashing | Check `error.log` — if it crashes 5 times in 60s, the launcher backs off for 60s before retrying |
| Check logs | Look at `error.log` in the script directory (launcher events are prefixed with `[launcher]`) |

## Requirements

- Windows 10/11
- Python 3.8+
- Internet connection

## Tech Stack

- **Pillow** — clipboard image capture via `ImageGrab`
- **requests** — HTTP uploads to ImgBB API
- **ctypes** — native Win32 clipboard API (64-bit safe)

## Keywords

screenshot uploader, auto upload screenshot, clipboard to image link, imgbb uploader, windows screenshot to url, snipping tool auto upload, screenshot sharing tool, image hosting automation, clipboard image uploader, free screenshot hosting, screenshot to link, auto image upload windows, screen capture to url, imgbb api python, screenshot url generator, paste screenshot link, windows clipboard monitor, automatic screenshot sharing, image link generator, snip and share

## License

MIT License — use it however you want.

## Contributing

PRs welcome. If you have ideas for improvements, open an issue or submit a pull request.
