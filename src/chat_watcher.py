import http.cookiejar
import queue
import threading
import time
from datetime import datetime
from pathlib import Path

import httpx
import requests
import pytchat

# Message types exposed by pytchat-ng for paid messages.
SUPERCHAT_TYPE = "superChat"
SUPERSTICKER_TYPE = "membershipItem"


class ChatBackendError(RuntimeError):
    """Raised when pytchat cannot open or maintain a live-chat session."""


def _load_cookies(cookie_path):
    if not cookie_path:
        return {}
    path = Path(cookie_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"YouTube cookies file not found: {path}")
    jar = http.cookiejar.MozillaCookieJar(str(path))
    jar.load(ignore_discard=True, ignore_expires=True)
    return {cookie.name: cookie.value for cookie in jar}


class _PytchatIterator:
    def __init__(self, video_id, cookies_file=None):
        client = httpx.Client(http2=True, cookies=_load_cookies(cookies_file), timeout=20.0)
        self.chat = pytchat.create(video_id=video_id, client=client)

    def __iter__(self):
        return self

    def __next__(self):
        while self.chat.is_alive():
            batch = self.chat.get()
            for item in batch.sync_items():
                return {
                    "author": {"name": getattr(item.author, "name", "Unknown")},
                    "message": getattr(item, "message", ""),
                    "message_type": getattr(item, "type", "textMessage"),
                    "money": {"text": getattr(item, "amountString", "N/A")},
                    "timestamp": _timestamp_microseconds(getattr(item, "datetime", None)),
                }
            time.sleep(0.25)
        raise StopIteration


def _timestamp_microseconds(value):
    if not value:
        return None
    try:
        return int(datetime.strptime(value, "%Y-%m-%d %H:%M:%S").timestamp() * 1_000_000)
    except (TypeError, ValueError):
        return None


class ChatDownloaderError(ChatBackendError):
    pass


class ParsingError(ChatBackendError):
    pass


SUPERCHAT_TYPE_ALIASES = {SUPERCHAT_TYPE, "paidMessage"}
SUPERSTICKER_TYPE_ALIASES = {SUPERSTICKER_TYPE, "paidSticker"}

# The old chat-downloader package relied on a page scraper which YouTube now
# frequently answers with a recaptcha page. pytchat-ng uses the live-chat
# continuation endpoint directly and is therefore much more reliable here.

MIN_BACKOFF_SECONDS = 5
MAX_BACKOFF_SECONDS = 60


class ChatWatcher:
    """Reads a YouTube live chat continuously in a background thread using
    chat-downloader, which reads the same public endpoints the live chat
    webpage itself uses. No API key and no quota involved.

    The watcher never stops on its own: if the stream isn't live yet, or the
    connection drops mid-stream, it backs off and keeps retrying so it can
    survive multi-hour, unattended livestreams.
    """

    def __init__(self, video_id, log_dir=None, cookies_file=None):
        self.video_id = video_id
        self.log_dir = log_dir
        self.cookies_file = cookies_file
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = None
        self._log_date = None
        self._log_file = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="chat-watcher")
        self._thread.start()
        return self

    def stop(self):
        self._stop_event.set()

    def drain(self):
        """Return all chat messages received since the last call (non-blocking)."""
        messages = []
        while True:
            try:
                messages.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return messages

    def _log(self, line):
        if self.log_dir is None:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._log_date:
            self._log_date = today
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._log_file = self.log_dir / f"chat_{today}.txt"

        try:
            with open(self._log_file, "a", encoding="utf-8") as chat_file:
                chat_file.write(line + "\n")
        except OSError as e:
            print(f"[chat] Failed to write chat log: {e}")

    def _log_parsing_diagnostics(self):
        """chat-downloader's own "Unable to parse initial video data" error
        gives no clue why the page didn't contain what it expected. Do one
        extra, independent fetch of the watch page here and report its
        status code and a few well-known markers (bot-check pages, region
        blocks, etc.) - without dumping the ~1MB of HTML - so a persistent
        failure can be told apart from an occasional transient hiccup."""
        try:
            url = f"https://www.youtube.com/watch?v={self.video_id}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
            response = requests.get(url, headers=headers, timeout=15)
            html = response.text
            markers = [text for text in (
                "Video unavailable", "unusual traffic", "systems have detected",
                "consent.youtube.com", "Sign in to confirm", "recaptcha",
            ) if text in html]
            print(f"[chat] Diagnostic: status={response.status_code} length={len(html)} "
                  f"has_ytInitialData={'ytInitialData' in html} markers={markers or 'none'}")
        except Exception as diag_error:
            print(f"[chat] Diagnostic fetch also failed: {diag_error}")

    def _connect(self):
        """Open YouTube's live-chat continuation stream through pytchat-ng."""
        attempts, retry_delay_seconds = 4, 2
        last_error = None
        for attempt in range(1, attempts + 1):
            print(f"[chat] Connecting to YouTube live chat (attempt {attempt}/{attempts})...")
            try:
                iterator = iter(_PytchatIterator(self.video_id, self.cookies_file))
                first_item = next(iterator, None)
                return first_item, iterator
            except Exception as error:
                if "LOGIN_REQUIRED" in str(error) or "Sign in to confirm" in str(error):
                    raise ChatBackendError(
                        "YouTube wymaga logowania dla tej transmisji. "
                        "Ustaw YOUTUBE_COOKIES_FILE na plik cookies.txt z zalogowanej przeglądarki."
                    ) from error
                last_error = error
                if attempt < attempts:
                    time.sleep(retry_delay_seconds)
        raise ChatBackendError(str(last_error)) from last_error

    def _run(self):
        backoff = MIN_BACKOFF_SECONDS

        while not self._stop_event.is_set():
            try:
                first_item, iterator = self._connect()
                backoff = MIN_BACKOFF_SECONDS
                print("[chat] Connected. Listening for messages...")

                if first_item is not None:
                    try:
                        self._handle_item(first_item)
                    except Exception as e:
                        print(f"[chat] Failed to process a message: {e}")

                for item in iterator:
                    if self._stop_event.is_set():
                        break
                    try:
                        self._handle_item(item)
                    except Exception as e:
                        # Never let a single malformed message kill the whole watcher
                        print(f"[chat] Failed to process a message: {e}")

            except ChatDownloaderError as e:
                print(f"[chat] Chat unavailable right now ({e}). Retrying in {backoff}s...")
                if isinstance(e, ParsingError):
                    self._log_parsing_diagnostics()
            except Exception as e:
                print(f"[chat] Unexpected chat error: {e}. Retrying in {backoff}s...")

            if self._stop_event.is_set():
                break

            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)

    def _handle_item(self, item):
        author = (item.get("author") or {}).get("name") or "Unknown"
        text = item.get("message") or ""
        message_type = item.get("message_type")
        money = item.get("money")

        timestamp_usec = item.get("timestamp")
        if timestamp_usec:
            timestamp = datetime.fromtimestamp(timestamp_usec / 1_000_000).strftime("%Y-%m-%d %H:%M:%S")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        is_superchat = message_type in SUPERCHAT_TYPE_ALIASES
        is_supersticker = message_type in SUPERSTICKER_TYPE_ALIASES
        amount = money.get("text", "N/A") if money else "N/A"

        if is_superchat:
            log_line = f"[{timestamp}] Super Chat from {author} ({amount}): {text}"
        elif is_supersticker:
            log_line = f"[{timestamp}] Super Sticker from {author} ({amount}): {text}"
        else:
            log_line = f"[{timestamp}] {author}: {text}"

        self._log(log_line)

        self._queue.put({
            "timestamp": timestamp,
            "author": author,
            "message": text,
            "is_superchat": is_superchat,
            "is_supersticker": is_supersticker,
        })
