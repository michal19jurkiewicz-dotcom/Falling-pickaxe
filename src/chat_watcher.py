import queue
import threading
import time
from datetime import datetime

import requests
from chat_downloader import ChatDownloader
from chat_downloader.errors import ChatDownloaderError, ParsingError
from chat_downloader.sites.youtube import YouTubeChatDownloader

# Message types chat-downloader uses for YouTube superchats/superstickers
SUPERCHAT_TYPE = "paid_message"
SUPERSTICKER_TYPE = "paid_sticker"

MIN_BACKOFF_SECONDS = 5
MAX_BACKOFF_SECONDS = 60

# chat-downloader (last released 2022) only recognises the *classic* watch-page
# template, where the data is inlined directly into a JS assignment:
#   ytInitialData = {...};
# YouTube now serves an alternate template for a portion of requests, where
# the same data instead sits in a dedicated JSON-typed <script> tag and gets
# assigned via JS at runtime:
#   <script id="yt-initial-data" type="application/json">{...}</script>
#   ...
#   var ytDataEl = document.getElementById('yt-initial-data');
#   window['ytInitialData'] = JSON.parse(ytDataEl.textContent);
# chat-downloader's regex never matches that second template, and unlike most
# of its other failure modes this one is NOT retried internally - it's raised
# straight away as an unretryable ParsingError ("Unable to parse initial video
# data"), which is what intermittently broke the chat connection here (roughly
# every 1 in 10 requests hit this template in testing). Patching the regex to
# also recognise the JSON-script-tag form fixes it at the source, for every
# caller of chat_downloader in this process.
YouTubeChatDownloader._YT_INITIAL_DATA_RE = (
    r'(?:'
    r'(?:window\s*\[\s*["\']ytInitialData["\']\s*\]|ytInitialData)\s*=\s*'
    r'|'
    r'<script[^>]+id=["\']yt-initial-data["\'][^>]*>'
    r')'
    r'({.+?})'
    r'(?:'
    r'\s*;' + YouTubeChatDownloader._YT_INITIAL_BOUNDARY_RE +
    r'|'
    r'</script'
    r')'
)


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
        """Fetch the watch page and start the chat generator, retrying a
        handful of times close together first. chat-downloader treats a 200
        response that's missing the embedded page data ("Unable to parse
        initial video data") as an unretryable fatal error - it does NOT
        retry that case internally despite its own max_attempts setting -
        even though, empirically, that specific response from YouTube is a
        transient blip most of the time (a fresh attempt secs later usually
        works). Clearing it here, close together, avoids surfacing it to the
        caller's much slower backoff and dropping chat messages for a full
        backoff cycle every time it happens.
        """
        attempts, retry_delay_seconds = 4, 2
        last_error = None
        for attempt in range(1, attempts + 1):
            print(f"[chat] Connecting to YouTube live chat (attempt {attempt}/{attempts})...")
            try:
                chat = ChatDownloader(cookies=self.cookies_file).get_chat(self.video_id)
                iterator = iter(chat)
                first_item = next(iterator, None)
                return first_item, iterator
            except ChatDownloaderError as e:
                last_error = e
                if isinstance(e, ParsingError) and attempt < attempts:
                    time.sleep(retry_delay_seconds)
                else:
                    raise
        raise last_error

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

        is_superchat = message_type == SUPERCHAT_TYPE
        is_supersticker = message_type == SUPERSTICKER_TYPE
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
