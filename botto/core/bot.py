import asyncio
import datetime
import logging
from typing import Any, Generator, List, Optional

import aiohttp  # type: ignore
import psutil  # type: ignore

import discord  # type: ignore
from discord.ext import commands  # type: ignore
from discord.ext import tasks  # type: ignore

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

        self.process: psutil.Process = psutil.Process()

        self.session: aiohttp.ClientSession = aiohttp.ClientSession(
            loop=self.loop, json_serialize=json.dumps, raise_for_status=True
        )
        self.activity: discord.Activity = discord.Activity(
            name="@mention", type=discord.ActivityType.listening
        )

        self.add_check(self._check_fundamental_permissions)
        self.after_invoke(self.unlock_after_invoke)
        self.maintain_presence.start()

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

    async def close(self) -> None:
        self.maintain_presence.stop()

        for ext in tuple(self.extensions):
            self.unload_extension(ext)

        await self.session.close()
        logger.info("Gracefully closed asynchronous HTTP client session.")
        logger.info("Closing client gracefully...")
        await super().close()

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
        self.ready_time = datetime.datetime.utcnow()
        logger.info("Bot has connected.")
        try:
            embed: Optional[discord.Embed] = self.cogs["Meta"].get_statistics_embed()
        except KeyError:
            embed = None
            logger.warning("Meta cog was not found, statistics embed will not be sent.")
        await self.get_owner().send("Bot has connected.", embed=embed)

    # ------ Other ------

    @tasks.loop(minutes=5)
    async def maintain_presence(self):
        if self.guilds[0].me.activity is None:
            await self.change_presence(activity=self.activity)
