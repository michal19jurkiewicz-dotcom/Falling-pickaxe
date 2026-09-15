import re


def validate_live_stream_id(input_string):
    """
    Extracts video ID from YouTube URL or returns the string as is if it's already an ID.

    Supported formats:
    - https://www.youtube.com/watch?v=uvubgYqg9VQ
    - https://www.youtube.com/live/uvubgYqg9VQ?si=dfmI1IOGu4NRlxtM
    - https://youtu.be/uvubgYqg9VQ
    - uvubgYqg9VQ (direct ID)

    Args:
        input_string (str): YouTube video URL or ID

    Returns:
        str: Extracted video ID or None if extraction failed
    """
    if not input_string:
        return None

    # Patterns for different YouTube URL formats
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtube\.com/live/)([a-zA-Z0-9_-]{11})',  # watch?v= or live/
        r'youtu\.be/([a-zA-Z0-9_-]{11})',  # youtu.be/
        r'^([a-zA-Z0-9_-]{11})$'  # Direct ID (11 characters)
    ]

    for pattern in patterns:
        match = re.search(pattern, input_string)
        if match:
            return match.group(1)

    # If nothing found, return None
    print(f"Failed to extract ID from string: {input_string}")
    return None
