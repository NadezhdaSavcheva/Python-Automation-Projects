from pathlib import Path
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

WATCH_DIR = (Path.home() / "Downloads").expanduser().resolve()

class NewDownloadHandler(FileSystemEventHandler):
    def on_created(self, event):
        if isinstance(event, FileCreatedEvent):
            logging.info(f"NEW: {event.src_path}")

    def on_moved(self, event):
        if isinstance(event, FileMovedEvent):
            logging.info(f"MOVED/RENAMED: {event.src_path} -> {event.dest_path}")

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
