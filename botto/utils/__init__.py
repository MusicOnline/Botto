import random
import re
import sys
import traceback
from typing import Any, Dict, List, Match, Optional, Tuple, Union

import aiohttp
import discord

from botto import config
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


async def hastebin(
    content: str,
    *,
    create_url: str = config["HASTEBIN_CREATE_URL"],
    paste_url: str = config["HASTEBIN_PASTE_URL"],
    session: Optional[aiohttp.ClientSession] = None,
) -> str:
    """Create a Hastebin-like paste and return the URL."""
    if not create_url or not paste_url:
        raise ValueError("No Hastebin-like URL provided.")
    session = session or aiohttp.ClientSession()
    async with session.post(create_url, data=content.encode("utf-8")) as resp:
        response = await resp.json()
        return paste_url.format(key=response["key"])


async def gist(
    *files: Tuple[str, str],
    description: Optional[str] = None,
    public: bool = False,
    github_token: str = config["GITHUB_TOKEN"],
    session: Optional[aiohttp.ClientSession] = None,
) -> str:
    """Create a GitHub gist and return the URL."""
    if not github_token:
        raise ValueError("No GitHub token provided.")

    url: str = "https://api.github.com/gists"
    headers: Dict[str, str] = {"Authorization": f"token {github_token}"}
    files_dict: Dict[str, Dict[str, str]] = {file[0]: {"content": file[1]} for file in files}

    data: dict = {"files": files_dict, "public": public}
    if description is not None:
        data.update(description=description)

    session = session or aiohttp.ClientSession()
    async with session.post(url, headers=headers, json=data) as resp:
        response = await resp.json()
        return response["html_url"]


async def try_hastebin_then_gist(
    content: str,
    *,
    create_url: str = config["HASTEBIN_CREATE_URL"],
    paste_url: str = config["HASTEBIN_PASTE_URL"],
    filename: str = "content.txt",
    description: Optional[str] = None,
    public: bool = False,
    github_token: str = config["GITHUB_TOKEN"],
    session: Optional[aiohttp.ClientSession] = None,
) -> Optional[str]:
    """Try to create and return Hastebin paste, GitHub gist if it fails, otherwise return None."""
    session = session or aiohttp.ClientSession()
    try:
        return await hastebin(content, create_url=create_url, paste_url=paste_url, session=session)
    except ValueError:
        try:
            return await gist(
                (filename, content),
                description=description,
                public=public,
                github_token=github_token,
                session=session,
            )
        except ValueError:
            return None


async def try_gist_then_hastebin(
    content: str,
    *,
    create_url: str = config["HASTEBIN_CREATE_URL"],
    paste_url: str = config["HASTEBIN_PASTE_URL"],
    filename: str = "content.txt",
    description: Optional[str] = None,
    public: bool = False,
    github_token: str = config["GITHUB_TOKEN"],
    session: Optional[aiohttp.ClientSession] = None,
) -> Optional[str]:
    """Try to create and return GitHub gist, Hastebin paste if it fails, otherwise return None."""
    session = session or aiohttp.ClientSession()
    try:
        return await gist(
            (filename, content),
            description=description,
            public=public,
            github_token=github_token,
            session=session,
        )
    except ValueError:
        try:
            return await hastebin(
                content, create_url=create_url, paste_url=paste_url, session=session
            )
        except ValueError:
            return None
