import asyncio
import logging
import time
from typing import Any, Dict, Optional

import aiohttp
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
        self.bot.loop.create_task(self.connect_to_server())

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
            self.ping_and_get_latency.start()  # pylint: disable=no-member
            async for msg in self.websocket:
                data: Dict[str, Any] = json.loads(msg.data)
                self.bot.dispatch("restricted_api_" + data["type"], data)
        self.ping_and_get_latency.cancel()  # pylint: disable=no-member

    @tasks.loop(minutes=1)
    async def ping_and_get_latency(self) -> float:
        time_start: float = time.perf_counter()
        await self.send_event("ping", timestamp=str(time_start))
        await self.bot.wait_for(
            "restricted_api_pong",
            check=lambda payload: payload["timestamp"] == str(time_start),
            timeout=30,
        )
        time_delta: float = time.perf_counter() - time_start
        self.latency = time_delta
        return time_delta

    async def send_event(self, event: str, **data: Any) -> None:
        if not self.websocket:
            raise botto.NotConnectedToRestrictedApi
        await self.websocket.send_str(json.dumps(dict(type=event, **data)))

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


def setup(bot: botto.Botto) -> None:
    bot.add_cog(RestrictedApi(bot))


def teardown(bot: botto.Botto) -> None:
    cog: Optional[commands.Cog] = bot.get_cog("RestrictedApi")
    assert isinstance(cog, RestrictedApi)
    if cog.websocket:
        bot.loop.create_task(cog.websocket.close())
