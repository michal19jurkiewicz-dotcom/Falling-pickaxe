import json
import queue
import threading
import time
import uuid

import websocket

ASTRO_URL = "wss://astro.streamelements.com"

MIN_BACKOFF_SECONDS = 5
MAX_BACKOFF_SECONDS = 60


class SubscriberWatcher:
    """Listens for new-subscriber events on a YouTube channel through
    StreamElements' free real-time "Astro" websocket - the same feed
    StreamElements itself uses to trigger on-stream subscriber alerts.

    This avoids the YouTube Data API entirely: no API key, no quota, and no
    rounding of the subscriber count (YouTube only exposes an exact count
    through its own paid-quota API; the public channel page rounds it for
    channels with more than ~1000 subscribers). StreamElements gets told
    about each individual subscription as it happens, so this reports exact
    events instead of polling for a count difference.

    Requires a free StreamElements account with the YouTube channel linked,
    and the channel's JWT token (Account -> Channels in the StreamElements
    dashboard).
    """

    def __init__(self, channel_id, jwt_token):
        self.channel_id = channel_id
        self.jwt_token = jwt_token
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread = None
        self._ws = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="subscriber-watcher")
        self._thread.start()
        return self

    def stop(self):
        self._stop_event.set()
        try:
            if self._ws is not None:
                self._ws.close()
        except Exception:
            pass

    def drain(self):
        """Return all new-subscriber events received since the last call (non-blocking)."""
        events = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events

    def _on_message(self, ws, raw):
        try:
            message = json.loads(raw)
        except (TypeError, ValueError):
            return

        message_type = message.get("type")

        if message_type == "welcome":
            ws.send(json.dumps({
                "type": "subscribe",
                "nonce": str(uuid.uuid4()),
                "data": {
                    "topic": "channel.activities",
                    "room": self.channel_id,
                    "token": self.jwt_token,
                    "token_type": "jwt",
                },
            }))
            print("[subs] Connected to StreamElements. Listening for new YouTube subscribers...")
            return

        if message_type != "message" or message.get("topic") != "channel.activities":
            return

        activity = message.get("data") or {}
        if activity.get("type") == "subscriber" and activity.get("provider") == "youtube":
            print("[subs] New subscriber detected")
            self._queue.put("New Subscriber")

    def _on_error(self, ws, error):
        print(f"[subs] Websocket error: {error}")

    def _run(self):
        backoff = MIN_BACKOFF_SECONDS

        while not self._stop_event.is_set():
            try:
                self._ws = websocket.WebSocketApp(
                    ASTRO_URL,
                    on_message=self._on_message,
                    on_error=self._on_error,
                )
                # run_forever blocks until the connection closes or errors out
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                print(f"[subs] Unexpected websocket error: {e}")

            if self._stop_event.is_set():
                break

            print(f"[subs] Disconnected from StreamElements. Reconnecting in {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
