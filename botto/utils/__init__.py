import random
import re
import sys
import traceback
from typing import Any, List, Match, Optional, Tuple, Union

import discord

from .paginator import EmbedPaginator

AnyChannel = Union[
    discord.TextChannel,
    discord.VoiceChannel,
    discord.CategoryChannel,
    discord.DMChannel,
    discord.GroupChannel,
]

OptionalChannel = Optional[AnyChannel]


def limit_str(string: Any, limit: int) -> str:
    """Add ellipsis to the end of string if it is longer than limit."""
    _string: str = str(string)
    if len(_string) > limit:
        return _string[: limit - 3] + "..."
    return _string


def is_too_long_err(error: Exception) -> Optional[Tuple[str, int]]:
    """Check if error is caused by message body too long.

    Return a tuple of the message body type and length limit if True,
    otherwise return None.
    """
    pattern: str = r"In (.+?): Must be (\d+) or fewer in length\."
    match: Optional[Match] = re.search(pattern, str(error))
    if match:
        return (match.group(1), int(match.group(2)))
    return None


def is_conversion_err(error: Exception) -> Optional[Tuple[str, int]]:
    """Check if error is caused by generic conversion error.

    Return a tuple of the converter type and parameter name if True,
    otherwise return None.
    """
    pattern: str = r'Converting to "(.+?)" failed for parameter "(.+?)"\.'
    match: Optional[Match] = re.search(pattern, str(error))
    if match:
        return (match.group(1), match.group(2))
    return None


def get_random_color() -> discord.Color:
    """Get a color with random hue, full saturation and value."""
    return discord.Color.from_hsv(random.random(), 1, 1)
