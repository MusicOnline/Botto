import re
import sys
import traceback
from typing import Any, List, Match, Optional, Tuple, Union

import discord  # type: ignore

from .paginator import EmbedPaginator

OptionalChannel = Union[
    discord.TextChannel,
    discord.VoiceChannel,
    discord.CategoryChannel,
    discord.DMChannel,
    discord.GroupChannel,
    None,
]


def limit_str(string: Any, limit: int) -> str:
    """Add ellipsis to the end of string if it is longer than limit."""
    _string: str = str(string)
    if len(_string) > limit:
        return _string[: limit - 3] + "..."
    return _string


def is_too_long_err(error: Exception) -> Optional[Tuple[str, int]]:
    """Check if error is caused by message body too long.

    Return a tuple of the message body type and length limit if True,
    otherwise return False.
    """
    pattern: str = r"In (.+?): Must be (\d+) or fewer in length\."
    match: Optional[Match] = re.search(pattern, str(error))
    if match:
        return (match.group(1), int(match.group(2)))
    return None
