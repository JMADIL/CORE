"""Recognize requests that need a media-generation provider, not just prose."""
import re

_MEDIA = re.compile(
    r"\b(?:generate|create|make|edit|animate|synthesize|convert)\b.{0,120}"
    r"\b(?:images?|pictures?|pics?|photos?|photographs?|illustrations?|drawings?|portraits?|videos?|speech|sound effects?|voiceovers?|audio|music|songs?|soundtracks?)\b"
    r"|\b(?:draw|paint|illustrate)\b|\bread\b.{0,100}\baloud\b"
    r"|\b(?:tts|text[ -]to[ -]speech)\b",
    re.I | re.S,
)
_PROMPT_ONLY = re.compile(
    r"\b(?:write|draft|generate|create|improve|suggest|give me)\s+"
    r"(?:(?:me|a|an|some|the|better|detailed)\s+){0,4}prompts?\b", re.I,
)


def requests_media(query: str) -> bool:
    return bool(_MEDIA.search(query) and not _PROMPT_ONLY.search(query))
