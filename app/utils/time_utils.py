def format_seconds_hh_mm_ss(seconds: float) -> str:
    """Format seconds as mm:ss when under 1 hour, else hh:mm:ss."""
    if seconds < 0:
        seconds = 0.0
    total = int(round(seconds))
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
