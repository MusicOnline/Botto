import functools
from typing import Any, Callable, Coroutine, Dict, Optional, Tuple, Union

import aiohttp

from discord.ext import commands

from botto import config  # pylint: disable=cyclic-import

try:
    import ujson as json
except ImportError:
    import json  # type: ignore


class Context(commands.Context):

    locked_authors: Dict[int, "Context"] = {}

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session

    # ------ General and simple methods ------

    async def run_in_exec(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        partial: functools.partial[Any] = functools.partial(func, *args, **kwargs)
        return await self.bot.loop.run_in_executor(None, partial)

    # ------ Context locking ------

    def lock(self) -> None:
        """Lock the author from using other commands."""
        self.locked_authors[self.author.id] = self

    def unlock(self) -> None:
        """Unlock the author from using other commands."""
        self.locked_authors.pop(self.author.id, None)

    def is_locked(self) -> bool:
        """Check if the author is locked from using other commands."""
        return self.author.id in self.locked_authors

    # ------ Paste posting shortcuts ------

    async def mystbin(self, content: str) -> str:
        """Create a mystbin and return the url."""
        url: str = "https://mystb.in/documents"
        async with self.session.post(url, data=content.encode("utf-8")) as resp:
            response = await resp.json()
            return f"https://mystb.in/{response['key']}"

    async def gist(
        self, *files: Tuple[str, str], description: Optional[str] = None, public: bool = False,
    ) -> str:
        """Create a GitHub gist and return the url."""
        if not config["GITHUB_TOKEN"]:
            raise ValueError("GITHUB_TOKEN not set in config file.")

        github_token = config["GITHUB_TOKEN"]
        url: str = "https://api.github.com/gists"
        headers: Dict[str, str]
        headers = {"Authorization": f"token {github_token}"}
        _files: Dict[str, Dict[str, str]]
        _files = {file[0]: {"content": file[1]} for file in files}

        data: dict = {"files": _files, "public": public}
        if description is not None:
            data.update(description=description)

        async with self.bot.session.post(url, headers=headers, json=data) as resp:
            response = await resp.json()
            return response["html_url"]

    # ------ GET request wrappers ------

    async def get_as_bytes(self, url: Any, **kwargs: Any) -> bytes:
        """Send a GET request and return the response as bytes."""
        async with self.session.get(str(url), **kwargs) as resp:
            return await resp.read()

    async def get_as_text(self, url: Any, encoding: Optional[str] = None, **kwargs: Any) -> str:
        """Send a GET request and return the response as text."""
        async with self.session.get(str(url), **kwargs) as resp:
            return await resp.text(encoding=encoding)

    async def get_as_json(
        self,
        url: Any,
        *,
        encoding: Optional[str] = None,
        loads: Callable[[str], Any] = json.loads,
        content_type: Optional[str] = "application/json",
        **kwargs: Any,
    ) -> Any:
        """Send a GET request and return the response as json."""
        async with self.session.get(str(url), **kwargs) as resp:
            return await resp.json(encoding=encoding, loads=loads, content_type=content_type)


CoroType = Callable[..., Coroutine[Any, Any, Any]]
CommandOrCoro = Union[CoroType, commands.Command]


def lock_context() -> Callable[[CommandOrCoro], CommandOrCoro]:
    """Lock context before running command."""

    def wrapped(command_or_coro: CommandOrCoro) -> CommandOrCoro:
        if isinstance(command_or_coro, commands.Command):
            command: commands.Command = command_or_coro
            old_callback: CoroType = command.callback
        else:
            old_callback = command_or_coro

        @functools.wraps(old_callback)
        async def wrapped_callback(*args: Any, **kwargs: Any) -> None:
            ctx: Context = args[0] if isinstance(args[0], Context) else args[1]
            ctx.lock()
            await old_callback(*args, **kwargs)

        try:
            command.callback = wrapped_callback
            return command
        except NameError:
            return wrapped_callback

    return wrapped
