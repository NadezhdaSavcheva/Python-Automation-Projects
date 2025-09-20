from pathlib import Path
from shutil import move
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

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

EXT = {
    "images":   {"jpg","jpeg","png","gif","webp","heic","bmp","tiff","svg"},
    "videos":   {"mp4","mov","mkv","webm","avi","m4v"},
    "audio":    {"mp3","wav","flac","m4a","aac","ogg"},
    "docs":     {"pdf","doc","docx","xls","xlsx","ppt","pptx","txt","md","csv","odt","ods"},
    "archives": {"zip","rar","7z","tar","gz","bz2"},
    "apps":     {"exe","msi","dmg","pkg","deb","rpm","apk"},
}

IGNORE_SUFFIXES = (".part", ".crdownload", ".tmp")
STABLE_SECONDS = 2

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

def move_file(p: Path):
    cat = category_for(p)
    dest_dir = DEST.get(cat, DEST["other"]).expanduser().resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = unique_target(dest_dir, p.name)
    move(str(p), str(target))
    logging.info(f"Moved: {p.name} -> {target}")

def should_ignore(path: Path) -> bool:
    s = str(path).lower()
    if not path.exists() or not path.is_file():
        return True
    if any(s.endswith(suf) for suf in IGNORE_SUFFIXES):
        return True
    if path.name.startswith("~$"):
        return True
    return False

def wait_until_stable(p: Path, stable_seconds: int) -> bool:
    same_for = 0
    last = -1
    while True:
        try:
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

class NewDownloadHandler(FileSystemEventHandler):
    def _is_in_watch(self, path: Path) -> bool:
        try:
            return path.parent.resolve() == WATCH_DIR
        except Exception:
            return False

    def _process(self, p: Path):
        if not self._is_in_watch(p):
            return
        if should_ignore(p):
            return
        if wait_until_stable(p, STABLE_SECONDS):
            move_file(p)

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent):
            self._process(Path(event.src_path))

    def on_moved(self, event):
        if isinstance(event, FileMovedEvent):
            self._process(Path(event.dest_path))

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    if not WATCH_DIR.exists():
        raise SystemExit(f"No such folder to watch: {WATCH_DIR}")
    logging.info(f"Watching for new files in: {WATCH_DIR}")
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
