"""Normalize LLM-produced question lists to 5–8 unique, non-empty strings."""

_MAX_QUESTIONS = 8
_MIN_QUESTIONS = 5

_FILLERS: tuple[str, ...] = (
    "What is the main idea the speaker is explaining?",
    "What example or detail does the video emphasize?",
    "How do the ideas in this video connect to each other?",
    "What practical takeaway does the speaker suggest?",
)


def normalize_suggested_questions(questions: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in questions:
        t = " ".join(q.split()).strip()
        if not t or len(t) > 400:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
        if len(out) >= _MAX_QUESTIONS:
            return out

    for filler in _FILLERS:
        if len(out) >= _MIN_QUESTIONS:
            break
        k = filler.lower()
        if k not in seen:
            seen.add(k)
            out.append(filler)

    i = 0
    while len(out) < _MIN_QUESTIONS:
        i += 1
        extra = f"What other idea from the video is worth exploring? ({i})"
        key = extra.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(extra)

    return out[:_MAX_QUESTIONS]
