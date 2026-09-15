import re
from urllib.parse import parse_qs, urlparse


_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def validate_live_stream_id(input_string):
    """Return the YouTube video ID from a live, Shorts, or watch URL.

    YouTube live streams can be shared as ``/live/ID``, ``/watch?v=ID``,
    ``/shorts/ID`` or ``youtu.be/ID``.  The Shorts form is important here:
    YouTube often presents vertical live streams using that route.
    """
    if not input_string:
        return None

    value = input_string.strip()
    if _VIDEO_ID_RE.fullmatch(value):
        return value

    candidate = value if "://" in value else f"https://{value}"
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None

    host = parsed.netloc.lower().split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    if host not in {"youtube.com", "m.youtube.com", "youtu.be"}:
        print(f"Failed to extract YouTube ID from string: {input_string}")
        return None

    if host == "youtu.be":
        path_id = parsed.path.strip("/").split("/")[0]
    else:
        parts = [part for part in parsed.path.split("/") if part]
        path_id = parts[1] if len(parts) >= 2 and parts[0].lower() in {"live", "shorts", "embed"} else ""
        path_id = path_id or parse_qs(parsed.query).get("v", [""])[0]

    if _VIDEO_ID_RE.fullmatch(path_id):
        return path_id

    print(f"Failed to extract YouTube ID from string: {input_string}")
    return None
