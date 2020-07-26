import asyncio
import datetime
import logging
import signal
from typing import Any, Generator, List, Optional

import aiohttp
import asyncpg
import jinja2
import psutil

import discord
from discord.client import _cleanup_loop
from discord.ext import commands
from discord.ext import tasks

from botto import config, utils  # pylint: disable=cyclic-import
from .context import Context
from .errors import BotMissingFundamentalPermissions

try:
    import ujson as json
except ImportError:
    import json  # type: ignore

try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logger = logging.getLogger("botto")  # pylint: disable=invalid-name


class Botto(commands.AutoShardedBot):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned_or(*config["PREFIXES"]),
            pm_help=False,
            owner_id=config["OWNER_ID"],
            **kwargs,
        )
        self.ready_time: Optional[datetime.datetime] = None

        self.process: psutil.Process = psutil.Process()

        self.session: aiohttp.ClientSession = aiohttp.ClientSession(
            loop=self.loop, json_serialize=json.dumps, raise_for_status=True
        )

        self.add_check(self._check_fundamental_permissions)
        self.after_invoke(self.unlock_after_invoke)
        self.maintain_presence.start()  # pylint: disable=no-member

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
        if not config["OWNER_ID"]:
            raise ValueError("OWNER_ID not set in config file.")
        owner_id = config["OWNER_ID"]
        owner: Optional[discord.User] = self.get_user(owner_id)
        if owner is None:
            raise ValueError("Could not find owner in user cache.")
        return owner

    def get_console_channel(self) -> utils.AnyChannel:
        if not config["CONSOLE_CHANNEL_ID"]:
            raise ValueError("CONSOLE_CHANNEL_ID not set in config file.")
        channel_id = config["CONSOLE_CHANNEL_ID"]
        channel: utils.OptionalChannel = self.get_channel(channel_id)
        if channel is None:
            raise ValueError("Could not find console channel in channel cache.")
        return channel

    async def send_console(self, *args, **kwargs) -> discord.Message:
        try:
            return await self.get_console_channel().send(*args, **kwargs)
        except ValueError:
            return await self.get_owner().send(*args, **kwargs)

    # ------ Basic methods ------

    async def connect_to_database(self, dsn: str) -> None:
        self.pool: asyncpg.Pool = await asyncpg.create_pool(dsn)  # pylint: disable=no-member
        if not hasattr(self, "jinja_env"):
            self.jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader("botto/sql"), line_statement_prefix="-- :",
            )

    def get_queries(self, template_name: str) -> Any:
        return self.jinja_env.get_template(template_name).module

    def run(self) -> None:  # noqa: C901  # pylint: disable=arguments-differ
        loop = self.loop

        # Additional startup behavior
        dsn = config["DATABASE_URI"]
        if dsn:
            loop.run_until_complete(self.connect_to_database(dsn))

        for module in config["STARTUP_MODULES"]:
            self.load_extension(module)

        # Default behavior but calls self.shutdown instead of self.close
        try:
            loop.add_signal_handler(signal.SIGINT, loop.stop)
            loop.add_signal_handler(signal.SIGTERM, loop.stop)
        except NotImplementedError:
            pass

        async def runner() -> None:
            try:
                await self.start(config["TOKEN"])
            finally:
                await self.shutdown()

        stop_loop_on_completion = lambda future: loop.stop()  # noqa: E731

        future = asyncio.ensure_future(runner(), loop=loop)
        future.add_done_callback(stop_loop_on_completion)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Received signal to terminate bot and event loop.")
        finally:
            future.remove_done_callback(stop_loop_on_completion)
            logger.info("Cleaning up tasks.")
            _cleanup_loop(loop)

        if not future.cancelled():
            future.result()

    async def shutdown(self) -> None:
        self.maintain_presence.cancel()  # pylint: disable=no-member

        for ext in tuple(self.extensions):
            self.unload_extension(ext)

        if not self.session.closed:
            await self.session.close()
            logger.info("Gracefully closed asynchronous HTTP client session.")
        if hasattr(self, "pool") and not self.pool._closed:
            await self.pool.close()
            logger.info("Gracefully closed asynchronous database connection pool.")
        if not self.is_closed():
            logger.info("Closing client gracefully...")
            await self.close()

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
        except psutil.AccessDenied:
            embed = None
            logger.exception("psutil lacks permissions to check system information.")
        await self.send_console("Bot has connected.", embed=embed)

    async def on_error(self, event_method: str, *args: Any, **kwargs: Any) -> None:
        logger.exception("Unhandled exception in '%s' event handler.", event_method)

    # ------ Other ------

    @tasks.loop(minutes=5)
    async def maintain_presence(self):
        while not self.guilds:
            await asyncio.sleep(1)
        if getattr(self.guilds[0].me, "activity", None) is None:
            await self.change_presence(
                activity=discord.Activity(
                    name=f"@{self.user.name}", type=discord.ActivityType.listening
                )
            )
