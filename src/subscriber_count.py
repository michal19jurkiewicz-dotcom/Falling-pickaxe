import re
import threading
import time
import urllib.request

MIN_BACKOFF_SECONDS = 10
MAX_BACKOFF_SECONDS = 120

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# The public channel page embeds this field in its inline JSON (ytInitialData)
# regardless of whether the channel is displayed as a numeric or "1.2K"-style
# count - no login, API key, or quota needed to read it.
_PATTERNS = [
    # Current channel-page format: the count sits in a generic
    # contentMetadataViewModel -> metadataRows -> metadataParts "text.content"
    # field, so it's matched together with its adjacent accessibilityLabel
    # (which spells out "subscriber") to avoid false-matching unrelated
    # "content" strings, e.g. the channel description.
    re.compile(r'"text":\s*\{\s*"content":\s*"([^"]+)"\s*\}\s*,\s*"accessibilityLabel":\s*"[^"]*subscriber'),
    # Older channel-page format, kept as a fallback.
    re.compile(r'"subscriberCountText":\s*\{\s*"simpleText":\s*"([^"]+)"'),
    re.compile(r'"subscriberCountText":\s*\{\s*"accessibility":\s*\{\s*"accessibilityData":\s*\{\s*"label":\s*"([^"]+)"'),
    # Current /about-page format: same field, but a flat string instead of a
    # nested {"simpleText": ...} object.
    re.compile(r'"subscriberCountText":\s*"([^"]+)"'),
]


class SubscriberCountWatcher:
    """Polls a YouTube channel's public "About" page for its current
    displayed subscriber count. This is a free, no-API-key alternative to
    the official Data API - it reads the same number shown on the channel
    page, which YouTube itself rounds for channels above ~1000 subscribers.

    This is intentionally separate from SubscriberWatcher: that one reports
    individual new-subscriber EVENTS via StreamElements; this one reports the
    channel's current TOTAL count, purely as an optional HUD readout.
    """

    def __init__(self, channel_url, poll_interval_seconds=60):
        self.channel_url = self._normalize_url(channel_url)
        self.poll_interval_seconds = max(20, poll_interval_seconds)
        self._stop_event = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self._latest_text = None

    @staticmethod
    def _normalize_url(channel_url):
        channel_url = (channel_url or "").strip()
        if not channel_url:
            return None
        if channel_url.startswith("@"):
            return f"https://www.youtube.com/{channel_url}"
        if not channel_url.startswith("http"):
            return f"https://www.youtube.com/{channel_url}"
        return channel_url

    def start(self):
        if not self.channel_url:
            print("[subs-count] No channel URL/handle configured, not starting.")
            return self
        self._thread = threading.Thread(target=self._run, daemon=True, name="subscriber-count-watcher")
        self._thread.start()
        return self

    def stop(self):
        self._stop_event.set()

    def get_text(self):
        """Latest known subscriber-count text (e.g. "12.3K subscribers"), or None."""
        with self._lock:
            return self._latest_text

    def _fetch_once(self):
        request = urllib.request.Request(self.channel_url, headers={"User-Agent": _USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
        with urllib.request.urlopen(request, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")

        for pattern in _PATTERNS:
            match = pattern.search(html)
            if match:
                return match.group(1)
        return None

    def _run(self):
        backoff = MIN_BACKOFF_SECONDS

        while not self._stop_event.is_set():
            fetch_ok = False
            try:
                text = self._fetch_once()
                if text:
                    with self._lock:
                        self._latest_text = text
                    print(f"[subs-count] Current subscriber count: {text}")
                    fetch_ok = True
                else:
                    print("[subs-count] Could not find subscriber count on channel page.")
            except Exception as e:
                print(f"[subs-count] Fetch failed: {e}")

            if fetch_ok:
                backoff = MIN_BACKOFF_SECONDS
                wait_seconds = self.poll_interval_seconds
            else:
                wait_seconds = backoff
                backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)

            if self._stop_event.wait(wait_seconds):
                break
