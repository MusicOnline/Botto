import re
import sys
import traceback
from typing import Any, Optional, Tuple, Union

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


def hidden_format_exc(
    error: Optional[Exception] = None, limit: Optional[int] = None, chain: bool = True
) -> str:
    """Hide half of the directory path in the traceback."""
    if error is None:
        exc_info = sys.exc_info()
    else:
        exc_info = (type(error), error, error.__traceback__)
    lines = traceback.format_exception(*exc_info, limit, chain)
    hidden_traceback = []
    pattern_1 = r'File ".*([\\/])(Botto.+)"'
    pattern_2 = r'File ".*([\\/])(Python\d\d-\d\d.+)"'
    for line in lines:
        if re.search(pattern_1, line):
            hidden_traceback.append(re.sub(pattern_1, r'File "C:\1...\1\2"', line))
        elif re.search(pattern_2, line):
            hidden_traceback.append(re.sub(pattern_2, r'File "C:\1...\1\2"', line))
        else:
            hidden_traceback.append(line)
    return "".join(hidden_traceback)


def limit_str(string: Any, limit: int) -> str:
    """Add ellipsis to the end of string if it is longer than limit."""
    string = str(string)
    if len(string) > limit:
        return string[: limit - 3] + "..."
    return string


def is_too_long_err(error: Exception) -> Optional[Tuple[str, int]]:
    """Check if error is caused by message body too long.

    Return a tuple of the message body type and length limit if True,
    otherwise return False.
    """
    pattern = r"In (.+?): Must be (\d+) or fewer in length\."
    match = re.search(pattern, str(error))
    if match:
        return (match.group(1), int(match.group(2)))
    return None
