# File Downloads Automator

A small Python script that watches your Downloads folder in real time and automatically moves newly created files into category folders (images, videos, docs, etc.).
It waits until downloads finish, skips temporary browser files, and avoids overwriting by renaming to name (1).ext.

---

## Features

- Real-time watch (processes only files that appear after start)
- Stable-download detection (STABLE_SECONDS + timeout)
- Skips .crdownload, .part, .tmp and MS Office temp files (~$...)
- Categorizes by extension (images/videos/audio/docs/archives/apps/other)
- Safe renaming on conflicts: name (1).ext, name (2).ext, …
- Works on Windows, macOS, and Linux

---

## Requirements

- Python 3.8+
- Dependency: watchdog
   ```bash
   python -m pip install watchdog
   ```

---

## Quick Start

1. Install the dependency (above).
2. Run the script:
   ```bash
   python fileDownloadsAutomator.py
   ```
3. Stop anytime with Ctrl + C.
> By default it watches ~/Downloads. Only files created/finished after the script starts are moved.

---

## Important: Handler initialization

Your event handler class requires the watch directory in its constructor:
   ```python
   class NewDownloadHandler(FileSystemEventHandler):
       def __init__(self, watch_dir: Path):
           ...
   ```


So in `main()` you must create it with `WATCH_DIR`:

   ```python
   observer = Observer()
   observer.schedule(NewDownloadHandler(WATCH_DIR), path=str(WATCH_DIR), recursive=False)
   ```


If you see `NewDownloadHandler()` without an argument, add `WATCH_DIR`.

---

## Configuration

Edit constants at the top of `fileDownloadsAutomator.py`:
- `WATCH_DIR` – folder to watch (default: `~/Downloads`).
- `DEST` – destination folders for each category. \
Folders are created automatically when needed.
- `EXT` – extensions per category (lowercase, without the dot).
- `IGNORE_SUFFIXES` – temporary suffixes to skip during downloads.
- `STABLE_SECONDS` – how long a file size must remain unchanged before moving (e.g., `4` is safe).
- `MAX_WAIT_SECONDS` – upper bound for stability wait to avoid hanging on never-ending downloads.

---

## How it works

- Listens to `on_created` and `on_moved` (browsers often do `*.crdownload → final.ext`).
- Processes only files directly inside the watched folder (no subdirectories).
- Ignores temporary/partial files and Office temp files.
- Waits for the file to become “stable” (size unchanged for `STABLE_SECONDS`).
- Classifies by extension and moves to the corresponding destination.
- Renames if a file with the same name already exists.

---

## Run on Login / Startup

**Windows (Task Scheduler):**
1. Open Task Scheduler → Create Task.
2. Triggers: At log on.
3. Actions: *Start a program* → `python` with the script path as argument.
4. Optional: adjust Conditions/Settings to your liking.

**Linux (systemd user service)**
Create `~/.config/systemd/user/file-downloads-automator.service`:
```ini
[Unit]
Description=Move new Downloads by category

[Service]
ExecStart=/usr/bin/python /PATH/TO/fileDownloadsAutomator.py
Restart=always

[Install]
WantedBy=default.target
```

Then:
```bash
systemctl --user daemon-reload
systemctl --user enable --now file-downloads-automator.service
```

**macOS (launchd)**
Create `~/Library/LaunchAgents/com.you.file-downloads-automator.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.you.file-downloads-automator</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/PATH/TO/fileDownloadsAutomator.py</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/file-downloads-automator.out</string>
  <key>StandardErrorPath</key><string>/tmp/file-downloads-automator.err</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.you.file-downloads-automator.plist
```

---

## Troubleshooting

- Nothing happens: \
Make sure you construct the handler with NewDownloadHandler(WATCH_DIR) and that WATCH_DIR exists.
- File never moves: \
It may still be downloading; raise STABLE_SECONDS or check if the file uses a temp suffix being ignored.
- PermissionError: \
Another process (AV indexer, backup) may lock the file. Try again after a moment or adjust security settings.
- Moved an old file to Downloads and it moved it: \
That’s expected—moving an existing file into the watched folder raises a new event.
