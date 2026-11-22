"""Retain complete conversation turns within the configured history limit."""
from langchain_core.messages import HumanMessage
from core.config import settings


def trim_history(messages):
    starts = [i for i, message in enumerate(messages) if isinstance(message, HumanMessage)]
    if len(starts) > settings.MAX_HISTORY_TURNS:
        return messages[starts[-settings.MAX_HISTORY_TURNS]:]
    return messages
