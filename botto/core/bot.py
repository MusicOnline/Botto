import asyncio
import datetime
import itertools
import logging
from typing import Any, Generator, List, Optional, Set

import aiohttp  # type: ignore
import pkg_resources
import psutil  # type: ignore

import discord  # type: ignore
from discord.ext import commands  # type: ignore

import botto
from .context import Context
from .errors import BotMissingFundamentalPermissions

try:
    import ujson as json
except ImportError:
    import json  # type: ignore

logger = logging.getLogger(__name__)


class Botto(commands.AutoShardedBot):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(*botto.config.PREFIXES),
            pm_help=False,
            owner_id=botto.config.OWNER_ID,
            **kwargs,
        )
        self.ready_time: Optional[datetime.datetime] = None
        self.keep_alive_task: Optional[asyncio.Task] = None

        self.dpy_version: str = pkg_resources.get_distribution("discord.py").version

        self.process: psutil.Process = psutil.Process()

        self.session: aiohttp.ClientSession = aiohttp.ClientSession(
            loop=self.loop, json_serialize=json.dumps, raise_for_status=True
        )

        self.activity: discord.Activity = discord.Activity(
            name="@Botto", type=discord.ActivityType.listening
        )

        self.remove_command("help")
        self.add_check(self._check_fundamental_permissions)
        self.after_invoke(self.unlock_after_invoke)

    # ------ Properties ------

    @property
    def ping(self) -> int:
        """The Discord WebSocket Protocol latency rounded in milliseconds."""
        return round(self.latency * 1000)

    @property
    def uptime(self) -> datetime.timedelta:
        assert isinstance(self.ready_time, datetime.datetime)
        return datetime.datetime.utcnow() - self.ready_time

    def humanize_uptime(self, *, brief: bool = False) -> str:
        hours, remainder = divmod(int(self.uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if not brief:
            fmt: str = "{h} hours, {m} minutes, and {s} seconds"
            if days:
                fmt = "{d} days, " + fmt
        else:
            fmt = "{h}h {m}m {s}s"
            if days:
                fmt = "{d}d " + fmt

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    def get_owner(self) -> discord.User:
        if not botto.config.OWNER_ID:
            raise ValueError("OWNER_ID not set in config file.")
        owner: Optional[discord.User] = self.get_user(botto.config.OWNER_ID)
        if owner is None:
            raise ValueError("Could not find owner in user cache.")
        return owner

    # ------ Basic methods ------

    def _do_cleanup(self) -> None:
        logger.info("Cleaning up event loop.")
        if self.loop.is_closed():
            return  # we're already cleaning up

        task: asyncio.Task = self.loop.create_task(self.shutdown())

        def _silence_gathered(fut: asyncio.Future) -> None:
            try:
                fut.result()
            except Exception:
                pass
            finally:
                self.loop.stop()

        def when_future_is_done(fut: asyncio.Future) -> None:
            pending: Set[asyncio.Task] = asyncio.Task.all_tasks(loop=self.loop)
            if pending:
                logger.info("Cleaning up after %s tasks.", len(pending))
                gathered = asyncio.gather(*pending, loop=self.loop)
                gathered.cancel()
                gathered.add_done_callback(_silence_gathered)
            else:
                self.loop.stop()

        task.add_done_callback(when_future_is_done)
        if not self.loop.is_running():
            self.loop.run_forever()
        else:
            # on Linux, we're still running because we got triggered via
            # the signal handler rather than the natural KeyboardInterrupt
            # Since that's the case, we're going to return control after
            # registering the task for the event loop to handle later
            return

        try:
            task.result()  # suppress unused task warning
        except Exception:
            pass

    async def shutdown(self) -> None:
        if self.keep_alive_task is not None:
            self.keep_alive_task.cancel()

        for ext in tuple(self.extensions):
            self.unload_extension(ext)

        await self.session.close()
        logger.info("Gracefully closed asynchronous HTTP client session.")
        await self.logout()
        logger.info("Gracefully logged out from Discord.")

    async def process_commands(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        ctx: Context = await self.get_context(message, cls=Context)
        if ctx.is_locked():
            return
        await self.invoke(ctx)

    # ------ Checks and invocation hooks ------

    async def _check_fundamental_permissions(self, ctx: Context) -> bool:
        # read_messages is an implicit requirement.
        # This check wouldn't run if it didn't read a command message. (duh)
        required_perms = discord.Permissions()
        required_perms.update(
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            external_emojis=True,
            add_reactions=True,
        )

        actual_perms = ctx.channel.permissions_for(ctx.me)

        missing: List[str] = [
            perm
            for perm, value in required_perms
            if value is True and getattr(actual_perms, perm) is not True
        ]

        if not missing:
            return True

        raise BotMissingFundamentalPermissions(missing)

    async def unlock_after_invoke(self, ctx: Context) -> None:
        """Post invocation hook to unlock context."""
        ctx.unlock()

    # ------ Views ------

    def users_view(self) -> Generator[discord.User, None, None]:
        return self._connection._users.values()

    def guilds_view(self) -> Generator[discord.Guild, None, None]:
        return self._connection._guilds.values()

    @property
    def user_count(self) -> int:
        return len(self._connection._users)

    @property
    def guild_count(self) -> int:
        return len(self._connection._guilds)

    # ------ Event listeners ------

    async def on_ready(self) -> None:
        if self.keep_alive_task is not None:
            self.keep_alive_task.cancel()
        self.keep_alive_task = self.loop.create_task(self.keep_alive())

        self.ready_time = datetime.datetime.utcnow()
        logger.info("Bot has connected.")
        try:
            embed: Optional[discord.Embed] = self.cogs["Meta"].get_statistics_embed()
        except KeyError:
            embed = None
            logger.warning("Meta cog was not found, statistics embed will not be sent.")
        await self.get_owner().send("Bot has connected.", embed=embed)

    # ------ Other ------

    async def keep_alive(self) -> None:
        """Background task for the bot not to enter a sleepish state when inactive."""
        channel: botto.utils.OptionalChannel = self.get_channel(
            botto.config.KEEP_ALIVE_CHANNEL
        )
        if channel is None:
            return
        assert isinstance(channel, discord.abc.Messageable)

        for i in itertools.count():
            if not self.is_closed():
                try:
                    await channel.send(f"Keeping alive, #{i}")
                except asyncio.CancelledError:
                    return
                except Exception:
                    pass
            await asyncio.sleep(5)
