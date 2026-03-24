"""
Auto-restart wrapper for uploader.pyw.
Relaunches the script if it crashes, with a brief delay to avoid rapid loops.
Place a shortcut to this file in shell:startup to run on boot.
"""
import subprocess
import sys
import os
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(SCRIPT_DIR, "uploader.pyw")
ERROR_LOG = os.path.join(SCRIPT_DIR, "error.log")
RESTART_DELAY = 3  # seconds between restarts
MAX_FAST_CRASHES = 5  # if it crashes this many times within FAST_WINDOW, wait longer
FAST_WINDOW = 60  # seconds
LONG_DELAY = 60  # longer wait after repeated fast crashes


def log(msg):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - [launcher] {msg}\n")


def main():
    crash_times = []

    while True:
        log("Starting uploader.pyw")
        proc = subprocess.Popen([sys.executable, SCRIPT])
        proc.wait()
        exit_code = proc.returncode
        log(f"uploader.pyw exited with code {exit_code}")

        # Track crash frequency
        now = time.time()
        crash_times = [t for t in crash_times if now - t < FAST_WINDOW]
        crash_times.append(now)

        if len(crash_times) >= MAX_FAST_CRASHES:
            log(f"Crashed {len(crash_times)} times in {FAST_WINDOW}s, waiting {LONG_DELAY}s")
            time.sleep(LONG_DELAY)
            crash_times.clear()
        else:
            time.sleep(RESTART_DELAY)


if __name__ == "__main__":
    main()
