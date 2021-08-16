import asyncio
import datetime
import logging
from typing import Any, Dict, Optional

import aiohttp
import discord
from discord.ext import commands, tasks

import botto

try:
    import ujson as json
except ImportError:
    import json  # type: ignore


logger: logging.Logger = logging.getLogger("botto.restricted_api")  # pylint: disable=invalid-name


class RestrictedApi(commands.Cog):
    def __init__(self, bot: botto.Botto) -> None:
        self.bot: botto.Botto = bot
        self.websocket: Optional[aiohttp.ClientWebSocketResponse] = None
        self.latency: Optional[float] = None
        self.connect_task_loop: asyncio.Task = self.bot.loop.create_task(self.connect_to_server())

    def stop_and_disconnect(self) -> None:
        self.connect_task_loop.cancel()
        self.ping_and_get_latency.cancel()  # pylint: disable=no-member
        if self.websocket:
            self.bot.loop.create_task(self.websocket.close())
            logger.info("Disconnected from restricted API.")

    def cog_unload(self) -> None:
        self.stop_and_disconnect()

    async def connect_to_server(self) -> None:
        while not self.bot.is_closed():
            self.ping_and_get_latency.cancel()  # pylint: disable=no-member
            try:
                self.websocket = await self.bot.session.ws_connect(
                    botto.config["RESTRICTED_API_URL"]
                )
            except aiohttp.ClientConnectorError:
                logger.exception(
                    "Exception raised in restricted API connection. Retrying in 5 seconds."
                )
                await asyncio.sleep(5)
                continue

            logger.info("Connected to restricted API.")
            self.ping_and_get_latency.start()  # pylint: disable=no-member
            async for msg in self.websocket:
                data: Dict[str, Any] = json.loads(msg.data)
                self.bot.dispatch("restricted_api_" + data["type"], data)
            logger.info("Disconnected from restricted API.")

        self.ping_and_get_latency.cancel()  # pylint: disable=no-member

    @tasks.loop(minutes=1)
    async def ping_and_get_latency(self) -> float:
        time_start: float = datetime.datetime.utcnow().timestamp()
        await self.send_event("ping", timestamp=str(time_start))
        await self.bot.wait_for(
            "restricted_api_pong",
            check=lambda payload: payload["timestamp"] == str(time_start),
            timeout=30,
        )
        time_delta: float = datetime.datetime.utcnow().timestamp() - time_start
        self.latency = time_delta
        return time_delta

    @ping_and_get_latency.after_loop
    async def on_ping_and_get_latency_cancel(self) -> None:
        if self.ping_and_get_latency.is_being_cancelled():  # pylint: disable=no-member
            self.latency = None

    async def send_event(self, event: str, **data: Any) -> None:
        if not self.websocket:
            raise botto.NotConnectedToRestrictedApi
        try:
            await self.websocket.send_str(json.dumps(dict(type=event, **data)))
        except RuntimeError as exc:
            # RuntimeError: unable to perform operation on <TCPTransport closed=True reading=False
            # 0x??? >; the handler is closed
            self.stop_and_disconnect()
            RestrictedApi.__init__(self, self.bot)
            raise botto.NotConnectedToRestrictedApi from exc

    async def send_event_with_context(self, event: str, ctx: botto.Context, **data: Any) -> None:
        context: Dict[str, Any] = {
            "author": {
                "name": ctx.author.name,
                "discriminator": ctx.author.discriminator,
                "id": ctx.author.id,
            },
            "channel": {
                "name": ctx.channel.name if ctx.guild else f"{ctx.author}'s DM",
                "id": ctx.channel.id,
            },
            "guild": ({"name": ctx.guild.name, "id": ctx.guild.id} if ctx.guild else None),
            "message": {"id": ctx.message.id},
        }
        await self.send_event(event, ctx=context, **data)

    def get_statistics_embed(self, payload: Dict[str, Any]) -> discord.Embed:
        embed: discord.Embed = discord.Embed(
            color=botto.config["MAIN_COLOR"], timestamp=datetime.datetime.utcnow()
        )
        embed.set_thumbnail(url=self.bot.user.avatar_url)

        embed.add_field(name="Connection", value=f"{self.bot.restricted_api_ping} ms latest")
        embed.add_field(
            name="Process",
            value=(
                f"{payload['process']['cpu']}% CPU\n"
                f"{payload['process']['used_ram'] / 2 ** 20:.2f} MiB"
            ),
        )
        embed.add_field(
            name="System",
            value=(
                f"{payload['system']['cpu']}% CPU\n"
                f"{payload['system']['used_ram'] / 2 ** 30:.2f} of "
                f"{payload['system']['total_ram'] / 2 ** 30:.2f} GiB"
            ),
        )

        return embed

    @botto.require_restricted_api()
    @botto.command()
    async def webstats(self, ctx: botto.Context) -> None:
        """Show general statistics of the backend server and system."""

        await self.bot.send_api_event_with_context("stats", ctx)

    @commands.Cog.listener()
    async def on_restricted_api_ack_stats(self, payload: dict) -> None:
        channel: botto.utils.OptionalChannel = self.bot.get_channel(payload["ctx"]["channel"]["id"])
        if not channel:
            return
        message: discord.PartialMessage = channel.get_partial_message(
            payload["ctx"]["message"]["id"]
        )
        embed: discord.Embed = self.get_statistics_embed(payload)
        await message.reply(embed=embed)


def setup(bot: botto.Botto) -> None:
    bot.add_cog(RestrictedApi(bot))
