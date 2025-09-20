from pathlib import Path
from shutil import move
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

# Settings
WATCH_DIR = (Path.home() / "Downloads").expanduser().resolve()

DEST = {
    "images": Path.home() / "Pictures/Incoming",
    "videos": Path.home() / "Videos/Incoming",
    "audio":  Path.home() / "Music/Incoming",
    "docs":   Path.home() / "Documents/Incoming",
    "archives": Path.home() / "Archives",
    "apps": Path.home() / "Apps",
    "other": Path.home() / "Other",
}

# Extensions without the dot, lowercase
EXT = {
    "images":   {"jpg","jpeg","png","gif","webp","heic","bmp","tiff","svg"},
    "videos":   {"mp4","mov","mkv","webm","avi","m4v"},
    "audio":    {"mp3","wav","flac","m4a","aac","ogg"},
    "docs":     {"pdf","doc","docx","xls","xlsx","ppt","pptx","txt","md","csv","odt","ods"},
    "archives": {"zip","rar","7z","tar","gz","bz2"},
    "apps":     {"exe","msi","dmg","pkg","deb","rpm","apk"},
}

IGNORE_SUFFIXES = (".part", ".crdownload", ".tmp")    # Browser temp files during download
STABLE_SECONDS = 4            # Seconds of unchanged size before moving
MAX_WAIT_SECONDS = 600        # Max time to wait for a file to become stable

# Helpers
def category_for(path: Path) -> str:
    ext = path.suffix.lower().lstrip(".")
    for cat, exts in EXT.items():
        if ext in exts:
            return cat
    return "other"

def unique_target(dest_dir: Path, name: str) -> Path:
    base = Path(name).stem
    ext = Path(name).suffix
    i, candidate = 1, dest_dir / name
    while candidate.exists():
        candidate = dest_dir / f"{base} ({i}){ext}"
        i += 1
    return candidate

def _file_exists_retry(p: Path, tries: int = 3, delay: float = 0.2) -> bool:
    for _ in range(tries):
        if p.exists():
            return True
        time.sleep(delay)
    return False

def wait_until_stable(p: Path, stable_seconds: int, max_wait: int) -> bool:
    """Wait until file size stays unchanged for `stable_seconds`, with an upper bound of `max_wait`."""
    if not _file_exists_retry(p):
        return False
    same_for = 0
    last = -1
    waited = 0
    while waited <= max_wait:
        try:
            if not p.is_file():    # May have disappeared or be a directory
                return False
            size = p.stat().st_size
        except FileNotFoundError:
            return False
            
        if size == last:
            same_for += 1
            if same_for >= stable_seconds:
                return True
        else:
            same_for = 0
            last = size
            
        time.sleep(1)
        waited += 1
    return False    # Timeout

def move_file(p: Path):
    cat = category_for(p)
    dest_dir = DEST.get(cat, DEST["other"]).expanduser().resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = unique_target(dest_dir, p.name)
    move(str(p), str(target))
    logging.info(f"Moved: {p.name} -> {target}")

# Event handler
class NewDownloadHandler(FileSystemEventHandler):
    def __init__(self, watch_dir: Path):
        super().__init__()
        self.watch_dir = watch_dir

    def _is_in_watch(self, path: Path) -> bool:
        try:
            return path.parent.resolve() == self.watch_dir
        except Exception:
            return False

    def _should_ignore(self, path: Path) -> bool:
        s = str(path).lower()
        if not _file_exists_retry(path):
            return True
        # for a brief moment it may not be a "file"; the retry above helps
        if not path.is_file():
            return True
        if any(s.endswith(suf) for suf in (x.lower() for x in IGNORE_SUFFIXES)):
            return True
        if path.name.startswith("~$"):  # temporary MS Office files
            return True
        return False

    def _process(self, path: Path):
        # process only events for files directly inside the watch folder (no subdirs)
        if not self._is_in_watch(path):
            return
        if self._should_ignore(path):
            return
        if wait_until_stable(path, STABLE_SECONDS, MAX_WAIT_SECONDS):
            try:
                move_file(path)
            except Exception as e:
                logging.error(f"Error moving {path}: {e}")
        else:
            logging.warning(f"Skipping (not stable within timeout): {path}")

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent):
            self._process(Path(event.src_path))

    def on_moved(self, event):
        # browsers often do: *.crdownload -> final.ext (in the same folder)
        if isinstance(event, FileMovedEvent):
            self._process(Path(event.dest_path))

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )
    
    if not WATCH_DIR.exists():
        raise SystemExit(f"No such folder to watch: {WATCH_DIR}")
        
    logging.info(f"Watching NEW files in: {WATCH_DIR}")
    observer = Observer()
    observer.schedule(NewDownloadHandler(), path=str(WATCH_DIR), recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopping...")
    finally:
        observer.stop()
        observer.join()

if __name__ == "__main__":
    main()
